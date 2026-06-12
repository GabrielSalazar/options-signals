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
