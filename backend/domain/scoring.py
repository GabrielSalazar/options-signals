"""
Score ponderado 0-100 para sinais de opções (CALL/PUT).

Espelha o algoritmo do scanner v4.0 calibrado sobre 31 sinais reais.
Pesos:
  Preço na faixa operável         12
  DTE 10-60 dias                   8
  |Delta| 0.15-0.45 (OTM ideal)   10
  Tendência (0/8/16/20)           20
  MACD (cross/favor/aceleração)   18
  RSI na zona da direção          14
  Estocástico                      9
  ADX >= 25                        5
  Volume relativo                  8
  Bônus Bollinger                  4
  ─────────────────────────────  ─────
  Teto                           100
"""
from backend.core.config import CONFIG


def _trend_points(t: int) -> int:
    return {0: 0, 1: 8, 2: 16, 3: 20}.get(int(t), 20)


def score_ponderado(last, prev, option_price: float, dte: int,
                    greeks: dict, direction: str = "CALL") -> dict:
    """
    last/prev: linhas (Series) do df de indicadores.
    Retorna {"score": int, "signal": bool, "reasons": list[str]}.
    """
    score, reasons = 0, []
    up = direction.upper() == "CALL"

    # 1. Preço na faixa operável (12)
    pmin = CONFIG.get("option_price_min", 0.10)
    pmax = CONFIG.get("option_price_max", 3.00)
    if pmin <= option_price <= pmax:
        score += 12; reasons.append(f"✅ Preço R${option_price:.2f} na faixa")
    else:
        reasons.append(f"❌ Preço fora da faixa: R${option_price:.2f}")

    # 2. DTE ideal (8)
    if CONFIG.get("dte_minimo", 10) <= dte <= CONFIG.get("dte_maximo", 60):
        score += 8; reasons.append(f"✅ Vencimento em {dte} dias")
    else:
        reasons.append(f"⚠️ DTE fora do ideal: {dte}d")

    # 3. Delta OTM ideal (10)
    delta_abs = abs(greeks.get("delta", 0.30))
    if CONFIG.get("delta_min", 0.15) <= delta_abs <= CONFIG.get("delta_max", 0.45):
        score += 10; reasons.append(f"✅ Delta {delta_abs:.2f} (OTM ideal)")
    elif delta_abs < CONFIG.get("delta_min", 0.15):
        reasons.append(f"⚠️ Delta {delta_abs:.2f} (muito OTM)")
    else:
        score += 5; reasons.append(f"ℹ️ Delta {delta_abs:.2f} (ATM/ITM)")

    # 4. Tendência (até 20)
    trend = int(last.get("trend_up" if up else "trend_down", 0))
    pts = _trend_points(trend)
    score += pts
    direc = "alta" if up else "baixa"
    if pts >= 16:
        reasons.append(f"✅ Tendência de {direc} ({trend}/3)")
    else:
        reasons.append(f"⚠️ Tendência de {direc} fraca ({trend}/3)")

    # 5. MACD (até 18)
    hist  = float(last.get("macd_diff", 0))
    prev_h = float(prev.get("macd_diff", 0))
    favor    = (hist > 0) if up else (hist < 0)
    growing  = (hist > prev_h) if up else (hist < prev_h)
    cross_up   = (hist > 0) and (prev_h <= 0)
    cross_down = (hist < 0) and (prev_h >= 0)
    if (up and cross_up) or (not up and cross_down):
        score += 18; reasons.append(f"✅ MACD cruzamento {'bullish' if up else 'bearish'}")
    elif favor and growing:
        score += 12; reasons.append("✅ MACD a favor e acelerando")
    elif favor:
        score += 7; reasons.append("⚠️ MACD a favor (estável)")
    else:
        reasons.append("❌ MACD contra a operação")

    # 6. RSI (até 14)
    rsi = float(last.get("rsi", 50))
    if up:
        if 35 <= rsi <= 60:
            score += 14; reasons.append(f"✅ RSI {rsi:.1f} (recuperação)")
        elif rsi < 35:
            score += 10; reasons.append(f"✅ RSI {rsi:.1f} (sobrevendido)")
        elif 60 < rsi <= 68:
            score += 6; reasons.append(f"⚠️ RSI {rsi:.1f} (esticando)")
        else:
            reasons.append(f"❌ RSI {rsi:.1f} (sobrecomprado)")
    else:
        if 40 <= rsi <= 65:
            score += 14; reasons.append(f"✅ RSI {rsi:.1f} (perdendo força)")
        elif rsi > 70:
            score += 10; reasons.append(f"✅ RSI {rsi:.1f} (sobrecomprado)")
        elif 32 <= rsi < 40:
            score += 6; reasons.append(f"⚠️ RSI {rsi:.1f} (esticando p/ baixo)")
        else:
            reasons.append(f"❌ RSI {rsi:.1f} (sobrevendido)")

    # 7. Estocástico (até 9)
    k  = float(last.get("stoch_k", 50)); d  = float(last.get("stoch_d", 50))
    pk = float(prev.get("stoch_k", 50)); pdv = float(prev.get("stoch_d", 50))
    if up:
        if k < 25:
            score += 9; reasons.append(f"✅ Estocástico sobrevendido (K={k:.0f})")
        elif (k > d) and (pk <= pdv) and k < 65:
            score += 9; reasons.append(f"✅ Estocástico cruzou p/ cima (K={k:.0f})")
        else:
            reasons.append(f"ℹ️ Estocástico K={k:.0f}/D={d:.0f}")
    else:
        if k > 75:
            score += 9; reasons.append(f"✅ Estocástico sobrecomprado (K={k:.0f})")
        elif (k < d) and (pk >= pdv) and k > 35:
            score += 9; reasons.append(f"✅ Estocástico cruzou p/ baixo (K={k:.0f})")
        else:
            reasons.append(f"ℹ️ Estocástico K={k:.0f}/D={d:.0f}")

    # 8. ADX (até 5)
    adx = float(last.get("adx", 20))
    if adx >= 25:
        score += 5; reasons.append(f"✅ ADX forte: {adx:.0f}")
    else:
        reasons.append(f"ℹ️ ADX fraco: {adx:.0f}")

    # 9. Volume relativo (até 8)
    vol = float(last.get("vol_ratio", 1.0))
    if vol >= 1.5:
        score += 8; reasons.append(f"✅ Volume {vol:.1f}x a média")
    elif vol >= 1.0:
        score += 4; reasons.append(f"ℹ️ Volume normal ({vol:.1f}x)")
    else:
        reasons.append(f"⚠️ Volume fraco ({vol:.1f}x)")

    # 10. Bônus Bollinger (até 4)
    bb = float(last.get("bb_pct", 0.5))
    if up and bb < 0.25:
        score += 4; reasons.append("✅ Bollinger: perto da banda inferior")
    elif (not up) and bb > 0.75:
        score += 4; reasons.append("✅ Bollinger: perto da banda superior")

    # 11. Bônus VWAP (até 5)
    vwap = float(last.get("vwap", 0.0))
    close = float(last.get("Close", 0.0))
    if vwap > 0:
        if up and close > vwap:
            score += 5; reasons.append("✅ Preço acima do VWAP (força compradora)")
        elif (not up) and close < vwap:
            score += 5; reasons.append("✅ Preço abaixo do VWAP (força vendedora)")

    # 12. Bônus Volatility Squeeze (até 5)
    bb_u, bb_l = float(last.get("bb_upper", 0)), float(last.get("bb_lower", 0))
    kc_u, kc_l = float(last.get("kc_upper", 0)), float(last.get("kc_lower", 0))
    if bb_u > 0 and kc_u > 0:
        # Se as bandas de Bollinger entrarem nos canais de Keltner, há Volatility Squeeze
        if bb_u < kc_u and bb_l > kc_l:
            score += 5; reasons.append("🔥 Volatility Squeeze (Expansão Iminente)")

    score = min(int(score), 100)
    return {
        "score": score,
        "signal": score >= CONFIG.get("min_score_ponderado", 60),
        "reasons": reasons,
    }
