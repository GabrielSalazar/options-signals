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

    # ── Gestão de risco (calibrado sobre 31 sinais reais) ──────────────────
    "stop_pct":          -0.43,
    "alvo1_pct":         0.25,
    "alvo2_pct":         2.50,
    "alvo_final_pct":    7.00,
    "rr_minimo":         0.8,
    "buy_band_pct":      0.035,   # faixa de compra = ±3,5% do preço central
    "book_days":         7,       # validade da ordem no book (dias corridos)

    # ── Filtros ────────────────────────────────────────────────────────────
    "min_volume_diario":    1_000_000,
    "min_variacao_gatilho": 0.015,
    "lookback_dias":        30,
    "min_score":            5,
    "scoring_mode":        "classico",  # "classico" | "ponderado"
    "min_score_ponderado": 60,           # limiar para modo ponderado (0-100)
    "delta_min":           0.15,         # filtro de qualidade |delta| mínimo
    "delta_max":           0.45,         # filtro de qualidade |delta| máximo
    "option_price_min":    0.10,         # preço mínimo da opção (R$)
    "option_price_max":    3.00,         # preço máximo da opção (R$)
    "min_negocios_opcao":  10,           # nº mínimo de negócios na opção (proxy de OI/liquidez)

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
    "COGN3.SA":  "Cogna Educação",
    "EMBR3.SA":  "Embraer",
    "RENT3.SA":  "Localiza",
    "PRIO3.SA":  "PRIO",
    "RAIL3.SA":  "Rumo",
    "ENEV3.SA":  "Eneva",
    "EQTL3.SA":  "Equatorial",
    "CSAN3.SA":  "Cosan",
    "HAPV3.SA":  "Hapvida",
    "HYPE3.SA":  "Hypera",
    "RDOR3.SA":  "Rede D'Or",
    "NTCO3.SA":  "Natura",
    "CPLE6.SA":  "Copel",
    "CYRE3.SA":  "Cyrela",
    "TIMS3.SA":  "TIM",
    "VBBR3.SA":  "Vibra Energia",
    "VIVT3.SA":  "Vivo",
    "YDUQ3.SA":  "YDUQS",
    "MULT3.SA":  "Multiplan",
    "PCAR3.SA":  "Grupo Pão de Açúcar",
    "MRFG3.SA":  "Marfrig",
    "BBDC3.SA":  "Bradesco ON",
    "ITUB3.SA":  "Itaú Unibanco ON",
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
    "COGN3": 0.10,  "EMBR3": 0.07,  "RENT3": 0.06,  "PRIO3": 0.07,
    "RAIL3": 0.07,  "ENEV3": 0.08,  "EQTL3": 0.06,  "CSAN3": 0.08,
    "HAPV3": 0.09,  "HYPE3": 0.07,  "RDOR3": 0.06,  "NTCO3": 0.09,
    "CPLE6": 0.06,  "CYRE3": 0.08,  "TIMS3": 0.06,  "VBBR3": 0.07,
    "VIVT3": 0.05,  "YDUQ3": 0.09,  "MULT3": 0.07,  "PCAR3": 0.10,
    "MRFG3": 0.10,  "BBDC3": 0.06,  "ITUB3": 0.06,
}

OTM_DEFAULT = 0.08  # distância OTM default para tickers fora do dicionário curado


def get_all_b3_assets() -> dict:
    """
    Retorna ATIVOS_B3 mesclado com todos os tickers da B3 via brapi.
    Tickers desconhecidos recebem o próprio código como nome.
    Em caso de falha da brapi, devolve apenas a lista curada.
    """
    from backend.services.data_providers import fetch_all_b3_tickers
    merged = dict(ATIVOS_B3)
    for t in fetch_all_b3_tickers():
        key = f"{t}.SA"
        if key not in merged:
            merged[key] = t
    return merged


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
