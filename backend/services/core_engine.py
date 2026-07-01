import logging
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from backend.core.cache import cache_get_df, cache_set_df
from backend.core.config import (
    CONFIG,
    OTM_DEFAULT,
    OTM_POR_ATIVO,
    is_reentrada_valida,
    registrar_sinal,
    score_horario,
    get_ticker_lock,
)
from backend.domain.greeks import calculate_greeks, implied_volatility
from backend.domain.indicators import (
    calcular_indicadores,
    detectar_canal_linear,
    detectar_divergencia,
    encontrar_zonas_demanda_oferta,
    ultimos_pivots_confirmados,
)
from backend.domain.options_math import (
    estimar_iv_historica,
    estimar_premio_otm,
    mes_vencimento_ideal,
    resolver_iv,
)
from backend.domain.scoring import (
    avaliar_filtro_iv,
    calcular_familias,
    classificar_setup,
    parametros_setup_shadow,
    score_ponderado,
)
from backend.services.data_providers import (
    fetch_brapi_historical,
    get_real_options_from_opcoes_net,
    obter_opcoes_vizinhas,
)
from backend.services.iv_history_service import iv_rank as obter_iv_rank

logger = logging.getLogger("b3_scanner")

def _baixar_yfinance(ticker: str, period: str, interval: str, verbose: bool) -> pd.DataFrame | None:
    """Baixa OHLCV via yfinance com 3 tentativas e backoff exponencial (1s, 2s, 4s)."""
    for tentativa in range(3):
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                return df
            return None
        except Exception as e:
            if tentativa == 2:
                if verbose:
                    logger.warning(f"yfinance falhou para {ticker} após 3 tentativas: {e}")
                return None
            time.sleep(2 ** tentativa)
    return None


def _baixar_ohlcv(ticker: str, period: str, interval: str, verbose: bool) -> pd.DataFrame | None:
    """Escolhe a ordem das fontes de OHLCV. Com BRAPI_TOKEN configurado, usa a brapi
    PRIMEIRO (evita o rate-limit do Yahoo no IP do servidor), caindo para yfinance se
    vier vazia. Sem token, mantém yfinance primeiro com a brapi como fallback."""
    if os.getenv("BRAPI_TOKEN"):
        df = fetch_brapi_historical(ticker, range_=period, interval=interval)
        if df is not None and not df.empty:
            if verbose:
                logger.info(f"📡 {ticker}: dados via brapi (primária)")
            return df
        return _baixar_yfinance(ticker, period, interval, verbose)

    df = _baixar_yfinance(ticker, period, interval, verbose)
    if df is not None and not df.empty:
        return df
    df = fetch_brapi_historical(ticker, range_=period, interval=interval)
    if df is not None and not df.empty and verbose:
        logger.info(f"📡 {ticker}: dados via brapi (fallback)")
    return df


def _carregar_ohlcv(ticker: str, interval: str, df_provided: pd.DataFrame | None,
                    indicators_calculated: bool, verbose: bool) -> pd.DataFrame | None:
    """Carrega/prepara o OHLCV: usa ``df_provided`` ou baixa das fontes (brapi/yfinance,
    com cache), calcula indicadores e valida tamanho. Retorna o df pronto para análise
    ou None se os dados forem insuficientes."""
    if df_provided is not None:
        df = df_provided.copy()
    else:
        period = "6mo" if interval == "1d" else "730d"
        cache_key = f"ohlcv:{ticker}:{interval}:{period}"
        df = cache_get_df(cache_key)

        if df is None:
            df = _baixar_ohlcv(ticker, period, interval, verbose)
            if df is not None and not df.empty:
                cache_set_df(cache_key, df, ttl=300)  # 5 min cache

    if df is None or len(df) < 30:
        return None

    if not indicators_calculated:
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = calcular_indicadores(df)
        df.dropna(inplace=True)

    if len(df) < 5:
        return None

    return df


def _avaliar_gatilhos(df: pd.DataFrame, ultimo, penult, preco: float,
                      vol_med: float, volume: float) -> dict:
    """Avalia os gatilhos técnicos (alta/baixa) sobre o df e retorna os scores,
    as listas de sinais (texto, p/ exibição) e de IDs (Camada 2.1, ex.: "G1"),
    e os escalares usados a jusante (stoch_k, rsi, vol_ratio).
    Não inclui o bônus de horário (somado pelo orquestrador)."""
    sinais_alta, sinais_baixa = [], []
    ids_alta, ids_baixa = [], []
    score_alta = score_baixa = 0

    stoch_k      = float(ultimo.get("stoch_k",     50))
    stoch_d      = float(ultimo.get("stoch_d",     50))
    stoch_k_prev = float(penult.get("stoch_k",     50))
    stoch_d_prev = float(penult.get("stoch_d",     50))
    rsi          = float(ultimo.get("rsi",         50))
    ema9         = float(ultimo.get("ema9",     preco))
    ema21        = float(ultimo.get("ema21",    preco))
    ema9_prev    = float(penult.get("ema9",     ema9))
    ema21_prev   = float(penult.get("ema21",    ema21))
    macd_d       = float(ultimo.get("macd_diff",    0))
    macd_d_prev  = float(penult.get("macd_diff",    0))
    atr          = float(ultimo.get("atr",  preco*0.02))
    sup20        = float(ultimo.get("suporte_20",   preco))
    res20        = float(ultimo.get("resistencia_20",preco))
    vol_ratio    = volume / vol_med if vol_med > 0 else 1.0
    bb_lo        = float(ultimo.get("bb_lower",     0))

    ordem = CONFIG["pivot_ordem"]
    ultimos_fundos, ultimos_topos = ultimos_pivots_confirmados(df, ordem, n=3)

    # ── GATILHOS DE ALTA ─────────────────────────────────────────────
    if (stoch_k < CONFIG["stoch_oversold"] + 10 and stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev):
        sinais_alta.append("📈 Estocástico: cruzamento altista em sobrevenda")
        ids_alta.append("G1")
        score_alta += 3

    if rsi < CONFIG["rsi_oversold"]:
        sinais_alta.append(f"📈 RSI sobrevenda: {rsi:.1f}")
        ids_alta.append("G2")
        score_alta += 2

    if preco <= sup20 + atr:
        sinais_alta.append(f"📈 Preço em suporte 20D: R${sup20:.2f}")
        ids_alta.append("G3")
        score_alta += 2

    if ema9 > ema21 and ema9_prev <= ema21_prev:
        sinais_alta.append("📈 EMA9 cruzou acima EMA21")
        ids_alta.append("G4")
        score_alta += 2

    if vol_ratio >= CONFIG["volume_mult"]:
        sinais_alta.append(f"📈 Volume {vol_ratio:.1f}x acima da média")
        ids_alta.append("G5")
        score_alta += 1

    if macd_d > 0 and macd_d_prev <= 0:
        sinais_alta.append("📈 MACD cruzou zero (momentum altista)")
        ids_alta.append("G6")
        score_alta += 2

    if (len(ultimos_fundos) >= 3 and all(ultimos_fundos[i] < ultimos_fundos[i+1] for i in range(2))):
        sinais_alta.append("📈 Fundos ascendentes (reversão)")
        ids_alta.append("G7")
        score_alta += 2

    if bb_lo > 0 and preco <= bb_lo * 1.01:
        sinais_alta.append(f"📈 Preço na Bollinger inferior: R${bb_lo:.2f}")
        ids_alta.append("G8")
        score_alta += 1

    div_alta, _ = detectar_divergencia(df, janela=5)
    if div_alta:
        sinais_alta.append("📈 Divergência altista RSI (preço cai, RSI sobe)")
        ids_alta.append("G9")
        score_alta += 3

    zona_dem, _ = encontrar_zonas_demanda_oferta(df)
    if zona_dem:
        sinais_alta.append("📈 Preço em zona de demanda histórica")
        ids_alta.append("G10")
        score_alta += 3

    canal_alt, _, slope = detectar_canal_linear(df)
    if canal_alt:
        sinais_alta.append(f"📈 Canal altista (slope={slope:.3f})")
        ids_alta.append("G11")
        score_alta += 2

    # ── GATILHOS DE BAIXA ────────────────────────────────────────────
    if (stoch_k > CONFIG["stoch_overbought"] - 10 and stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev):
        sinais_baixa.append("📉 Estocástico: cruzamento baixista em sobrecompra")
        ids_baixa.append("B1")
        score_baixa += 3

    if rsi > CONFIG["rsi_overbought"]:
        sinais_baixa.append(f"📉 RSI sobrecompra: {rsi:.1f}")
        ids_baixa.append("B2")
        score_baixa += 2

    if preco >= res20 - atr:
        sinais_baixa.append(f"📉 Preço em resistência 20D: R${res20:.2f}")
        ids_baixa.append("B3")
        score_baixa += 2

    if ema9 < ema21 and ema9_prev >= ema21_prev:
        sinais_baixa.append("📉 EMA9 cruzou abaixo EMA21")
        ids_baixa.append("B4")
        score_baixa += 2

    if (len(ultimos_topos) >= 3 and all(ultimos_topos[i] > ultimos_topos[i+1] for i in range(2))):
        sinais_baixa.append("📉 Topos descendentes (tendência de baixa)")
        ids_baixa.append("B5")
        score_baixa += 2

    if macd_d < 0 and macd_d_prev >= 0:
        sinais_baixa.append("📉 MACD cruzou zero negativamente")
        ids_baixa.append("B6")
        score_baixa += 2

    _, div_baixa = detectar_divergencia(df, janela=5)
    if div_baixa:
        sinais_baixa.append("📉 Divergência baixista RSI (preço sobe, RSI cai)")
        ids_baixa.append("B7")
        score_baixa += 3

    _, zona_ofe = encontrar_zonas_demanda_oferta(df)
    if zona_ofe:
        sinais_baixa.append("📉 Preço em zona de oferta histórica")
        ids_baixa.append("B8")
        score_baixa += 3

    _, canal_bx, slope_bx = detectar_canal_linear(df)
    if canal_bx:
        sinais_baixa.append(f"📉 Canal baixista (slope={slope_bx:.3f})")
        ids_baixa.append("B9")
        score_baixa += 2

    return {
        "score_alta": score_alta, "score_baixa": score_baixa,
        "sinais_alta": sinais_alta, "sinais_baixa": sinais_baixa,
        "ids_alta": ids_alta, "ids_baixa": ids_baixa,
        "stoch_k": stoch_k, "rsi": rsi, "vol_ratio": vol_ratio,
    }


def _montar_estrutura_opcao(ticker_base: str, preco: float, tipo_sinal: str,
                            df: pd.DataFrame, interval: str, verbose: bool,
                            is_backtest: bool = False) -> dict | None:
    """Monta a estrutura da opção (strike, vencimento, IV, prêmio, opção real,
    greeks, entradas/alvos/stop, R/R). Retorna o dict da estrutura ou None se
    rejeitado pelos filtros de delta ou R/R."""
    dist_otm   = OTM_POR_ATIVO.get(ticker_base, OTM_DEFAULT)
    strike_ref = round(
        preco * (1 - dist_otm) if tipo_sinal == "PUT" else preco * (1 + dist_otm), 2
    )

    if is_backtest:
        # No backtest, calcula vencimento a partir da data do próprio sinal
        data_ref = df.index[-1].to_pydatetime().date() if hasattr(df.index[-1], "to_pydatetime") else df.index[-1]
        if hasattr(data_ref, "date"):
            data_ref = data_ref.date()
        mes_v, ano_v, dte = mes_vencimento_ideal(hoje=data_ref)
    else:
        mes_v, ano_v, dte = mes_vencimento_ideal()

    hv_20d       = estimar_iv_historica(df, interval=interval)
    premio_est   = estimar_premio_otm(preco, strike_ref, dte, hv_20d, tipo_sinal)

    # --- INTEGRAÇÃO COM DADOS REAIS (opcoes.net.br) ---
    if is_backtest:
        opcao_real = None
    else:
        opcao_real = get_real_options_from_opcoes_net(ticker_base, tipo_sinal, strike_ref)

    if opcao_real:
        strike_ref = opcao_real["strike_real"]
        preco_tela = opcao_real["preco_tela"]
        ticker_opcao = opcao_real["ticker_opcao"]
    else:
        preco_tela = None
        ticker_opcao = "N/A (S/ Liquidez)"

    T = max(dte, 1) / 252

    # Fallback chain de IV implícita (Camada 1.1): tela -> strikes vizinhos -> HV proxy -> default
    ivs_vizinhos = []
    if preco_tela:
        for vizinho in obter_opcoes_vizinhas(ticker_base, tipo_sinal, strike_ref, mes_v, ano_v, strike_ref):
            intrinsico = (max(preco - vizinho["strike_real"], 0.0) if tipo_sinal == "CALL"
                         else max(vizinho["strike_real"] - preco, 0.0))
            if vizinho["preco_tela"] > intrinsico:
                try:
                    ivs_vizinhos.append(implied_volatility(
                        preco, vizinho["strike_real"], T, vizinho["preco_tela"],
                        tipo_sinal, sigma_init=hv_20d,
                    ))
                except Exception:
                    pass

    iv_impl, iv_source = resolver_iv(preco_tela, preco, strike_ref, T, tipo_sinal, hv_20d, ivs_vizinhos)
    iv_mercado = iv_impl if iv_source == "tela" else None
    greeks = calculate_greeks(preco, strike_ref, T, iv_impl, tipo_sinal)

    delta_abs = abs(greeks["delta"])
    if delta_abs and not (CONFIG.get("delta_min", 0.0) <= delta_abs <= CONFIG.get("delta_max", 1.0)):
        if verbose:
            logger.info(f"⚠ {ticker_base}: |delta|={delta_abs:.2f} fora da faixa OTM ideal")
        return None

    # O preço de tela vira a nossa entrada principal, se existir
    preco_base_calculo = preco_tela if preco_tela else premio_est

    band = CONFIG.get("buy_band_pct", 0.035)
    entrada_min  = round(preco_base_calculo * (1 - band), 2)
    entrada_max  = round(preco_base_calculo * (1 + band), 2)
    alvo1        = round(preco_base_calculo * (1 + CONFIG["alvo1_pct"]),     2)
    alvo2        = round(preco_base_calculo * (1 + CONFIG["alvo2_pct"]),     2)
    alvo_final   = round(preco_base_calculo * (1 + CONFIG["alvo_final_pct"]),2)
    stop         = round(preco_base_calculo * (1 + CONFIG["stop_pct"]),      2)

    book_until   = (datetime.now() + timedelta(days=CONFIG.get("book_days", 7))).strftime("%d/%m")
    risco        = preco_base_calculo - stop
    # R/R é informativo apenas (alvos/stop são % fixos → razão constante; não filtra).
    rr_alvo1     = round((alvo1 - preco_base_calculo) / risco, 2) if risco > 0 else 0
    rr_alvo2     = round((alvo2 - preco_base_calculo) / risco, 2) if risco > 0 else 0
    rr_final     = round((alvo_final - preco_base_calculo) / risco, 2) if risco > 0 else 0

    return {
        "dist_otm": dist_otm, "strike_ref": strike_ref, "hv_20d": hv_20d,
        "iv_impl": iv_impl, "iv_source": iv_source, "iv_mercado": iv_mercado,
        "dte": dte, "mes_v": mes_v, "ano_v": ano_v, "premio_est": premio_est,
        "preco_tela": preco_tela, "ticker_opcao": ticker_opcao,
        "entrada_min": entrada_min, "entrada_max": entrada_max,
        "alvo1": alvo1, "alvo2": alvo2, "alvo_final": alvo_final, "stop": stop,
        "book_until": book_until, "greeks": greeks,
        "rr_alvo1": rr_alvo1, "rr_alvo2": rr_alvo2, "rr_final": rr_final,
        "preco_base_calculo": preco_base_calculo,
    }


def _montar_sinal(ticker_base: str, nome: str, tipo_sinal: str, direcao_label: str,
                  emoji: str, score: int, gatilhos: list, preco: float, ultimo, penult,
                  stoch_k: float, rsi: float, vol_ratio: float, estrutura: dict,
                  verbose: bool, bonus_sessao: int = 0) -> dict | None:
    """Calcula o score ponderado (shadow) e monta o dict final do sinal.
    Retorna None se o modo 'ponderado' reprovar."""
    try:
        score_pond = score_ponderado(
            ultimo, penult,
            option_price=estrutura["preco_base_calculo"],
            dte=estrutura["dte"], greeks=estrutura["greeks"], direction=tipo_sinal,
        )
        shadow_score = score_pond["score"]
        shadow_signal = score_pond["signal"]
        shadow_reasons = score_pond["reasons"]
    except Exception as e:
        if verbose:
            logger.warning(f"shadow score falhou para {ticker_base}: {e}")
        shadow_score, shadow_signal, shadow_reasons = None, None, []

    # No modo "ponderado" o ponderado decide; "classico" mantém comportamento atual
    if CONFIG.get("scoring_mode") == "ponderado":
        if not shadow_signal:
            if verbose:
                logger.info(f"⚠ {ticker_base}: score ponderado {shadow_score} abaixo do limiar")
            return None

    hv_20d = estrutura["hv_20d"]
    iv_mercado = estrutura["iv_mercado"]
    return {
        "emoji":        emoji,
        "ticker":       ticker_base,
        "nome":         nome,
        "tipo_sinal":   tipo_sinal,
        "direcao":      direcao_label,
        "preco_acao":   preco,
        "ticker_opcao": estrutura["ticker_opcao"],
        "strike_ref":   estrutura["strike_ref"],
        "dist_otm_pct": estrutura["dist_otm"] * 100,
        "hv_20d":       round(hv_20d * 100, 1),
        "iv_mercado":   round(iv_mercado * 100, 1) if iv_mercado else None,
        "iv_impl":      round(estrutura["iv_impl"] * 100, 1),
        "iv_source":    estrutura["iv_source"],
        "iv_rank":      estrutura.get("iv_rank"),
        "iv_premium":   estrutura.get("iv_premium"),
        "iv_filter_decisao": estrutura.get("iv_filter_decisao"),
        "dte":          estrutura["dte"],
        "mes_venc":     estrutura["mes_v"],
        "ano_venc":     estrutura["ano_v"],
        "premio_est":   estrutura["premio_est"],
        "preco_tela":   estrutura["preco_tela"],
        "entrada_min":  estrutura["entrada_min"],
        "entrada_max":  estrutura["entrada_max"],
        "alvo1":        estrutura["alvo1"],
        "alvo2":        estrutura["alvo2"],
        "alvo_final":   estrutura["alvo_final"],
        "stop":         estrutura["stop"],
        "book_until":   estrutura["book_until"],
        "greeks":       estrutura["greeks"],
        "score_ponderado": shadow_score,
        "ponderado_passou": shadow_signal,
        "ponderado_reasons": shadow_reasons,
        "rr_alvo1":     estrutura["rr_alvo1"],
        "rr_alvo2":     estrutura["rr_alvo2"],
        "rr_final":     estrutura["rr_final"],
        "score":        score,
        "score_tecnico": score,
        "bonus_sessao":  bonus_sessao,
        "stoch_k":      stoch_k,
        "rsi":          rsi,
        "vol_ratio":    vol_ratio,
        "vol_media_20": float(ultimo.get("vol_media_20", 0)),
        "gatilhos":     gatilhos,
        "gatilhos_ids": estrutura.get("gatilhos_ids", []),
        "familias_ativas": estrutura.get("familias_ativas"),
        "score_familias_capped": estrutura.get("score_familias_capped"),
        "consenso_decisao": estrutura.get("consenso_decisao"),
        "setup":        estrutura.get("setup"),
        "setup_params_shadow": estrutura.get("setup_params_shadow"),
    }


def analisar_ativo(ticker: str, nome: str, interval: str = "1d", verbose: bool = False, df_provided: pd.DataFrame = None, indicators_calculated: bool = False, incluir_em_cooldown: bool = False) -> dict | None:
    """
    Analisa um ativo e retorna sinal de opção se critérios forem atendidos.
    Pode receber df_provided para testes e backtest, ou baixar direto via yfinance.

    incluir_em_cooldown: quando True (scan manual), um sinal bloqueado apenas
    pela regra de reentrada ainda é retornado, marcado com em_cooldown=True e
    SEM re-registrar o cooldown — o chamador decide exibi-lo, mas não deve
    persistir nem notificar (o dedup continua valendo para esses caminhos).
    """
    try:
        ticker_base = ticker.replace(".SA", "")

        df = _carregar_ohlcv(ticker, interval, df_provided, indicators_calculated, verbose)
        if df is None:
            return None

        ultimo    = df.iloc[-1]
        penult    = df.iloc[-2]

        preco     = float(ultimo["Close"])
        volume    = float(ultimo["Volume"])
        vol_med   = float(ultimo.get("vol_media_20", volume))

        if vol_med < CONFIG["min_volume_acoes"]:
            return None

        gat = _avaliar_gatilhos(df, ultimo, penult, preco, vol_med, volume)
        sinais_alta  = gat["sinais_alta"]
        sinais_baixa = gat["sinais_baixa"]
        score_alta   = gat["score_alta"]
        score_baixa  = gat["score_baixa"]
        stoch_k      = gat["stoch_k"]
        rsi          = gat["rsi"]
        vol_ratio    = gat["vol_ratio"]

        # ── BÔNUS DE SESSÃO (informativo — NÃO entra na decisão de emissão) ──
        bonus_sessao = score_horario()

        # ── DECISÃO (apenas score técnico/direcional) ─────────────────────
        MIN_SCORE = CONFIG["min_score"]
        if score_alta < MIN_SCORE and score_baixa < MIN_SCORE:
            return None

        if score_alta >= score_baixa:
            tipo_sinal    = "CALL"
            score         = score_alta
            gatilhos      = sinais_alta
            direcao_label = "COMPRA DE CALL"
            emoji         = "🟢"
        else:
            tipo_sinal    = "PUT"
            score         = score_baixa
            gatilhos      = sinais_baixa
            direcao_label = "COMPRA DE PUT"
            emoji         = "🔴"

        # ── REENTRADA por (ticker, direção, score) — só em produção ──────
        ticker_lock = get_ticker_lock(ticker_base)
        with ticker_lock:
            em_cooldown = df_provided is None and not is_reentrada_valida(ticker_base, tipo_sinal, score)
            if em_cooldown and not incluir_em_cooldown:
                if verbose:
                    logger.info(f"↩ {ticker_base}: reentrada bloqueada ({tipo_sinal}, score {score})")
                return None

            # ── ESTRUTURA DA OPÇÃO ────────────────────────────────────────────
            estrutura = _montar_estrutura_opcao(
                ticker_base, preco, tipo_sinal, df, interval, verbose, is_backtest=(df_provided is not None)
            )
            if estrutura is None:
                return None

            # ── FILTRO DE VOLATILIDADE (Camada 1.3 — shadow mode por padrão) ──
            rank_info = obter_iv_rank(ticker_base)
            filtro = avaliar_filtro_iv(rank_info["iv_rank"], rank_info["iv_premium"],
                                       rank_info["confiavel"], score)
            estrutura["iv_rank"] = rank_info["iv_rank"]
            estrutura["iv_premium"] = rank_info["iv_premium"]
            estrutura["iv_filter_decisao"] = filtro["decisao"]

            if CONFIG.get("iv_filter_mode") == "ativo":
                if filtro["decisao"] == "bloquear":
                    if verbose:
                        logger.info(f"🚫 {ticker_base}: filtro IV bloqueou emissão ({filtro['motivo']})")
                    return None
                if filtro["decisao"] == "exige_score_7" and score < 7:
                    if verbose:
                        logger.info(f"🚫 {ticker_base}: filtro IV exige score>=7, atual={score} ({filtro['motivo']})")
                    return None
            elif filtro["decisao"] != "normal" and verbose:
                logger.info(f"ℹ {ticker_base}: filtro IV (shadow) indicaria '{filtro['decisao']}' — {filtro['motivo']}")

            # ── FAMÍLIAS / CONSENSO / SETUP (Camada 2.1-2.2 — shadow) ─────────
            gatilhos_ids = gat["ids_alta"] if tipo_sinal == "CALL" else gat["ids_baixa"]
            familias = calcular_familias(gatilhos_ids)
            consenso_decisao = ("passaria" if (score >= MIN_SCORE and familias["familias_ativas"] >= 2)
                                else "bloquearia")
            setup = classificar_setup(familias["breakdown"])
            estrutura["gatilhos_ids"] = gatilhos_ids
            estrutura["familias_ativas"] = familias["familias_ativas"]
            estrutura["score_familias_capped"] = familias["score_capped"]
            estrutura["consenso_decisao"] = consenso_decisao
            estrutura["setup"] = setup
            estrutura["setup_params_shadow"] = parametros_setup_shadow(setup)

            # Sinal em cooldown não re-registra (não estende a janela de reentrada).
            if df_provided is None and not em_cooldown:
                registrar_sinal(ticker_base, tipo_sinal, score)

            sinal = _montar_sinal(ticker_base, nome, tipo_sinal, direcao_label, emoji, score,
                                  gatilhos, preco, ultimo, penult, stoch_k, rsi, vol_ratio,
                                  estrutura, verbose, bonus_sessao=bonus_sessao)
            if sinal is not None:
                sinal["em_cooldown"] = em_cooldown
            return sinal

    except Exception as e:
        if verbose:
            logger.error(f"✗ Erro {ticker}: {e}")
        return None
