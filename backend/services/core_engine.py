import logging
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from backend.core.cache import cache_get_df, cache_set_df
from backend.core.config import (
    CONFIG,
    OTM_DEFAULT,
    OTM_POR_ATIVO,
    get_ticker_lock,
    is_reentrada_valida,
    registrar_sinal,
    score_horario,
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
    avaliar_filtro_liquidez_shadow,
    avaliar_vetos_tecnicos,
    calcular_classe_v2,
    calcular_familias,
    classificar_setup,
    divergencia_premio_pct,
    parametros_setup_shadow,
    score_ponderado,
    sizing_sugerido_pct,
)
from backend.services.data_providers import (
    fetch_brapi_historical,
    get_real_options_from_opcoes_net,
    obter_opcoes_vizinhas,
)
from backend.services.event_service import obter_evento_na_data
from backend.services.iv_history_service import iv_rank as obter_iv_rank
from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_scanner")


def obter_option_liquidity(ticker_base: str, data, max_idade_dias: int = 7) -> dict | None:
    """Consulta a linha mais recente de option_liquidity com data <= `data` (Fase 3).

    Os arquivos B3 (PR/COTAHIST) refletem o FECHAMENTO do pregão: o scan do dia D
    usa o dado do pregão D-1 (ou o mais recente disponível). `max_idade_dias`
    limita o quão velho o dado pode ser — além disso, é tratado como inexistente
    (None = "desconhecido", não penaliza).

    Fail-safe: Supabase indisponível, linha inexistente ou qualquer exceção
    retornam None — a emissão de sinais nunca depende desses dados (shadow).
    """
    try:
        supabase = get_supabase()
        if not supabase:
            return None
        limite = data - timedelta(days=max_idade_dias)
        res = (supabase.table("option_liquidity")
               .select("oi, bid, ask, spread_pct, vxbr, evento_label")
               .eq("ticker", ticker_base)
               .lte("data", data.isoformat())
               .gte("data", limite.isoformat())
               .order("data", desc=True)
               .limit(1)
               .execute())
        return res.data[0] if res.data else None
    except Exception:
        return None

def _baixar_yfinance(ticker: str, period: str, interval: str, verbose: bool) -> pd.DataFrame | None:
    """Baixa OHLCV via yfinance com 3 tentativas e backoff exponencial (1s, 2s, 4s)."""
    yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
    for tentativa in range(3):
        try:
            df = yf.download(yf_ticker, period=period, interval=interval, auto_adjust=True, progress=False)
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


_PUCK_IDS = {"G20", "G21", "B20", "B21"}


def _filtrar_ids_puck_shadow(ids: list[str], sinais: list[str]) -> tuple[list[str], list[str]]:
    """Remove IDs PUCK (e textos correspondentes) quando puck_gatilhos_mode != "ativo".
    Evita que gatilhos em shadow contaminem calcular_familias/classe via as
    listas principais quando matriz_v2_gatilhos_mode está "ativo"."""
    if CONFIG.get("puck_gatilhos_mode") == "ativo":
        return ids, sinais
    pares = [(i, s) for i, s in zip(ids, sinais) if i not in _PUCK_IDS]
    return [i for i, _ in pares], [s for _, s in pares]


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
    # suporte_20/resistencia_20 são rolling(20).min/max() incluindo o candle
    # ATUAL — usar `penult` evita que o próprio candle de hoje "grude" no
    # nível e dispare G3/B3 quase sempre em movimentos rápidos.
    sup20        = float(penult.get("suporte_20",   preco))
    res20        = float(penult.get("resistencia_20",preco))
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

    tol_sr = atr * CONFIG.get("sr_tolerancia_atr", 1.5)
    if preco <= sup20 + tol_sr:
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

    if preco >= res20 - tol_sr:
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

    if vol_ratio >= CONFIG["volume_mult"]:
        sinais_baixa.append(f"📉 Volume {vol_ratio:.1f}x acima da média")
        ids_baixa.append("B10")
        score_baixa += 1

    bb_hi = float(ultimo.get("bb_upper", 0))
    if bb_hi > 0 and preco >= bb_hi * 0.99:
        sinais_baixa.append(f"📉 Preço na Bollinger superior: R${bb_hi:.2f}")
        ids_baixa.append("B11")
        score_baixa += 1

    # ── GATILHOS MATRIZ v2 (G12-G19/B12-B19) + REDUTORES ────────────────
    # Em modo "shadow" (default) só reportam nos campos *_v2; em "ativo"
    # somam/subtraem no score e os IDs entram nas listas principais.
    v2 = _avaliar_gatilhos_v2(df, ultimo, stoch_k, rsi, preco)

    if CONFIG.get("matriz_v2_gatilhos_mode") == "ativo":
        # IDs PUCK só entram nas listas principais (famílias/classe) quando o
        # flag próprio ativar — senão contaminariam calcular_familias com
        # pontos do registro enquanto o score os trata como 0 (shadow).
        ids_a, sinais_a = _filtrar_ids_puck_shadow(v2["ids_alta_v2"], v2["sinais_alta_v2"])
        ids_b, sinais_b = _filtrar_ids_puck_shadow(v2["ids_baixa_v2"], v2["sinais_baixa_v2"])
        sinais_alta.extend(sinais_a);   ids_alta.extend(ids_a)
        sinais_baixa.extend(sinais_b);  ids_baixa.extend(ids_b)
        # Redutores por direção; o score nunca fica negativo (spec §3)
        score_alta  = max(0, score_alta + v2["score_alta_v2"] - v2["redutores_alta_total"])
        score_baixa = max(0, score_baixa + v2["score_baixa_v2"] - v2["redutores_baixa_total"])

    return {
        "score_alta": score_alta, "score_baixa": score_baixa,
        "sinais_alta": sinais_alta, "sinais_baixa": sinais_baixa,
        "ids_alta": ids_alta, "ids_baixa": ids_baixa,
        "stoch_k": stoch_k, "rsi": rsi, "vol_ratio": vol_ratio,
        "v2": v2,
    }


def _avaliar_gatilhos_v2(df: pd.DataFrame, ultimo, stoch_k: float, rsi: float,
                         preco: float) -> dict:
    """Gatilhos novos da matriz v2 (spec 2026-07-01 §3) e redutores.
    Sempre avaliados (para telemetria shadow); quem decide se somam no score
    é o chamador, conforme CONFIG['matriz_v2_gatilhos_mode'].
    Indicador ausente/NaN nunca dispara — fail-safe para dfs antigos/testes."""
    def _val(key):
        x = ultimo.get(key)
        if x is None:
            return None
        x = float(x)
        return None if x != x else x  # NaN -> None

    ids_alta, ids_baixa = [], []
    sinais_alta, sinais_baixa = [], []
    score_alta = score_baixa = 0

    def _fire(lado: str, gid: str, texto: str, pontos: int):
        nonlocal score_alta, score_baixa
        if lado == "alta":
            ids_alta.append(gid); sinais_alta.append(texto); score_alta += pontos
        else:
            ids_baixa.append(gid); sinais_baixa.append(texto); score_baixa += pontos

    cci = _val("cci")
    extremo = CONFIG.get("cci_extremo", 100.0)
    if cci is not None:
        if cci < -extremo:
            _fire("alta", "G12", f"📈 CCI em zona extrema: {cci:.0f}", 2)
        elif cci > extremo:
            _fire("baixa", "B12", f"📉 CCI em zona extrema: {cci:.0f}", 2)

    mfi = _val("mfi")
    if mfi is not None:
        if mfi <= CONFIG.get("mfi_oversold", 30.0):
            _fire("alta", "G13", f"📈 MFI sobrevendido: {mfi:.0f}", 2)
        elif mfi >= CONFIG.get("mfi_overbought", 70.0):
            _fire("baixa", "B13", f"📉 MFI sobrecomprado: {mfi:.0f}", 2)

    # OBV: slope de regressão simples sobre os últimos 5 candles
    obv_slope = None
    if "obv" in df.columns and len(df) >= 5:
        obv_tail = df["obv"].tail(5).values.astype(float)
        if not any(x != x for x in obv_tail):
            obv_slope = float(pd.Series(obv_tail).diff().mean())
            if obv_slope > 0:
                _fire("alta", "G14", "📈 OBV subindo (fluxo comprador)", 1)
            elif obv_slope < 0:
                _fire("baixa", "B14", "📉 OBV caindo (fluxo vendedor)", 1)

    cmf = _val("cmf")
    if cmf is not None:
        if cmf > 0:
            _fire("alta", "G15", f"📈 CMF positivo: {cmf:.2f}", 1)
        elif cmf < 0:
            _fire("baixa", "B15", f"📉 CMF negativo: {cmf:.2f}", 1)

    st = _val("supertrend_dir")
    if st is not None:
        if int(st) == 1:
            _fire("alta", "G16", "📈 SuperTrend bullish", 1)
        else:
            _fire("baixa", "B16", "📉 SuperTrend bearish", 1)

    ema21_v = _val("ema21")
    if ema21_v is not None:
        if preco > ema21_v:
            _fire("alta", "G17", "📈 Preço acima da EMA21", 1)
        elif preco < ema21_v:
            _fire("baixa", "B17", "📉 Preço abaixo da EMA21", 1)

    adx = _val("adx")
    if adx is not None and adx >= CONFIG.get("adx_gatilho_min", 25.0):
        _fire("alta", "G18", f"📈 ADX forte: {adx:.0f}", 2)
        _fire("baixa", "B18", f"📉 ADX forte: {adx:.0f}", 2)

    bw = _val("bb_width")
    if bw is not None and bw < CONFIG.get("bw_compressao_max", 0.10):
        if stoch_k < CONFIG["stoch_oversold"] or rsi < CONFIG["rsi_oversold"]:
            _fire("alta", "G19", f"📈 Compressão Bollinger (BW {bw*100:.0f}%) + oscilador extremo", 2)
        if stoch_k > CONFIG["stoch_overbought"] or rsi > CONFIG["rsi_overbought"]:
            _fire("baixa", "B19", f"📉 Compressão Bollinger (BW {bw*100:.0f}%) + oscilador extremo", 2)

    # ── Gatilhos PUCK (rompimento HC + divergência de fluxo) ─────────────
    # Em shadow os pontos são 0: o ID entra na telemetria (trigger_outcomes)
    # sem afetar score mesmo se matriz_v2_gatilhos_mode virar "ativo".
    puck_ativo = CONFIG.get("puck_gatilhos_mode") == "ativo"
    hc_max = _val("hc_max"); hc_min = _val("hc_min")
    ema50_v = _val("ema50"); cmf_z = _val("cmf_z")
    low_v = _val("Low"); high_v = _val("High")
    z_min = CONFIG.get("cmf_z_gatilho", 1.0)

    if None not in (hc_max, ema21_v, ema50_v, cmf_z, low_v):
        if low_v > hc_max and cmf_z >= z_min and preco > ema21_v > ema50_v:
            _fire("alta", "G20",
                  f"📈 Rompimento do HC institucional (z-fluxo {cmf_z:.1f})",
                  3 if puck_ativo else 0)
    if None not in (hc_min, ema21_v, ema50_v, cmf_z, high_v):
        if high_v < hc_min and cmf_z <= -z_min and preco < ema21_v < ema50_v:
            _fire("baixa", "B20",
                  f"📉 Rompimento baixista do HC institucional (z-fluxo {cmf_z:.1f})",
                  3 if puck_ativo else 0)

    close_prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else None
    if cmf is not None and close_prev is not None:
        if cmf < 0 and preco > close_prev:
            _fire("alta", "G21",
                  "📈 Divergência de fluxo (venda absorvida, preço subiu)",
                  2 if puck_ativo else 0)
        elif cmf > 0 and preco < close_prev:
            _fire("baixa", "B21",
                  "📉 Divergência de fluxo (compra absorvida, preço caiu)",
                  2 if puck_ativo else 0)

    # Redutores (spec §3): fluxo contra o sinal e ADX fraco
    redutores_alta, redutores_baixa = [], []
    fluxo_contra_alta = (obv_slope is not None and obv_slope < 0) or (cmf is not None and cmf < 0)
    fluxo_contra_baixa = (obv_slope is not None and obv_slope > 0) or (cmf is not None and cmf > 0)
    if fluxo_contra_alta:
        redutores_alta.append({"id": "RED_FLUXO", "pontos": 2, "motivo": "OBV/CMF contra a compra"})
    if fluxo_contra_baixa:
        redutores_baixa.append({"id": "RED_FLUXO", "pontos": 2, "motivo": "OBV/CMF contra a venda"})
    if adx is not None and adx < CONFIG.get("adx_redutor_min", 20.0):
        red_adx = {"id": "RED_ADX", "pontos": 2, "motivo": f"ADX fraco ({adx:.0f})"}
        redutores_alta.append(red_adx)
        redutores_baixa.append(red_adx)

    return {
        "ids_alta_v2": ids_alta, "ids_baixa_v2": ids_baixa,
        "sinais_alta_v2": sinais_alta, "sinais_baixa_v2": sinais_baixa,
        "score_alta_v2": score_alta, "score_baixa_v2": score_baixa,
        "redutores_alta": redutores_alta, "redutores_baixa": redutores_baixa,
        "redutores_alta_total": sum(r["pontos"] for r in redutores_alta),
        "redutores_baixa_total": sum(r["pontos"] for r in redutores_baixa),
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

    # Calcula o spread da banda de entrada (ex: 3.5%, mas com mínimo de R$ 0.02 para cada lado)
    band_pct = CONFIG.get("buy_band_pct", 0.035)
    margem = max(preco_base_calculo * band_pct, 0.02)
    entrada_min  = max(0.01, round(preco_base_calculo - margem, 2))
    entrada_max  = round(preco_base_calculo + margem, 2)
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
        "gatilhos_v2_ids": estrutura.get("gatilhos_v2_ids", []),
        "score_v2_extra":  estrutura.get("score_v2_extra", 0),
        "redutores_v2":    estrutura.get("redutores_v2", []),
        "vetos_v2":        estrutura.get("vetos_v2", []),
        "classe_v2":       estrutura.get("classe_v2"),
        "razoes_downgrade_classe": estrutura.get("razoes_downgrade_classe", []),
        "divergencia_premio_pct": estrutura.get("divergencia_premio_pct"),
        "sizing_sugerido_pct": estrutura.get("sizing_sugerido_pct"),
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

        # Empate exato = evidências de alta e baixa igualmente fortes — sinal
        # ambíguo, não um viés a favor de CALL. Não emite.
        if score_alta == score_baixa:
            if verbose:
                logger.info(f"⚖ {ticker_base}: empate alta×baixa (score={score_alta}) — sinal ambíguo, não emitido")
            return None

        if score_alta > score_baixa:
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

        # ── VETOS TÉCNICOS (matriz v2 §4 — shadow por padrão) ────────────
        vetos_v2 = avaliar_vetos_tecnicos(ultimo, tipo_sinal, score)
        vetos_ativos = [v for v in vetos_v2 if v["modo"] == "ativo"]
        if vetos_ativos:
            if verbose:
                motivos = "; ".join(v["motivo"] for v in vetos_ativos)
                logger.info(f"🚫 {ticker_base}: veto técnico bloqueou emissão ({motivos})")
            return None

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

            # ── LIQUIDEZ / EXECUTABILIDADE (Fase 3 Matriz v2 — shadow) ────────
            # Em backtest (df_provided) NÃO consultamos dados de hoje: option_liquidity
            # e calendar_events refletem o presente e contaminariam sinais históricos
            # com look-ahead. Campos ficam None ("desconhecido" — não penaliza).
            is_backtest = df_provided is not None
            liquidity_info = None if is_backtest else obter_option_liquidity(
                ticker_base, datetime.now(timezone.utc).date()
            )
            estrutura["oi"] = liquidity_info.get("oi") if liquidity_info else None
            estrutura["bid"] = liquidity_info.get("bid") if liquidity_info else None
            estrutura["ask"] = liquidity_info.get("ask") if liquidity_info else None
            estrutura["spread_pct"] = liquidity_info.get("spread_pct") if liquidity_info else None
            estrutura["vxbr"] = liquidity_info.get("vxbr") if liquidity_info else None
            estrutura["evento_label"] = liquidity_info.get("evento_label") if liquidity_info else None

            # Fallback: sem evento em option_liquidity, consulta calendar_events
            # ANTES do veto shadow, para que o evento entre na decisão (fail-safe).
            if estrutura["evento_label"] is None and not is_backtest:
                estrutura["evento_label"] = obter_evento_na_data(datetime.now(timezone.utc).date())

            filtro_liq = avaliar_filtro_liquidez_shadow(
                estrutura["oi"],
                estrutura["spread_pct"],
                estrutura["vxbr"],
                estrutura["evento_label"],
                score,
            )
            estrutura["filtro_liquidez_decisao"] = filtro_liq["decisao"]
            estrutura["filtro_liquidez_motivo"] = filtro_liq["motivo"]
            # Shadow: NÃO bloqueia emissão — apenas telemetria (ativação na Fase 4)
            if filtro_liq["decisao"] != "normal" and verbose:
                logger.info(f"ℹ {ticker_base}: filtro liquidez (shadow) indicaria '{filtro_liq['decisao']}' — {filtro_liq['motivo']}")

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

            # ── TELEMETRIA MATRIZ v2 — Fase 1 (shadow) ────────────────────────
            v2 = gat.get("v2", {})
            if tipo_sinal == "CALL":
                gatilhos_v2_ids = v2.get("ids_alta_v2", [])
                score_v2_extra = v2.get("score_alta_v2", 0)
                redutores_v2 = v2.get("redutores_alta", [])
            else:
                gatilhos_v2_ids = v2.get("ids_baixa_v2", [])
                score_v2_extra = v2.get("score_baixa_v2", 0)
                redutores_v2 = v2.get("redutores_baixa", [])
            estrutura["gatilhos_v2_ids"] = gatilhos_v2_ids
            estrutura["score_v2_extra"] = score_v2_extra
            estrutura["redutores_v2"] = redutores_v2
            estrutura["vetos_v2"] = vetos_v2

            # ── CLASSE v2 E CAMPOS INFORMATIVOS (matriz v2 Fase 2) ──────────────
            classe_v2, razoes_downgrade = calcular_classe_v2(
                score + score_v2_extra - sum(r["pontos"] for r in redutores_v2),
                familias["breakdown"],
                score
            )
            estrutura["classe_v2"] = classe_v2
            estrutura["razoes_downgrade_classe"] = razoes_downgrade

            # Divergência prêmio real vs. modelado (Bloco 1 item 3 da matriz)
            premio_real = estrutura.get("preco_opcao", 0.0)
            premio_bs = estrutura.get("premio_bs", 0.0)
            div_premio = divergencia_premio_pct(premio_real, premio_bs)
            estrutura["divergencia_premio_pct"] = div_premio

            # Position sizing sugestivo (checklist §6.33 da matriz)
            sizing_sugerido = sizing_sugerido_pct(preco, ultimo.get("atr", 0.0), risco_pct=1.0)
            estrutura["sizing_sugerido_pct"] = sizing_sugerido

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
