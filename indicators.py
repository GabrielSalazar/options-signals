import numpy as np
import pandas as pd
from config import CONFIG

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) < 30:
        return df

    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    if TA_AVAILABLE:
        stoch = ta.momentum.StochasticOscillator(
            high=h, low=l, close=c,
            window=CONFIG["stoch_k_period"],
            smooth_window=CONFIG["stoch_d_period"]
        )
        df["stoch_k"]     = stoch.stoch()
        df["stoch_d"]     = stoch.stoch_signal()
        df["rsi"]         = ta.momentum.RSIIndicator(close=c, window=CONFIG["rsi_period"]).rsi()
        df["ema9"]        = ta.trend.EMAIndicator(close=c, window=CONFIG["ema_fast"]).ema_indicator()
        df["ema21"]       = ta.trend.EMAIndicator(close=c, window=CONFIG["ema_slow"]).ema_indicator()
        df["ema200"]      = ta.trend.EMAIndicator(close=c, window=200).ema_indicator()
        macd_obj          = ta.trend.MACD(close=c)
        df["macd"]        = macd_obj.macd()
        df["macd_signal"] = macd_obj.macd_signal()
        df["macd_diff"]   = macd_obj.macd_diff()
        df["atr"]         = ta.volatility.AverageTrueRange(h, l, c, window=14).average_true_range()
        bb                = ta.volatility.BollingerBands(close=c, window=20, window_dev=2)
        df["bb_upper"]    = bb.bollinger_hband()
        df["bb_lower"]    = bb.bollinger_lband()
        df["bb_mid"]      = bb.bollinger_mavg()
    else:
        df["stoch_k"]     = _stoch_manual(h, l, c, CONFIG["stoch_k_period"])
        df["rsi"]         = _rsi_manual(c, CONFIG["rsi_period"])
        df["ema9"]        = c.ewm(span=CONFIG["ema_fast"],  adjust=False).mean()
        df["ema21"]       = c.ewm(span=CONFIG["ema_slow"],  adjust=False).mean()
        df["ema200"]      = c.ewm(span=200,                 adjust=False).mean()
        df["stoch_d"]     = df["stoch_k"].rolling(CONFIG["stoch_d_period"]).mean()
        df["macd"]        = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_diff"]   = df["macd"] - df["macd_signal"]
        df["atr"]         = _atr_manual(h, l, c, 14)
        df["bb_lower"]    = c.rolling(20).mean() - 2 * c.rolling(20).std()
        df["bb_upper"]    = c.rolling(20).mean() + 2 * c.rolling(20).std()
        df["bb_mid"]      = c.rolling(20).mean()

    df["vol_media_20"]    = v.rolling(20).mean()
    df["suporte_20"]      = l.rolling(20).min()
    df["resistencia_20"]  = h.rolling(20).max()
    df["var_pct"]         = c.pct_change()
    df["is_fundo_local"]  = (l < l.shift(1)) & (l < l.shift(-1))
    df["is_topo_local"]   = (h > h.shift(1)) & (h > h.shift(-1))
    return df

def _stoch_manual(high, low, close, k=14):
    lowest  = low.rolling(k).min()
    highest = high.rolling(k).max()
    denom   = (highest - lowest).replace(0, np.nan)
    return 100 * ((close - lowest) / denom)

def _rsi_manual(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _atr_manual(high, low, close, period=14):
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def detectar_divergencia(df: pd.DataFrame, janela: int = 5) -> tuple:
    if len(df) < janela + 2:
        return False, False
    precos = df["Close"].tail(janela).values
    rsi    = df["rsi"].tail(janela).values
    if np.any(np.isnan(rsi)):
        return False, False
    div_alta  = (precos[-1] < precos[0]) and (rsi[-1] > rsi[0])
    div_baixa = (precos[-1] > precos[0]) and (rsi[-1] < rsi[0])
    return div_alta, div_baixa

def encontrar_zonas_demanda_oferta(df: pd.DataFrame, lookback: int = 60,
                                   tolerancia_atr: float = 1.0) -> tuple:
    if len(df) < 10:
        return False, False

    preco  = float(df["Close"].iloc[-1])
    atr    = float(df["atr"].iloc[-1]) if "atr" in df.columns else preco * 0.02

    fundos = df[df["is_fundo_local"]]["Low"].tail(lookback).values
    topos  = df[df["is_topo_local"]]["High"].tail(lookback).values

    zona_demanda = any(abs(preco - f) <= atr * tolerancia_atr for f in fundos)
    zona_oferta  = any(abs(preco - t) <= atr * tolerancia_atr for t in topos)

    return zona_demanda, zona_oferta

def detectar_canal_linear(df: pd.DataFrame, janela: int = 20) -> tuple:
    if len(df) < janela:
        return False, False, 0.0

    idx = np.arange(janela)
    h   = df["High"].tail(janela).values
    l   = df["Low"].tail(janela).values

    try:
        slope_topos  = np.polyfit(idx, h, 1)[0]
        slope_fundos = np.polyfit(idx, l, 1)[0]
        slope_medio  = (slope_topos + slope_fundos) / 2

        canal_altista  = (slope_topos > 0) and (slope_fundos > 0)
        canal_baixista = (slope_topos < 0) and (slope_fundos < 0)
        return canal_altista, canal_baixista, slope_medio
    except Exception:
        return False, False, 0.0
