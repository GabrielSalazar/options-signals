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


def inside_bar(df: pd.DataFrame) -> SetupResult:
    """Candle atual contido no range do anterior."""
    nome = "Inside Bar"
    if len(df) < 2:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    dentro = (float(df["High"].iloc[-1]) <= float(df["High"].iloc[-2])
              and float(df["Low"].iloc[-1]) >= float(df["Low"].iloc[-2]))
    if dentro:
        tend = _tendencia_ema9(df)
        vies = "alta" if tend == "up" else "baixa" if tend == "down" else "neutro"
        return SetupResult(nome, "ativo", vies,
                           "Barra interna — compressão de volatilidade; rompimento define a direção.")
    return SetupResult(nome, "inativo", "neutro", "Sem barra interna no candle atual.")


def rompimento(df: pd.DataFrame) -> SetupResult:
    """Rompimento da resistência/suporte de 20 períodos."""
    nome = "Rompimento 20"
    if len(df) < 2 or "resistencia_20" not in df.columns:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    close = float(df["Close"].iloc[-1])
    resist = float(df["resistencia_20"].iloc[-2])
    sup = float(df["suporte_20"].iloc[-2])
    if close > resist:
        return SetupResult(nome, "ativo", "alta",
                           f"Rompimento da máxima de 20 períodos (R$ {resist:.2f}) — força compradora.")
    if close < sup:
        return SetupResult(nome, "ativo", "baixa",
                           f"Perda do suporte de 20 períodos (R$ {sup:.2f}) — força vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Preço dentro do range de 20 períodos.")


def engolfo(df: pd.DataFrame) -> SetupResult:
    """Padrão de engolfo (engulfing) de alta ou baixa."""
    nome = "Engolfo"
    if len(df) < 2:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o1, c1 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    o0, c0 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1])
    bull = c1 < o1 and c0 > o0 and o0 <= c1 and c0 >= o1
    bear = c1 > o1 and c0 < o0 and o0 >= c1 and c0 <= o1
    if bull:
        return SetupResult(nome, "ativo", "alta", "Engolfo de alta — reversão compradora.")
    if bear:
        return SetupResult(nome, "ativo", "baixa", "Engolfo de baixa — reversão vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Sem engolfo no candle atual.")


def pin_bar(df: pd.DataFrame) -> SetupResult:
    """Martelo (sombra inferior longa) ou Shooting Star (sombra superior longa)."""
    nome = "Pin Bar"
    if len(df) < 1:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o = float(df["Open"].iloc[-1]); c = float(df["Close"].iloc[-1])
    h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])
    corpo = abs(c - o)
    rng = h - l
    if rng <= 0:
        return SetupResult(nome, "inativo", "neutro", "Candle sem range.")
    sombra_inf = min(o, c) - l
    sombra_sup = h - max(o, c)
    if corpo > 0 and sombra_inf >= 2 * corpo and max(o, c) >= l + 0.66 * rng:
        return SetupResult(nome, "ativo", "alta", "Martelo — rejeição de preços baixos.")
    if corpo > 0 and sombra_sup >= 2 * corpo and min(o, c) <= l + 0.34 * rng:
        return SetupResult(nome, "ativo", "baixa", "Shooting Star — rejeição de preços altos.")
    return SetupResult(nome, "inativo", "neutro", "Sem pin bar no candle atual.")


def doji(df: pd.DataFrame) -> SetupResult:
    """Doji — corpo desprezível frente ao range (indecisão)."""
    nome = "Doji"
    if len(df) < 1:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o = float(df["Open"].iloc[-1]); c = float(df["Close"].iloc[-1])
    h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])
    rng = h - l
    if rng > 0 and abs(c - o) <= 0.1 * rng:
        return SetupResult(nome, "ativo", "neutro", "Doji — indecisão entre compra e venda.")
    return SetupResult(nome, "inativo", "neutro", "Sem doji no candle atual.")


def pullback_media(df: pd.DataFrame) -> SetupResult:
    """Reentrada a favor da tendência após repique à MME9 ou MME21."""
    nome = "Pullback MME9/21"
    if len(df) < 1 or "ema9" not in df.columns or "ema21" not in df.columns:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    ema9 = float(df["ema9"].iloc[-1]); ema21 = float(df["ema21"].iloc[-1])
    high = float(df["High"].iloc[-1]); low = float(df["Low"].iloc[-1]); close = float(df["Close"].iloc[-1])
    atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else (high - low)
    tocou9 = low <= ema9 <= high or abs(close - ema9) < 0.5 * atr
    tocou21 = low <= ema21 <= high or abs(close - ema21) < 0.5 * atr
    if ema9 > ema21 and (tocou9 or tocou21):
        return SetupResult(nome, "ativo", "alta", "Pullback à média em tendência de alta — reentrada compradora.")
    if ema9 < ema21 and (tocou9 or tocou21):
        return SetupResult(nome, "ativo", "baixa", "Repique à média em tendência de baixa — reentrada vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Preço longe das médias 9/21.")


def detectar_setups(df: pd.DataFrame) -> list[SetupResult]:
    """Executa todos os detectores na ordem canônica de exibição."""
    return [
        larry_91(df), larry_92(df), larry_93(df),
        inside_bar(df), rompimento(df),
        engolfo(df), pin_bar(df), doji(df),
        pullback_media(df),
    ]
