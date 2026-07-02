"""
Score ponderado 0-100 para sinais de opções (CALL/PUT).

Espelha o algoritmo do scanner v4.0 calibrado sobre 31 sinais reais.
O somatório bruto dos pesos passa de 100 (os bônus são oportunistas); o score
final é capado em 100 (ver `min(int(score), 100)` no fim).

Pesos:
  Preço na faixa operável            12
  DTE no range [dte_minimo, _maximo]  8
  |Delta| 0.15-0.45 (OTM ideal)      10
  Tendência (0/8/16/20)              20
  MACD (cross/favor/aceleração)      18
  RSI na zona da direção             14
  Estocástico                         9
  ADX >= 25                           5
  Volume relativo                     8
  Bônus Bollinger                     4
  Bônus VWAP                          5
  Bônus Volatility Squeeze            5
  ────────────────────────────────  ─────
  Bruto                             118  (cap final = 100)
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


def avaliar_filtro_iv(iv_rank: float | None, iv_premium: float | None,
                       iv_rank_confiavel: bool, score_tecnico: int) -> dict:
    """
    Decide o filtro de volatilidade da Camada 1.3, recalibrado pela matriz v2
    (§2.5: banda operável 10-70, veto acima de 80). Os limites usam comparação
    estrita (>/<), então o valor exato do limite cai sempre na faixa "interna":
      IV Rank em [piso, atencao]                    -> normal
      IV Rank > atencao e <= bloqueio               -> exige score_tecnico >= 7
      IV Rank > bloqueio                            -> bloquear (IV cara, risco de IV crush)
      IV Rank < piso                                -> exige score_tecnico >= 7 (movimento lento)
    Defaults: bloqueio=80, atencao=70, piso=10 (CONFIG). O proxy iv_premium
    (sem histórico confiável) mantém os limites 1.2/1.5 e não tem piso — HV
    baixa demais já é penalizada pelo prêmio ínfimo da opção.
    Usa iv_rank quando confiável (>=60 du de histórico); senão cai no proxy iv_premium.
    Retorna {"decisao": str, "motivo": str}.
    """
    if iv_rank_confiavel and iv_rank is not None:
        if iv_rank < CONFIG.get("iv_rank_piso", 10):
            if score_tecnico >= 7:
                return {"decisao": "normal", "motivo": "IV muito baixa, mas score tecnico compensa"}
            return {"decisao": "exige_score_7",
                    "motivo": "IV muito baixa — movimento tende a ser lento, exige score tecnico >= 7"}
        cara = iv_rank > CONFIG.get("iv_rank_bloqueio", 80)
        media = iv_rank > CONFIG.get("iv_rank_atencao", 70)
    elif iv_premium is not None:
        cara, media = iv_premium > 1.5, iv_premium > 1.2
    else:
        return {"decisao": "normal", "motivo": "sem dado de IV — filtro inerte"}

    if cara:
        return {"decisao": "bloquear", "motivo": "IV cara — compra a seco bloqueada"}
    if media:
        if score_tecnico >= 7:
            return {"decisao": "normal", "motivo": "IV moderada, mas score tecnico compensa"}
        return {"decisao": "exige_score_7", "motivo": "IV moderada — exige score tecnico >= 7"}
    return {"decisao": "normal", "motivo": "IV normal"}


# ── Camada 2.1 — famílias de gatilhos e teto de contribuição ──────────────

# Taxonomia de famílias alinhada à matriz v2 (§5): OSCILADOR, MOMENTUM,
# TENDENCIA, ESTRUTURA, LIQUIDEZ. A antiga DIVERGENCIA foi absorvida por
# MOMENTUM (divergência RSI é sinal de momentum interno), junto com o MACD;
# MFI/OBV/CMF entrarão em MOMENTUM na Fase 1 da matriz.
GATILHOS: dict[str, dict] = {
    # Gatilhos de alta (G1-G11, docs/ESTRATEGIAS_OPCOES_B3.md)
    "G1":  {"familia": "OSCILADOR",   "pontos": 3},
    "G2":  {"familia": "OSCILADOR",   "pontos": 2},
    "G3":  {"familia": "ESTRUTURA",   "pontos": 2},
    "G4":  {"familia": "TENDENCIA",   "pontos": 2},
    "G5":  {"familia": "LIQUIDEZ",    "pontos": 1},
    "G6":  {"familia": "MOMENTUM",    "pontos": 2},
    "G7":  {"familia": "TENDENCIA",   "pontos": 2},
    "G8":  {"familia": "ESTRUTURA",   "pontos": 1},
    "G9":  {"familia": "MOMENTUM",    "pontos": 3},
    "G10": {"familia": "LIQUIDEZ",    "pontos": 3},
    "G11": {"familia": "TENDENCIA",   "pontos": 2},
    # Gatilhos de baixa (B1-B11)
    "B1": {"familia": "OSCILADOR",   "pontos": 3},
    "B2": {"familia": "OSCILADOR",   "pontos": 2},
    "B3": {"familia": "ESTRUTURA",   "pontos": 2},
    "B4": {"familia": "TENDENCIA",   "pontos": 2},
    "B5": {"familia": "TENDENCIA",   "pontos": 2},
    "B6": {"familia": "MOMENTUM",    "pontos": 2},
    "B7": {"familia": "MOMENTUM",    "pontos": 3},
    "B8": {"familia": "LIQUIDEZ",    "pontos": 3},
    "B9": {"familia": "TENDENCIA",   "pontos": 2},
    "B10": {"familia": "LIQUIDEZ",   "pontos": 1},
    "B11": {"familia": "ESTRUTURA",  "pontos": 1},
    # Matriz v2 Fase 1 (spec 2026-07-01 §3) — gatilhos novos, espelhados G/B.
    # Pesos máx. 2: os pesos 3 são reservados aos âncora (G1/B1, G9/B7, G10/B8).
    "G12": {"familia": "OSCILADOR", "pontos": 2},   # CCI < -100
    "G13": {"familia": "MOMENTUM",  "pontos": 2},   # MFI <= 30
    "G14": {"familia": "MOMENTUM",  "pontos": 1},   # OBV subindo (5 candles)
    "G15": {"familia": "MOMENTUM",  "pontos": 1},   # CMF > 0
    "G16": {"familia": "TENDENCIA", "pontos": 1},   # SuperTrend bullish
    "G17": {"familia": "TENDENCIA", "pontos": 1},   # Close > EMA21
    "G18": {"familia": "TENDENCIA", "pontos": 2},   # ADX >= 25
    "G19": {"familia": "ESTRUTURA", "pontos": 2},   # BW < 10% + oscilador extremo
    "B12": {"familia": "OSCILADOR", "pontos": 2},   # CCI > +100
    "B13": {"familia": "MOMENTUM",  "pontos": 2},   # MFI >= 70
    "B14": {"familia": "MOMENTUM",  "pontos": 1},   # OBV caindo (5 candles)
    "B15": {"familia": "MOMENTUM",  "pontos": 1},   # CMF < 0
    "B16": {"familia": "TENDENCIA", "pontos": 1},   # SuperTrend bearish
    "B17": {"familia": "TENDENCIA", "pontos": 1},   # Close < EMA21
    "B18": {"familia": "TENDENCIA", "pontos": 2},   # ADX >= 25
    "B19": {"familia": "ESTRUTURA", "pontos": 2},   # BW < 10% + oscilador extremo
}


def calcular_familias(gatilhos_ids: list[str]) -> dict:
    """
    Aplica o teto de contribuição por família (Camada 2.1) sobre os gatilhos
    que dispararam. Cada família contribui no máximo `familia_cap_<nome>`
    (CONFIG) ao score, mesmo que a soma bruta dos gatilhos da família exceda
    o teto. `familias_ativas` conta famílias distintas com pelo menos 1
    gatilho disparado (antes do cap) — é a "largura de consenso".
    IDs fora do registro `GATILHOS` são ignorados (não derruba o cálculo).
    Retorna {"score_capped": int, "familias_ativas": int, "breakdown": dict}.
    """
    caps = {
        "OSCILADOR":   CONFIG.get("familia_cap_oscilador", 4),
        "MOMENTUM":    CONFIG.get("familia_cap_momentum", 4),
        "TENDENCIA":   CONFIG.get("familia_cap_tendencia", 4),
        "ESTRUTURA":   CONFIG.get("familia_cap_estrutura", 4),
        "LIQUIDEZ":    CONFIG.get("familia_cap_liquidez", 3),
    }
    bruto: dict[str, int] = {}
    for gid in gatilhos_ids:
        info = GATILHOS.get(gid)
        if not info:
            continue
        bruto[info["familia"]] = bruto.get(info["familia"], 0) + info["pontos"]

    breakdown = {fam: min(pts, caps.get(fam, pts)) for fam, pts in bruto.items()}
    return {
        "score_capped": sum(breakdown.values()),
        "familias_ativas": len(bruto),
        "breakdown": breakdown,
    }


def classificar_setup(breakdown: dict) -> str:
    """
    Classifica o sinal por família dominante (Camada 2.2):
      REVERSAO    se OSCILADOR+MOMENTUM+ESTRUTURA > TENDENCIA
      CONTINUACAO se TENDENCIA > OSCILADOR+MOMENTUM+ESTRUTURA
      HIBRIDO     em caso de empate (inclusive 0 a 0)
    MOMENTUM substitui a antiga DIVERGENCIA no lado de reversão — MACD e
    divergência já contavam nesse lado antes do remapeamento (via OSCILADOR
    e DIVERGENCIA respectivamente), então o comportamento é preservado.
    `breakdown` é o dict {familia: pontos} retornado por `calcular_familias`
    (já com os tetos aplicados).
    """
    reversao = (breakdown.get("OSCILADOR", 0) + breakdown.get("MOMENTUM", 0)
                + breakdown.get("ESTRUTURA", 0))
    continuacao = breakdown.get("TENDENCIA", 0)
    if reversao > continuacao:
        return "REVERSAO"
    if continuacao > reversao:
        return "CONTINUACAO"
    return "HIBRIDO"


def avaliar_vetos_tecnicos(ultimo, tipo_sinal: str, score_tecnico: int) -> list[dict]:
    """
    Vetos técnicos da matriz v2 (§4), avaliados sobre a última linha de
    indicadores. Retorna a lista de vetos DISPARADOS, cada um com o modo
    vigente ("shadow" reporta, "ativo" bloqueia — o chamador decide):
      VETO_ADX        — ADX < adx_veto_min (lateralidade; reversão vira chute)
      VETO_SUPERTREND — SuperTrend contra a direção do sinal
      VETO_BW         — Bollinger aberto (BW > bw_aberto_min) com preço no
                        meio das bandas (0,35 < %B < 0,65): errático
      EMA200_CONTRA   — não veta: exige score_tecnico >= min_score + 2
    Indicador ausente (NaN/None) nunca dispara veto — fail-safe.
    """
    up = tipo_sinal.upper() == "CALL"
    vetos: list[dict] = []

    adx = ultimo.get("adx")
    if adx is not None and not _isnan(adx) and float(adx) < CONFIG.get("adx_veto_min", 15.0):
        vetos.append({"id": "VETO_ADX", "modo": CONFIG.get("veto_adx_mode", "shadow"),
                      "motivo": f"ADX {float(adx):.0f} < {CONFIG.get('adx_veto_min', 15.0):.0f} — mercado lateral"})

    st = ultimo.get("supertrend_dir")
    if st is not None and not _isnan(st):
        contra = (int(st) == -1) if up else (int(st) == 1)
        if contra:
            vetos.append({"id": "VETO_SUPERTREND", "modo": CONFIG.get("veto_supertrend_mode", "shadow"),
                          "motivo": f"SuperTrend {'bearish' if up else 'bullish'} contra o sinal"})

    bw = ultimo.get("bb_width")
    bb_pct = ultimo.get("bb_pct")
    if (bw is not None and bb_pct is not None and not _isnan(bw) and not _isnan(bb_pct)
            and float(bw) > CONFIG.get("bw_aberto_min", 0.25) and 0.35 < float(bb_pct) < 0.65):
        vetos.append({"id": "VETO_BW", "modo": CONFIG.get("veto_bw_mode", "shadow"),
                      "motivo": f"Bandas abertas (BW {float(bw)*100:.0f}%) com preço no meio — sem direção"})

    ema200 = ultimo.get("ema200")
    close = ultimo.get("Close")
    if ema200 is not None and close is not None and not _isnan(ema200) and not _isnan(close):
        contra_200 = (float(close) < float(ema200)) if up else (float(close) > float(ema200))
        if contra_200 and score_tecnico < CONFIG.get("min_score", 5) + 2:
            vetos.append({"id": "EMA200_CONTRA", "modo": CONFIG.get("veto_ema200_mode", "shadow"),
                          "motivo": "Sinal contra a EMA200 exige score minimo +2"})

    return vetos


def _isnan(x) -> bool:
    try:
        return x != x  # NaN é o único valor diferente de si mesmo
    except Exception:
        return False


def calcular_classe_v2(score: int, familias_breakdown: dict,
                       score_tecnico: int) -> tuple[str, list[str]]:
    """Classifica o sinal em classe A/B/C conforme a matriz v2 (spec §4).

    Retorna: (classe, [razoes_downgrade])

    Regra dos 60%: se uma família responde por >60% do score total, rebaixa
    uma classe (A→B, B→C). Desempate A/B via bônus horário é responsabilidade
    do chamador (não aplicado aqui).
    """
    razoes_downgrade = []

    # Thresholds de score para cada classe (antes de redutores/bônus)
    if score >= 12 and len([f for f in familias_breakdown.values() if f > 0]) >= 5:
        classe_base = "A"
    elif score >= 8 and len([f for f in familias_breakdown.values() if f > 0]) >= 4:
        classe_base = "B"
    else:
        return ("C", ["score ou famílias insuficientes"])

    # Regra dos 60%: nenhuma família pode responder por >60% do total (estrito)
    score_total = sum(familias_breakdown.values())
    if score_total > 0:
        for familia, pontos in familias_breakdown.items():
            pct = (pontos / score_total) * 100
            if pct >= 60.1:  # margem para 60.0% = OK, 60.1% = downgrade
                razoes_downgrade.append(f"{familia} responde por {pct:.0f}% (>60%)")
                # Downgrade: A→B, B→C
                classe_base = "B" if classe_base == "A" else "C"
                break

    # Se classe for A, verificar critério extra: score_tecnico deve estar
    # em zona "focada" (RSI 30–70, oscilador relevante). Próxima versão pode
    # refinar isso com dados em tempo real; por enquanto, apenas registra.
    if classe_base == "A" and (score_tecnico < 3 or score_tecnico > 8):
        razoes_downgrade.append(f"score_tecnico {score_tecnico} fora da zona ideal para classe A")

    return (classe_base, razoes_downgrade)


def divergencia_premio_pct(premio_real: float, premio_modelado: float) -> float | None:
    """Divergência entre prêmio real vs. modelado (spec 2026-07-01 §5).
    Bloco 1 item 3 da matriz: prêmio real vs. modelado <15% (informativo shadow).
    Retorna percentual positivo (real-modelado)/modelado ou None se modelado ≤0."""
    if premio_modelado <= 0:
        return None
    return ((premio_real - premio_modelado) / premio_modelado) * 100


def sizing_sugerido_pct(preco: float, atr: float, risco_pct: float = 1.0) -> float:
    """Position sizing sugestivo conforme checklist §6.33 da matriz v2.
    Fórmula: risco_pct / (atr / preco), i.e., quanto do capital arriscar
    se o stop está a ATR de distância.
    Ex: preco=100, atr=2 (2% de stop), risco=1% → 1%/2% = 0.5% do capital.
    Retorna percentual recomendado."""
    if preco <= 0 or atr <= 0:
        return 0.0
    atr_pct = (atr / preco) * 100
    if atr_pct == 0:
        return 0.0
    return min(risco_pct / atr_pct, 5.0)  # cap a 5% para segurança


def parametros_setup_shadow(setup: str) -> dict:
    """
    Parâmetros de estrutura de opção que SERIAM usados por setup (Camada 2.2).
    Shadow apenas — não afeta a estrutura real da opção, que continua usando
    os parâmetros únicos atuais de CONFIG. Valores da tabela do plano,
    hipóteses a validar na Camada 5. HIBRIDO usa os mesmos valores da
    Continuação (que já coincidem com os defaults atuais de produção:
    alvo2_pct=2.50, stop_pct=-0.43), por não haver família dominante que
    justifique desviar.
    """
    if setup == "REVERSAO":
        return {"otm_mult": 0.7, "dte_min": 10, "dte_max": 25,
                "alvo2_pct": 1.50, "stop_pct": -0.35}
    return {"otm_mult": 1.0, "dte_min": 5, "dte_max": 20,
            "alvo2_pct": 2.50, "stop_pct": -0.43}
