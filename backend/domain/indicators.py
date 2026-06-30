import numpy as np
import pandas as pd

from backend.core.config import CONFIG


def pivots_confirmados(df: pd.DataFrame, ordem: int = 1) -> tuple[pd.Series, pd.Series]:
    """Fundos/topos locais por janela simétrica de `ordem` candles de cada lado.

    Um pivot no índice ``i`` só é marcado quando existem ``ordem`` candles à
    esquerda E à direita (a janela ``rolling(center=True)`` retorna NaN nas
    bordas). Por isso o valor de ``i`` é invariante à adição de candles após
    ``i + ordem`` — base do teste anti-look-ahead. A marcação fica na data de
    OCORRÊNCIA ``i``; o consumo deve ignorar as últimas ``ordem`` linhas do df
    recebido (ver ``ultimos_pivots_confirmados``).
    """
    low, high = df["Low"], df["High"]
    w = 2 * ordem + 1
    min_roll = low.rolling(w, center=True).min()
    max_roll = high.rolling(w, center=True).max()
    is_fundo = (low == min_roll) & min_roll.notna()
    is_topo  = (high == max_roll) & max_roll.notna()
    return is_fundo, is_topo


def ultimos_pivots_confirmados(df: pd.DataFrame, ordem: int = 1,
                               n: int = 3) -> tuple:
    """Últimos ``n`` valores de fundos (Low) e topos (High) locais CONFIRMADOS.

    Exclui as últimas ``ordem`` linhas do df recebido: na decisão tomada na
    última linha ``t``, um pivot em índice ``> t - ordem`` exigiria candles
    futuros. Isso elimina o look-ahead mesmo quando ``is_fundo_local`` foi
    pré-calculado sobre um df maior (caso do backtest).
    """
    if len(df) <= ordem:
        return [], []
    base = df.iloc[:len(df) - ordem]
    fundos = base[base["is_fundo_local"]]["Low"].tail(n).values
    topos  = base[base["is_topo_local"]]["High"].tail(n).values
    return fundos, topos


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
        adx_obj           = ta.trend.ADXIndicator(h, l, c, window=14)
        df["adx"]         = adx_obj.adx()
        df["williams_r"]  = ta.momentum.WilliamsRIndicator(h, l, c, lbp=14).williams_r()
        df["cci"]         = ta.trend.CCIIndicator(h, l, c, window=20).cci()

        # Keltner Channels (using ta-lib / ta wrapper if available, or manual)
        kc                = ta.volatility.KeltnerChannel(h, l, c, window=20, window_atr=14, fillna=False)
        df["kc_upper"]    = kc.keltner_channel_hband()
        df["kc_lower"]    = kc.keltner_channel_lband()
        df["kc_mid"]      = kc.keltner_channel_mband()

        # VWAP (ta.volume)
        vwap              = ta.volume.VolumeWeightedAveragePrice(h, l, c, v, window=20, fillna=False)
        df["vwap"]        = vwap.volume_weighted_average_price()
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
        df["adx"]         = _adx_manual(h, l, c, 14)
        lo14, hi14        = l.rolling(14).min(), h.rolling(14).max()
        df["williams_r"]  = -100 * (hi14 - c) / (hi14 - lo14 + 1e-9)
        tp                = (h + l + c) / 3
        tp_ma             = tp.rolling(20).mean()
        tp_md             = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
        df["cci"]         = (tp - tp_ma) / (0.015 * tp_md + 1e-9)

        # Keltner Channels (Manual)
        df["kc_mid"]      = df["ema21"] # Approximation for EMA 20
        df["kc_upper"]    = df["kc_mid"] + (1.5 * df["atr"])
        df["kc_lower"]    = df["kc_mid"] - (1.5 * df["atr"])

        # VWAP (Rolling 20 periods for Daily charts)
        vwap_vol_sum      = v.rolling(20).sum()
        df["vwap"]        = (tp * v).rolling(20).sum() / (vwap_vol_sum + 1e-9)

    # Derivados úteis para o score ponderado (independentes da lib ta)
    df["bb_pct"]   = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    df["vol_ratio"] = v / v.rolling(20).mean()
    df["trend_up"]   = ((c > df["ema9"]).astype(int) + (c > df["ema21"]).astype(int)
                        + (c > df["ema200"]).astype(int))
    df["trend_down"] = ((c < df["ema9"]).astype(int) + (c < df["ema21"]).astype(int)
                        + (c < df["ema200"]).astype(int))

    df["vol_media_20"]    = v.rolling(20).mean()
    df["suporte_20"]      = l.rolling(20).min()
    df["resistencia_20"]  = h.rolling(20).max()
    df["var_pct"]         = c.pct_change()
    is_fundo, is_topo = pivots_confirmados(df, ordem=CONFIG["pivot_ordem"])
    df["is_fundo_local"] = is_fundo
    df["is_topo_local"]  = is_topo
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

def _adx_manual(high, low, close, period=14):
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di  = 100 * plus_dm.rolling(period).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.rolling(period).mean() / (atr + 1e-9)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    return dx.rolling(period).mean()

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
                                   tolerancia_atr: float = 1.0,
                                   ordem: int | None = None) -> tuple:
    if len(df) < 10:
        return False, False

    if ordem is None:
        ordem = CONFIG["pivot_ordem"]

    preco  = float(df["Close"].iloc[-1])
    atr    = float(df["atr"].iloc[-1]) if "atr" in df.columns else preco * 0.02

    # Só pivots confirmados (exclui as últimas `ordem` linhas — sem look-ahead).
    base = df.iloc[:len(df) - ordem] if len(df) > ordem else df.iloc[0:0]
    fundos = base[base["is_fundo_local"]]["Low"].tail(lookback).values
    topos  = base[base["is_topo_local"]]["High"].tail(lookback).values

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
