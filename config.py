import os
from datetime import datetime, timedelta

CONFIG = {
    # ── Indicadores ────────────────────────────────────────────────────────
    "stoch_k_period":    14,
    "stoch_d_period":    3,
    "stoch_smooth":      3,
    "stoch_oversold":    25,
    "stoch_overbought":  75,
    "rsi_period":        14,
    "rsi_oversold":      35,
    "rsi_overbought":    65,
    "ema_fast":          9,
    "ema_slow":          21,
    "volume_mult":       1.5,

    # ── Gestão de risco ────────────────────────────────────────────────────
    "stop_pct":          -0.42,
    "alvo1_pct":         0.25,
    "alvo2_pct":         1.50,
    "alvo_final_pct":    4.00,
    "rr_minimo":         0.8,

    # ── Filtros ────────────────────────────────────────────────────────────
    "min_volume_diario":    1_000_000,
    "min_variacao_gatilho": 0.015,
    "lookback_dias":        30,
    "min_score":            5,

    # ── DTE (Days to Expiration) ───────────────────────────────────────────
    "dte_minimo":   10,
    "dte_maximo":   45,

    # ── Reentrada ──────────────────────────────────────────────────────────
    "reentrada_min_dias": 3,

    # ── Telegram (opcional) ───────────────────────────────────────────────
    "telegram_token":   os.getenv("TELEGRAM_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
}

ATIVOS_B3 = {
    "ITUB4.SA":  "Itaú Unibanco",
    "BBDC4.SA":  "Bradesco PN",
    "BBAS3.SA":  "Banco do Brasil",
    "SANB11.SA": "Santander Brasil",
    "B3SA3.SA":  "B3 S.A.",
    "BPAC11.SA": "BTG Pactual",
    "BBSE3.SA":  "BB Seguridade",
    "VALE3.SA":  "Vale",
    "PETR4.SA":  "Petrobras PN",
    "PETR3.SA":  "Petrobras ON",
    "SUZB3.SA":  "Suzano",
    "KLBN11.SA": "Klabin",
    "GGBR4.SA":  "Gerdau",
    "CSNA3.SA":  "CSN",
    "USIM5.SA":  "Usiminas",
    "BRKM5.SA":  "Braskem",
    "GOAU4.SA":  "Gerdau Metalúrgica",
    "MGLU3.SA":  "Magazine Luiza",
    "LREN3.SA":  "Lojas Renner",
    "RADL3.SA":  "RD Saúde",
    "ABEV3.SA":  "Ambev",
    "ASAI3.SA":  "Assaí Atacadista",
    "WEGE3.SA":  "WEG",
    "EGIE3.SA":  "Engie Brasil",
    "BRAV3.SA":  "Brava Energia",
    "BEEF3.SA":  "Minerva Foods",
    "MRVE3.SA":  "MRV Engenharia",
    "BOVA11.SA": "ETF IBOVESPA",
    "RANI3.SA":  "Irani Papel",
}

OTM_POR_ATIVO = {
    "MGLU3":  0.12,  "BRKM5": 0.10,  "USIM5":  0.10,  "ASAI3": 0.10,
    "BEEF3":  0.12,  "MRVE3": 0.10,  "BRAV3":  0.10,  "CSNA3": 0.09,
    "VALE3":  0.07,  "SUZB5": 0.07,  "LREN3":  0.07,  "RADL3": 0.07,
    "GGBR4":  0.08,  "GOAU4": 0.08,  "PETR4":  0.06,  "PETR3": 0.06,
    "ITUB4":  0.05,  "BBDC4": 0.05,  "ABEV3":  0.05,  "BBSE3": 0.05,
    "BBAS3":  0.05,  "SANB11":0.05,  "B3SA3":  0.06,  "BPAC11":0.05,
    "WEGE3":  0.06,  "EGIE3": 0.05,  "KLBN11": 0.07,
    "BOVA11": 0.04,  "RANI3": 0.08,
}

_historico_sinais = {}

def registrar_sinal(ticker: str):
    _historico_sinais.setdefault(ticker, []).append(datetime.now())

def is_reentrada_valida(ticker: str) -> bool:
    if ticker not in _historico_sinais:
        return True
    ultima = _historico_sinais[ticker][-1]
    return (datetime.now() - ultima).days >= CONFIG["reentrada_min_dias"]

def score_horario(hora_str: str = None) -> int:
    if hora_str is None:
        hora_str = datetime.now().strftime("%H:%M")
    try:
        h, m = map(int, hora_str.split(":"))
        minutos = h * 60 + m
        if 600 <= minutos <= 690:   return 2   # 10:00–11:30
        if 780 <= minutos <= 900:   return 3   # 13:00–15:00
        if 900 <= minutos <= 990:   return 1   # 15:00–16:30
        return 0
    except Exception:
        return 0

def dentro_horario_pregao(margem_min: int = 30) -> bool:
    now = datetime.now()
    abert  = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    fech   = now.replace(hour=16, minute=30, second=0, microsecond=0)
    margem = timedelta(minutes=margem_min)
    return (abert + margem) <= now <= (fech - margem)
