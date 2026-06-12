"""Detecção pura de setups de price action a partir de OHLCV + indicadores.

Cada detector avalia o candle mais recente (iloc[-1]) e retorna um SetupResult.
São interpretações determinísticas e simplificadas, adequadas a um flag de
estado numa página de leitura — não a execução automática.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class SetupResult:
    nome: str
    status: str   # "ativo" | "armado" | "inativo"
    vies: str     # "alta" | "baixa" | "neutro"
    descricao: str


def _tendencia_ema9(df: pd.DataFrame) -> str:
    """Inclinação da MME9: 'up', 'down' ou 'flat'.

    Usa lookback de até 3 candles anteriores (slope ema9[-1] - ema9[-min(4,n)]).
    Requer ao menos 2 linhas com ema9.
    """
    if "ema9" not in df.columns or len(df) < 2:
        return "flat"
    lookback = min(4, len(df))
    slope = float(df["ema9"].iloc[-1]) - float(df["ema9"].iloc[-lookback])
    if slope > 0:
        return "up"
    if slope < 0:
        return "down"
    return "flat"


def larry_91(df: pd.DataFrame) -> SetupResult:
    """Continuação por rompimento na direção da MME9."""
    nome = "Larry 9.1"
    if len(df) < 3:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    close = float(df["Close"].iloc[-1])
    high_prev = float(df["High"].iloc[-2])
    low_prev = float(df["Low"].iloc[-2])
    if tend == "up" and close > high_prev:
        return SetupResult(nome, "ativo", "alta",
                           "MME9 em alta e rompimento da máxima anterior — continuação compradora.")
    if tend == "down" and close < low_prev:
        return SetupResult(nome, "ativo", "baixa",
                           "MME9 em baixa e rompimento da mínima anterior — continuação vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Sem rompimento a favor da MME9.")


def larry_92(df: pd.DataFrame) -> SetupResult:
    """Pivô de retorno à média (1 candle de pullback)."""
    nome = "Larry 9.2"
    if len(df) < 3:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    low = df["Low"]
    high = df["High"]
    if tend == "up":
        disparou = float(low.iloc[-3]) > float(low.iloc[-2]) and float(high.iloc[-1]) > float(high.iloc[-2])
        if disparou:
            return SetupResult(nome, "ativo", "alta",
                               "Rompimento da máxima após pullback — entrada compradora a favor da MME9.")
        if float(low.iloc[-1]) < float(low.iloc[-2]):
            return SetupResult(nome, "armado", "alta",
                               f"Pullback em tendência de alta — aguardando rompimento de R$ {float(high.iloc[-1]):.2f}.")
    if tend == "down":
        disparou = float(high.iloc[-3]) < float(high.iloc[-2]) and float(low.iloc[-1]) < float(low.iloc[-2])
        if disparou:
            return SetupResult(nome, "ativo", "baixa",
                               "Rompimento da mínima após repique — entrada vendedora a favor da MME9.")
        if float(high.iloc[-1]) > float(high.iloc[-2]):
            return SetupResult(nome, "armado", "baixa",
                               f"Repique em tendência de baixa — aguardando perda de R$ {float(low.iloc[-1]):.2f}.")
    return SetupResult(nome, "inativo", "neutro", "Sem pivô de retorno à média.")


def larry_93(df: pd.DataFrame) -> SetupResult:
    """Continuação após duas correções consecutivas contra a tendência."""
    nome = "Larry 9.3"
    if len(df) < 3:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    low = df["Low"]
    high = df["High"]
    if tend == "up" and float(low.iloc[-1]) < float(low.iloc[-2]) < float(low.iloc[-3]):
        return SetupResult(nome, "armado", "alta",
                           "Duas mínimas decrescentes em tendência de alta — correção madura, aguardando retomada.")
    if tend == "down" and float(high.iloc[-1]) > float(high.iloc[-2]) > float(high.iloc[-3]):
        return SetupResult(nome, "armado", "baixa",
                           "Duas máximas crescentes em tendência de baixa — repique maduro, aguardando retomada.")
    return SetupResult(nome, "inativo", "neutro", "Sem padrão de continuação 9.3.")
