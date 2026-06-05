import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from backend.core.config import CONFIG, OTM_POR_ATIVO, OTM_DEFAULT, is_reentrada_valida, registrar_sinal, score_horario
from backend.core.cache import cache_get_df, cache_set_df
from backend.domain.indicators import (
    calcular_indicadores,
    detectar_divergencia,
    encontrar_zonas_demanda_oferta,
    detectar_canal_linear
)
from backend.domain.options_math import mes_vencimento_ideal, estimar_iv_historica, estimar_premio_otm
from backend.services.data_providers import get_real_options_from_opcoes_net, fetch_brapi_historical
from backend.domain.greeks import calculate_greeks, implied_volatility
from backend.domain.scoring import score_ponderado

logger = logging.getLogger("b3_scanner")

def analisar_ativo(ticker: str, nome: str, interval: str = "1d", verbose: bool = False, df_provided: pd.DataFrame = None, indicators_calculated: bool = False) -> dict | None:
    """
    Analisa um ativo e retorna sinal de opção se critérios forem atendidos.
    Pode receber df_provided para testes e backtest, ou baixar direto via yfinance.
    """
    try:
        ticker_base = ticker.replace(".SA", "")
        if df_provided is None and not is_reentrada_valida(ticker_base):
            if verbose:
                logger.info(f"↩ {ticker_base}: sinal recente (<{CONFIG['reentrada_min_dias']}d), pulando")
            return None

        if df_provided is not None:
            df = df_provided.copy()
        else:
            period = "6mo" if interval == "1d" else "730d"
            cache_key = f"ohlcv:{ticker}:{interval}"
            df = cache_get_df(cache_key)

            if df is None:
                max_retries = 3
                for tentativa in range(max_retries):
                    try:
                        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
                        if df is not None and not df.empty:
                            cache_set_df(cache_key, df, ttl=300)  # 5 min cache
                            break
                    except Exception as e:
                        if tentativa == max_retries - 1:
                            if verbose:
                                logger.warning(f"yfinance falhou para {ticker} após {max_retries} tentativas: {e}. Tentando brapi...")
                            df = None
                            break
                        import time
                        time.sleep(2 ** tentativa) # Exponential backoff: 1s, 2s, 4s

                # Fallback brapi se yfinance falhou ou retornou vazio
                if df is None or df.empty:
                    df = fetch_brapi_historical(ticker, range_=period, interval=interval)
                    if df is not None and not df.empty:
                        cache_set_df(cache_key, df, ttl=300)
                        if verbose:
                            logger.info(f"📡 {ticker}: dados via brapi (fallback)")
        
        if df is None or len(df) < 30:
            return None

        if not indicators_calculated:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = calcular_indicadores(df)
            df.dropna(inplace=True)
        
        if len(df) < 5:
            return None

        ultimo    = df.iloc[-1]
        penult    = df.iloc[-2]

        preco     = float(ultimo["Close"])
        volume    = float(ultimo["Volume"])
        vol_med   = float(ultimo.get("vol_media_20", volume))

        if vol_med < CONFIG["min_volume_acoes"]:
            return None

        sinais_alta, sinais_baixa = [], []
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

        # ── GATILHOS DE ALTA ─────────────────────────────────────────────
        if (stoch_k < CONFIG["stoch_oversold"] + 10 and stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev):
            sinais_alta.append("📈 Estocástico: cruzamento altista em sobrevenda")
            score_alta += 3

        if rsi < CONFIG["rsi_oversold"]:
            sinais_alta.append(f"📈 RSI sobrevenda: {rsi:.1f}")
            score_alta += 2

        if preco <= sup20 + atr:
            sinais_alta.append(f"📈 Preço em suporte 20D: R${sup20:.2f}")
            score_alta += 2

        if ema9 > ema21 and ema9_prev <= ema21_prev:
            sinais_alta.append("📈 EMA9 cruzou acima EMA21")
            score_alta += 2

        if vol_ratio >= CONFIG["volume_mult"]:
            sinais_alta.append(f"📈 Volume {vol_ratio:.1f}x acima da média")
            score_alta += 1

        if macd_d > 0 and macd_d_prev <= 0:
            sinais_alta.append("📈 MACD cruzou zero (momentum altista)")
            score_alta += 2

        ultimos_fundos = df[df["is_fundo_local"]].tail(3)["Low"].values
        if (len(ultimos_fundos) >= 3 and all(ultimos_fundos[i] < ultimos_fundos[i+1] for i in range(2))):
            sinais_alta.append("📈 Fundos ascendentes (reversão)")
            score_alta += 2

        if bb_lo > 0 and preco <= bb_lo * 1.01:
            sinais_alta.append(f"📈 Preço na Bollinger inferior: R${bb_lo:.2f}")
            score_alta += 1

        div_alta, _ = detectar_divergencia(df, janela=5)
        if div_alta:
            sinais_alta.append("📈 Divergência altista RSI (preço cai, RSI sobe)")
            score_alta += 3

        zona_dem, _ = encontrar_zonas_demanda_oferta(df)
        if zona_dem:
            sinais_alta.append("📈 Preço em zona de demanda histórica")
            score_alta += 3

        canal_alt, _, slope = detectar_canal_linear(df)
        if canal_alt:
            sinais_alta.append(f"📈 Canal altista (slope={slope:.3f})")
            score_alta += 2

        # ── GATILHOS DE BAIXA ────────────────────────────────────────────
        if (stoch_k > CONFIG["stoch_overbought"] - 10 and stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev):
            sinais_baixa.append("📉 Estocástico: cruzamento baixista em sobrecompra")
            score_baixa += 3

        if rsi > CONFIG["rsi_overbought"]:
            sinais_baixa.append(f"📉 RSI sobrecompra: {rsi:.1f}")
            score_baixa += 2

        if preco >= res20 - atr:
            sinais_baixa.append(f"📉 Preço em resistência 20D: R${res20:.2f}")
            score_baixa += 2

        if ema9 < ema21 and ema9_prev >= ema21_prev:
            sinais_baixa.append("📉 EMA9 cruzou abaixo EMA21")
            score_baixa += 2

        ultimos_topos = df[df["is_topo_local"]].tail(3)["High"].values
        if (len(ultimos_topos) >= 3 and all(ultimos_topos[i] > ultimos_topos[i+1] for i in range(2))):
            sinais_baixa.append("📉 Topos descendentes (tendência de baixa)")
            score_baixa += 2

        if macd_d < 0 and macd_d_prev >= 0:
            sinais_baixa.append("📉 MACD cruzou zero negativamente")
            score_baixa += 2

        _, div_baixa = detectar_divergencia(df, janela=5)
        if div_baixa:
            sinais_baixa.append("📉 Divergência baixista RSI (preço sobe, RSI cai)")
            score_baixa += 3

        _, zona_ofe = encontrar_zonas_demanda_oferta(df)
        if zona_ofe:
            sinais_baixa.append("📉 Preço em zona de oferta histórica")
            score_baixa += 3

        _, canal_bx, slope_bx = detectar_canal_linear(df)
        if canal_bx:
            sinais_baixa.append(f"📉 Canal baixista (slope={slope_bx:.3f})")
            score_baixa += 2

        # ── SCORE DE HORÁRIO integrado ───────────────────────
        bonus_horario = score_horario()
        score_alta  += bonus_horario
        score_baixa += bonus_horario

        # ── DECISÃO ──────────────────────────────────────────────────────
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

        # ── ESTRUTURA DO SINAL ────────────────────────────────────────────
        dist_otm   = OTM_POR_ATIVO.get(ticker_base, OTM_DEFAULT)
        strike_ref = round(
            preco * (1 - dist_otm) if tipo_sinal == "PUT" else preco * (1 + dist_otm), 2
        )

        mes_v, ano_v, dte = mes_vencimento_ideal()
        iv           = estimar_iv_historica(df, interval=interval)
        premio_est   = estimar_premio_otm(preco, strike_ref, dte, iv, tipo_sinal)

        # --- INTEGRAÇÃO COM DADOS REAIS (opcoes.net.br) ---
        opcao_real = get_real_options_from_opcoes_net(ticker_base, tipo_sinal, strike_ref)
        if opcao_real:
            strike_ref = opcao_real["strike_real"]
            preco_tela = opcao_real["preco_tela"]
            ticker_opcao = opcao_real["ticker_opcao"]
        else:
            preco_tela = None
            ticker_opcao = "N/A (S/ Liquidez)"

        # Greeks: se há preço REAL de tela, derivamos IV de mercado e usamos no BS
        T = max(dte, 1) / 252
        iv_mercado = None
        sigma_para_greeks = iv
        if preco_tela:
            try:
                iv_mercado = implied_volatility(
                    preco, strike_ref, T, preco_tela, tipo_sinal, sigma_init=iv,
                )
                if 0.05 <= iv_mercado <= 3.0:
                    sigma_para_greeks = iv_mercado
            except Exception:
                iv_mercado = None
        greeks = calculate_greeks(preco, strike_ref, T, sigma_para_greeks, tipo_sinal)

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
        rr_alvo1     = round((alvo1 - preco_base_calculo) / risco, 2) if risco > 0 else 0
        rr_alvo2     = round((alvo2 - preco_base_calculo) / risco, 2) if risco > 0 else 0
        rr_final     = round((alvo_final - preco_base_calculo) / risco, 2) if risco > 0 else 0

        if rr_alvo1 < CONFIG["rr_minimo"]:
            if verbose:
                logger.info(f"⚠ {ticker_base}: R/R Alvo1={rr_alvo1:.2f} < {CONFIG['rr_minimo']} → rejeitado")
            return None

        if df_provided is None:
            registrar_sinal(ticker_base)

        # ── SHADOW MODE: calcula score ponderado em paralelo ───────────────
        try:
            score_pond = score_ponderado(
                ultimo, penult,
                option_price=(preco_tela if preco_tela else premio_est),
                dte=dte, greeks=greeks, direction=tipo_sinal,
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

        return {
            "emoji":        emoji,
            "ticker":       ticker_base,
            "nome":         nome,
            "tipo_sinal":   tipo_sinal,
            "direcao":      direcao_label,
            "preco_acao":   preco,
            "ticker_opcao": ticker_opcao,
            "strike_ref":   strike_ref,
            "dist_otm_pct": dist_otm * 100,
            "iv_hist":      round(iv * 100, 1),
            "iv_mercado":   round(iv_mercado * 100, 1) if iv_mercado else None,
            "dte":          dte,
            "mes_venc":     mes_v,
            "ano_venc":     ano_v,
            "premio_est":   premio_est,
            "preco_tela":   preco_tela,
            "entrada_min":  entrada_min,
            "entrada_max":  entrada_max,
            "alvo1":        alvo1,
            "alvo2":        alvo2,
            "alvo_final":   alvo_final,
            "stop":         stop,
            "book_until":   book_until,
            "greeks":       greeks,
            "score_ponderado": shadow_score,
            "ponderado_passou": shadow_signal,
            "ponderado_reasons": shadow_reasons,
            "rr_alvo1":     rr_alvo1,
            "rr_alvo2":     rr_alvo2,
            "rr_final":     rr_final,
            "score":        score,
            "stoch_k":      stoch_k,
            "rsi":          rsi,
            "vol_ratio":    vol_ratio,
            "gatilhos":     gatilhos,
        }

    except Exception as e:
        if verbose:
            logger.error(f"✗ Erro {ticker}: {e}")
        return None
