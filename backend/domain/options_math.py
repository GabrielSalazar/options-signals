import calendar
import math
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from backend.core.config import CONFIG
from backend.domain.greeks import implied_volatility
from backend.domain.volatility import compute_log_returns

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

def _proximo_vencimento_b3(hoje: date | None = None) -> tuple:
    """Retorna (mes, ano, dte, tipo_venc) do próximo vencimento B3 no range [dte_min, dte_max].
    Busca sextas semanais (toda sexta-feira, exceto 3ª sexta) e mensais (3ª sexta).
    Retorna primeiro match dentro do range. Se hoje é sexta, pula para próxima sexta."""
    if hoje is None:
        hoje = datetime.now(timezone.utc).date()
    dte_min = CONFIG["dte_minimo"]
    dte_max = CONFIG["dte_maximo"]

    # Se hoje é sexta, começa a procurar a partir de amanhã; senão, a partir de hoje
    dias_adiante_inicio = 1 if hoje.weekday() == 4 else 0

    # Procura próximas 12 sextas (3 meses de cobertura)
    for dias_adiante in range(dias_adiante_inicio, 365):
        candidato = hoje + pd.Timedelta(days=dias_adiante)
        if candidato.weekday() != 4:  # 4 = sexta
            continue

        dias_corridos = (candidato - hoje).days
        dte = round(dias_corridos * 5 / 7)  # DTE em dias úteis

        if not (dte_min <= dte <= dte_max):
            continue

        # É a 3ª sexta do mês? (mensal)
        cal = calendar.monthcalendar(candidato.year, candidato.month)
        sextas = [semana[4] for semana in cal if semana[4] != 0]
        eh_terceira_sexta = len(sextas) >= 3 and candidato.day == sextas[2]
        tipo = "mensal" if eh_terceira_sexta else "semanal"

        return candidato.month, candidato.year, dte, tipo

    # Fallback: não encontrou nada no range
    return hoje.month, hoje.year, 0, "nenhum"

def mes_vencimento_ideal(hoje: date | None = None) -> tuple:
    """Retorna (mes, ano, dte) do próximo vencimento B3 no range [dte_min, dte_max]."""
    mes, ano, dte, _ = _proximo_vencimento_b3(hoje=hoje)
    return mes, ano, dte

def estimar_iv_historica(df: pd.DataFrame, janela: int = 20, interval: str = "1d") -> float:
    retornos = compute_log_returns(df["Close"])
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
        return max(0.01, round(preco * 0.015, 2))
    t = dte_du / 252
    try:
        d1 = (math.log(preco / strike) + 0.5 * iv**2 * t) / (iv * math.sqrt(t))
        d2 = d1 - iv * math.sqrt(t)

        if tipo == "PUT":
            premio = strike * norm.cdf(-d2) - preco * norm.cdf(-d1)
        else:
            premio = preco * norm.cdf(d1) - strike * norm.cdf(d2)
        return max(0.01, round(float(premio), 2))
    except Exception:
        fator_otm = abs(preco - strike) / preco
        return max(0.01, round(preco * iv * math.sqrt(t) * max(0.1, 1 - fator_otm * 5), 2))

def resolver_iv(preco_tela: float | None, S: float, K: float, T: float, tipo: str,
                 hv_20d: float, ivs_strikes_vizinhos: list[float] | None = None) -> tuple[float, str]:
    """
    Fallback chain de IV implícita (Camada 1.1):
      1. tela            — IV implícita do prêmio real, validada contra no-arbitrage.
      2. strikes_vizinhos — mediana da IV implícita dos strikes líquidos vizinhos.
      3. hv_proxy         — HV 20d × 1.1 (prêmio de risco típico).
      4. default          — 0.40 (último recurso).
    Retorna (iv, fonte).
    """
    ivs_strikes_vizinhos = ivs_strikes_vizinhos or []

    if preco_tela and T > 0:
        intrinsico = max(S - K, 0.0) if tipo.upper() == "CALL" else max(K - S, 0.0)
        if preco_tela > intrinsico:
            iv = implied_volatility(S, K, T, preco_tela, tipo, sigma_init=hv_20d or 0.5)
            if 0.05 <= iv <= 3.0:
                return iv, "tela"

    validos = [v for v in ivs_strikes_vizinhos if v and 0.05 <= v <= 3.0]
    if validos:
        return float(np.median(validos)), "strikes_vizinhos"

    if hv_20d and hv_20d > 0:
        return float(hv_20d * 1.1), "hv_proxy"

    return 0.40, "default"
