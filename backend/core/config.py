import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.core.settings import MotorSettings

_TZ_SP = ZoneInfo("America/Sao_Paulo")

_settings = MotorSettings()
CONFIG: dict = _settings.model_dump(by_alias=False)
# CONFIG continua sendo um dict mutável (compatibilidade com os usos
# existentes de CONFIG["x"]/CONFIG.get("x") e com a mutação em runtime de
# _historico_sinais já documentada). A validação de schema acontece uma
# vez, no boot, via MotorSettings.

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

# A montagem do universo (curados + B3 + brapi) vive em backend/services/ticker_loader.py
# para respeitar a direção de dependência routers → services → domain/core.


def validar_config(cfg: dict = None) -> None:
    """Valida invariantes críticos do CONFIG (fail-fast no boot). [P2-7]

    Levanta ValueError se algum invariante for violado — evita configs que
    silenciosamente impedem a emissão de sinais (ex.: DTE/delta inconsistentes).
    """
    c = cfg if cfg is not None else CONFIG
    if not (0 < c["dte_minimo"] < c["dte_maximo"]):
        raise ValueError(f"DTE inválido: dte_minimo={c['dte_minimo']} dte_maximo={c['dte_maximo']}")
    if not (0 < c["delta_min"] < c["delta_max"] <= 1.0):
        raise ValueError(f"banda de delta inválida: {c['delta_min']}..{c['delta_max']}")
    if c["stop_pct"] >= 0:
        raise ValueError(f"stop_pct deve ser negativo: {c['stop_pct']}")
    if not (c["alvo1_pct"] < c["alvo2_pct"] < c["alvo_final_pct"]):
        raise ValueError("alvos devem ser crescentes: alvo1_pct < alvo2_pct < alvo_final_pct")
    if c["min_score"] <= 0:
        raise ValueError(f"min_score deve ser > 0: {c['min_score']}")


# Fail-fast: valida os invariantes assim que o módulo é importado (no boot).
validar_config()


_historico_sinais_lock = threading.Lock()
_ticker_locks = {}
_ticker_locks_lock = threading.Lock()

def get_ticker_lock(ticker: str) -> threading.Lock:
    with _ticker_locks_lock:
        if ticker not in _ticker_locks:
            _ticker_locks[ticker] = threading.Lock()
        return _ticker_locks[ticker]

# _historico_sinais: ticker -> [{"ts": datetime, "tipo": str|None, "score": int}]
_historico_sinais = {}

def registrar_sinal(ticker: str, tipo_sinal: str | None = None, score: int = 0):
    with _historico_sinais_lock:
        _historico_sinais.setdefault(ticker, []).append(
            {"ts": datetime.now(), "tipo": tipo_sinal, "score": int(score)}
        )

def is_reentrada_valida(ticker: str, tipo_sinal: str | None = None, score: int = 0) -> bool:
    """Cooldown por (ticker, direção):
    - mesma direção dentro de `reentrada_mesma_direcao_dias` → bloqueia;
    - direção oposta vigente → só emite se score >= score_vigente + delta.
    """
    with _historico_sinais_lock:
        registros = _historico_sinais.get(ticker)
        if not registros:
            return True
        registros_copia = list(registros)

    agora = datetime.now()
    dias = CONFIG["reentrada_mesma_direcao_dias"]
    delta = CONFIG["reentrada_direcao_oposta_delta_score"]

    mesmos = [r for r in registros_copia if r.get("tipo") == tipo_sinal]
    if mesmos and (agora - mesmos[-1]["ts"]).days < dias:
        return False

    opostos = [r for r in registros_copia
               if r.get("tipo") is not None and r.get("tipo") != tipo_sinal]
    if opostos and (agora - opostos[-1]["ts"]).days < dias:
        if score < opostos[-1].get("score", 0) + delta:
            return False

    return True

def score_horario(hora_str: str = None) -> int:
    if hora_str is None:
        hora_str = datetime.now(_TZ_SP).strftime("%H:%M")
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
    now = datetime.now(_TZ_SP)
    abert  = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    fech   = now.replace(hour=16, minute=30, second=0, microsecond=0)
    margem = timedelta(minutes=margem_min)
    return (abert + margem) <= now <= (fech - margem)
