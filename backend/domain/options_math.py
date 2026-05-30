import math
import calendar
import numpy as np
import pandas as pd
from datetime import datetime, date, timezone
from scipy.stats import norm
from backend.core.config import CONFIG

MESES_CALL = {"A":1,"B":2,"C":3,"D":4,"E":5,"F":6,"G":7,"H":8,"I":9,"J":10,"K":11,"L":12}
MESES_PUT  = {"M":1,"N":2,"O":3,"P":4,"Q":5,"R":6,"S":7,"T":8,"U":9,"V":10,"W":11,"X":12}

ETFS_B3 = {"BOVA11", "SMAL11", "IVVB11", "HASH11"}

def decodificar_opcao_b3(codigo: str) -> dict:
    codigo = codigo.upper().strip()
    if len(codigo) < 7:
        return {}

    letra_tipo = codigo[4]
    acao_base_raw = codigo[:4]

    if letra_tipo in MESES_CALL:
        tipo, mes = "CALL", MESES_CALL[letra_tipo]
    elif letra_tipo in MESES_PUT:
        tipo, mes = "PUT", MESES_PUT[letra_tipo]
    else:
        return {}

    try:
        strike_raw = int(codigo[5:])
    except ValueError:
        return {}

    acao_norm = acao_base_raw.rstrip("0123456789") + "11" if acao_base_raw.startswith("BOV") else acao_base_raw
    is_etf = any(acao_base_raw.startswith(etf[:4]) for etf in ETFS_B3)

    if is_etf:
        strike = float(strike_raw) if strike_raw >= 100 else strike_raw / 10.0
    elif strike_raw >= 10000:
        strike = strike_raw / 100.0
    elif strike_raw >= 1000:
        candidato = strike_raw / 100.0
        strike = strike_raw / 1000.0 if candidato < 2.0 else candidato
    elif strike_raw >= 100:
        candidato = strike_raw / 100.0
        strike = strike_raw / 1000.0 if candidato < 1.0 else candidato
    else:
        strike = strike_raw / 10.0

    hoje = datetime.now(timezone.utc)
    ano_atual = hoje.year
    return {
        "codigo":     codigo,
        "acao_base":  acao_base_raw,
        "tipo":       tipo,
        "mes_venc":   mes,
        "ano_venc":   ano_atual if mes >= hoje.month else ano_atual + 1,
        "strike":     round(strike, 2),
    }

def calcular_dte(mes_venc: int, ano_venc: int = None) -> int:
    hoje = datetime.now(timezone.utc).date()
    if ano_venc is None:
        ano_venc = hoje.year
    cal = calendar.monthcalendar(ano_venc, mes_venc)
    sextas = [semana[4] for semana in cal if semana[4] != 0]
    if len(sextas) < 3:
        return 0
    venc = date(ano_venc, mes_venc, sextas[2])
    dias_corridos = (venc - hoje).days
    return max(0, round(dias_corridos * 5 / 7))

def mes_vencimento_ideal() -> tuple:
    hoje = datetime.now(timezone.utc)
    for delta_mes in range(0, 4):
        mes = ((hoje.month - 1 + delta_mes) % 12) + 1
        ano = hoje.year + ((hoje.month - 1 + delta_mes) // 12)
        dte = calcular_dte(mes, ano)
        if CONFIG["dte_minimo"] <= dte <= CONFIG["dte_maximo"]:
            return mes, ano, dte
    return hoje.month, hoje.year, 0

def estimar_iv_historica(df: pd.DataFrame, janela: int = 20, interval: str = "1d") -> float:
    retornos = np.log(df["Close"] / df["Close"].shift(1)).dropna()
    if len(retornos) < janela:
        return 0.40
    iv_periodo = retornos.tail(janela).std()
    
    # Anualização baseada no timeframe
    if interval == "1h":
        # Assumindo 7 horas de pregão B3 por dia
        fator_anualizacao = np.sqrt(252 * 7)
    else:
        fator_anualizacao = np.sqrt(252)
        
    return float(iv_periodo * fator_anualizacao)

def estimar_premio_otm(preco: float, strike: float, dte_du: int,
                       iv: float, tipo: str = "PUT") -> float:
    if dte_du <= 0 or iv <= 0:
        return max(0.10, round(preco * 0.015, 2))
    t = dte_du / 252
    try:
        d1 = (math.log(preco / strike) + 0.5 * iv**2 * t) / (iv * math.sqrt(t))
        d2 = d1 - iv * math.sqrt(t)
        
        if tipo == "PUT":
            premio = strike * norm.cdf(-d2) - preco * norm.cdf(-d1)
        else:
            premio = preco * norm.cdf(d1) - strike * norm.cdf(d2)
        return max(0.10, round(float(premio), 2))
    except Exception:
        fator_otm = abs(preco - strike) / preco
        return max(0.10, round(preco * iv * math.sqrt(t) * max(0.1, 1 - fator_otm * 5), 2))
