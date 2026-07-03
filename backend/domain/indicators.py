import logging

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

        # Fluxo de capital (matriz v2 §2.2)
        df["mfi"]         = ta.volume.MFIIndicator(h, l, c, v, window=14).money_flow_index()
        df["obv"]         = ta.volume.OnBalanceVolumeIndicator(c, v).on_balance_volume()
        df["cmf"]         = ta.volume.ChaikinMoneyFlowIndicator(h, l, c, v, window=20).chaikin_money_flow()
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

        # Fluxo de capital (matriz v2 §2.2) — fallbacks manuais
        df["mfi"]         = _mfi_manual(h, l, c, v, 14)
        df["obv"]         = _obv_manual(c, v)
        df["cmf"]         = _cmf_manual(h, l, c, v, 20)

    # SuperTrend (matriz v2 §2.3) — não existe na lib ta; sempre manual
    df["supertrend_dir"] = _supertrend_dir(h, l, c, df["atr"], mult=3.0)

    # ── Camada PUCK: HC institucional, fluxo normalizado, absorção ────────
    df["ema50"] = c.ewm(span=50, adjust=False).mean()
    df["clv"] = _clv(h, l, c)
    df["hc_max"], df["hc_min"] = _high_candle_zones(
        h, l, v, CONFIG.get("hc_fator_volume", 1.5))

    periodo_z = CONFIG.get("cmf_z_periodo", 21)
    mfv = df["clv"] * v
    soma_vol = v.rolling(periodo_z).sum()
    agress_pos = mfv.clip(lower=0).rolling(periodo_z).sum() / (soma_vol + 1e-9)
    agress_neg = (-mfv).clip(lower=0).rolling(periodo_z).sum() / (soma_vol + 1e-9)
    media_pos = agress_pos.ewm(span=periodo_z, adjust=False).mean()
    media_neg = agress_neg.ewm(span=periodo_z, adjust=False).mean()
    # cmf_norm: intensidade do fluxo vs. média histórica do próprio ativo
    # (>1.5 = evento institucional; PUCK v3.1 §7). Sinal segue o CMF.
    df["cmf_norm"] = np.where(
        df["cmf"] > 0, agress_pos / (media_pos + 1e-9),
        np.where(df["cmf"] < 0, -(agress_neg / (media_neg + 1e-9)), 0.0))
    # cmf_z: z-score do CMF (PUCK v4.4 §5) — threshold autocalibrado cross-asset.
    # min_periods reduzido: "cmf" já carrega ~19 NaN de warm-up próprio: exigir
    # a janela cheia de `periodo_z` ADICIONAL empurraria o warm-up total de
    # cmf_z para muito além do de qualquer outro indicador (ex.: ADX, 14+14
    # períodos), inflando as linhas descartadas por `dropna()` a jusante bem
    # além do necessário para uma estimativa razoável de média/desvio.
    cmf_min_periods = max(5, periodo_z // 2 - 1)
    df["cmf_z"] = ((df["cmf"] - df["cmf"].rolling(periodo_z, min_periods=cmf_min_periods).mean())
                   / (df["cmf"].rolling(periodo_z, min_periods=cmf_min_periods).std() + 1e-9))

    # Absorção (PUCK v4.4 §8): testou o topo do HC, fechou abaixo, fluxo neutro
    df["absorcao"] = ((h >= df["hc_max"]) & (c < df["hc_max"])
                      & (df["clv"].abs() < CONFIG.get("absorcao_clv_max", 0.1)))

    # Persistência de fluxo (PUCK v4.4 §12): dias consecutivos com CLV direcional
    limite_clv = CONFIG.get("fluxo_persistencia_clv", 0.3)
    pos = (df["clv"] > limite_clv).astype(int)
    neg = (df["clv"] < -limite_clv).astype(int)
    df["fluxo_persist_pos"] = pos * (pos.groupby((pos != pos.shift()).cumsum()).cumcount() + 1)
    df["fluxo_persist_neg"] = neg * (neg.groupby((neg != neg.shift()).cumsum()).cumcount() + 1)

    # Aceleração de fluxo (OPÇÕES B3 v8.2, filtro 4): CMF estritamente
    # crescente/decrescente por 3 barras. Comparação com NaN é False → fail-safe.
    df["cmf_acel_pos"] = (df["cmf"] > df["cmf"].shift(1)) & (df["cmf"].shift(1) > df["cmf"].shift(2))
    df["cmf_acel_neg"] = (df["cmf"] < df["cmf"].shift(1)) & (df["cmf"].shift(1) < df["cmf"].shift(2))

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

def _mfi_manual(high, low, close, volume, period=14):
    """Money Flow Index — RSI ponderado por volume (0-100)."""
    tp = (high + low + close) / 3
    fluxo = tp * volume
    delta_tp = tp.diff()
    fluxo_pos = fluxo.where(delta_tp > 0, 0.0).rolling(period).sum()
    fluxo_neg = fluxo.where(delta_tp < 0, 0.0).rolling(period).sum()
    razao = fluxo_pos / fluxo_neg.replace(0, np.nan)
    return 100 - (100 / (1 + razao))


def _obv_manual(close, volume):
    """On-Balance Volume — volume acumulado com sinal da variação do fechamento."""
    direcao = np.sign(close.diff()).fillna(0.0)
    return (direcao * volume).cumsum()


def _cmf_manual(high, low, close, volume, period=20):
    """Chaikin Money Flow — fluxo de capital acumulado normalizado (-1 a 1)."""
    rng = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / rng
    mfv = mfm * volume
    return mfv.rolling(period).sum() / (volume.rolling(period).sum() + 1e-9)


def _supertrend_dir(high, low, close, atr, mult: float = 3.0) -> pd.Series:
    """Direção do SuperTrend: +1 (bullish) / -1 (bearish).

    Implementação clássica com bandas básicas ((H+L)/2 ± mult*ATR) e bandas
    finais "grudadas" (a banda só se move a favor da tendência enquanto o
    preço não a rompe). Loop necessário — a banda final depende do estado
    anterior. NaN de ATR no warm-up produz direção +1 neutra inicial.
    """
    hl2 = (high + low) / 2
    upper_basic = (hl2 + mult * atr).values
    lower_basic = (hl2 - mult * atr).values
    c = close.values
    n = len(c)
    upper = np.copy(upper_basic)
    lower = np.copy(lower_basic)
    dir_ = np.ones(n, dtype=int)
    for i in range(1, n):
        if np.isnan(upper_basic[i]) or np.isnan(lower_basic[i]):
            dir_[i] = dir_[i - 1]
            continue
        if np.isnan(upper[i - 1]) or np.isnan(lower[i - 1]):
            # warm-up do ATR: primeira banda válida parte da básica
            upper[i], lower[i] = upper_basic[i], lower_basic[i]
            dir_[i] = dir_[i - 1]
            continue
        upper[i] = (upper_basic[i] if upper_basic[i] < upper[i - 1] or c[i - 1] > upper[i - 1]
                    else upper[i - 1])
        lower[i] = (lower_basic[i] if lower_basic[i] > lower[i - 1] or c[i - 1] < lower[i - 1]
                    else lower[i - 1])
        if dir_[i - 1] == 1:
            dir_[i] = -1 if c[i] < lower[i] else 1
        else:
            dir_[i] = 1 if c[i] > upper[i] else -1
    return pd.Series(dir_, index=close.index)


def _clv(high, low, close) -> pd.Series:
    """Close Location Value (PUCK §5): +1 fecha na máxima, -1 na mínima.
    Range zero (leilão) → 0 (sem pressão)."""
    rng = (high - low).replace(0, np.nan)
    return (((close - low) - (high - close)) / rng).fillna(0.0)


def _high_candle_zones(high, low, volume, fator: float = 1.5) -> tuple[pd.Series, pd.Series]:
    """Zona do High Candle institucional (PUCK §3-4).

    O HC é o candle de maior volume visto até então, desde que o volume seja
    também > fator × média20 (filtro institucional — sem ele qualquer volume
    crescente atualizaria a zona). Retorna (hc_max, hc_min) forward-filled.
    Loop necessário (estado sequencial), mesmo padrão do _supertrend_dir.
    Sem look-ahead: a zona do dia i usa apenas candles 0..i.

    Antes do primeiro candle institucional, retorna ±inf (sentinela neutra):
    comparações de rompimento/absorção nunca disparam (`Low > +inf` = False,
    `High < -inf` = False, `High >= +inf` = False — fail-safe) e o `dropna()`
    do pipeline (`_carregar_ohlcv`/`rodar_backtest`) não descarta linhas —
    com NaN, um ativo sem candle institucional teria a coluna inteira NaN e
    o dataframe todo seria descartado a jusante.
    """
    media_vol = volume.rolling(20).mean().values
    vol, hi, lo = volume.values, high.values, low.values
    n = len(vol)
    hc_max = np.full(n, np.nan)
    hc_min = np.full(n, np.nan)
    maior_vol = 0.0
    cur_max, cur_min = np.inf, -np.inf
    for i in range(n):
        limiar = media_vol[i] * fator if media_vol[i] == media_vol[i] else float("inf")
        if vol[i] > maior_vol and vol[i] > limiar:
            maior_vol = vol[i]
            cur_max, cur_min = hi[i], lo[i]
        hc_max[i] = cur_max
        hc_min[i] = cur_min
    return (pd.Series(hc_max, index=high.index),
            pd.Series(hc_min, index=high.index))


def detectar_divergencia(df: pd.DataFrame, janela: int = 5, ordem: int | None = None) -> tuple:
    """Divergência entre PIVÔS CONFIRMADOS (não ponta-a-ponta da janela).

    Divergência altista: o fundo confirmado mais recente tem preço MENOR e
    RSI MAIOR que o fundo confirmado anterior (preço faz mínima mais baixa,
    momentum não acompanha). Divergência baixista é o espelho com topos.
    Requer ao menos 2 pivôs de cada tipo dentro de `janela` candles; sem
    pivôs suficientes ou com `is_fundo_local`/`is_topo_local` ausentes,
    retorna (False, False) — não há como avaliar ponta-a-ponta como fallback,
    pois isso reintroduziria o falso-positivo que esta função corrige.
    """
    if "is_fundo_local" not in df.columns or "is_topo_local" not in df.columns:
        return False, False
    if ordem is None:
        ordem = CONFIG["pivot_ordem"]

    base = df.tail(janela)
    fundos = base[base["is_fundo_local"]].dropna(subset=["rsi"])
    topos  = base[base["is_topo_local"]].dropna(subset=["rsi"])

    div_alta = False
    if len(fundos) >= 2:
        prev, last = fundos.iloc[-2], fundos.iloc[-1]
        div_alta = bool(last["Low"] < prev["Low"] and last["rsi"] > prev["rsi"])

    div_baixa = False
    if len(topos) >= 2:
        prev, last = topos.iloc[-2], topos.iloc[-1]
        div_baixa = bool(last["High"] > prev["High"] and last["rsi"] < prev["rsi"])

    return div_alta, div_baixa

def encontrar_zonas_demanda_oferta(df: pd.DataFrame, lookback: int = 60,
                                   tolerancia_atr: float = 1.0,
                                   ordem: int | None = None,
                                   min_toques: int = 2) -> tuple:
    """Zona de demanda/oferta: nível historicamente respeitado por ≥`min_toques`
    pivôs confirmados dentro de `atr * tolerancia_atr` um do outro, olhando os
    últimos `lookback` DIAS (não os últimos `lookback` pivôs — com poucos
    pivôs no período, uma janela maior é buscada implicitamente, o que antes
    inflava o lookback real muito além do documentado). Um único toque não
    caracteriza zona — é ruído."""
    if len(df) < 10:
        return False, False

    if ordem is None:
        ordem = CONFIG["pivot_ordem"]

    preco  = float(df["Close"].iloc[-1])
    atr    = float(df["atr"].iloc[-1]) if "atr" in df.columns else preco * 0.02
    tol    = atr * tolerancia_atr

    # Só pivots confirmados (exclui as últimas `ordem` linhas — sem look-ahead),
    # e só dentro da janela de `lookback` dias corridos no df (não de pivôs).
    base = df.iloc[:len(df) - ordem] if len(df) > ordem else df.iloc[0:0]
    base = base.tail(lookback)
    fundos = base[base["is_fundo_local"]]["Low"].values
    topos  = base[base["is_topo_local"]]["High"].values

    def _tem_zona_com_toques_minimos(preco: float, niveis, tol: float, min_toques: int) -> bool:
        for nivel in niveis:
            toques = sum(1 for outro in niveis if abs(nivel - outro) <= tol)
            if toques >= min_toques and abs(preco - nivel) <= tol:
                return True
        return False

    zona_demanda = _tem_zona_com_toques_minimos(preco, fundos, tol, min_toques)
    zona_oferta  = _tem_zona_com_toques_minimos(preco, topos, tol, min_toques)

    return zona_demanda, zona_oferta

def _r_squared(idx: np.ndarray, y: np.ndarray, coef: np.ndarray) -> float:
    pred = coef[0] * idx + coef[1]
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot


def detectar_canal_linear(df: pd.DataFrame, janela: int = 20, r2_minimo: float = 0.6) -> tuple:
    """Canal linear por regressão de topos/fundos, com exigência de qualidade
    de ajuste (R² >= r2_minimo em AMBAS as retas). Sem esse filtro, qualquer
    drift ruidoso com slope no sinal certo (mas ajuste ruim) era classificado
    como canal — ver `_r_squared`."""
    if len(df) < janela:
        return False, False, 0.0

    idx = np.arange(janela)
    h   = df["High"].tail(janela).values
    l   = df["Low"].tail(janela).values

    try:
        coef_topos  = np.polyfit(idx, h, 1)
        coef_fundos = np.polyfit(idx, l, 1)
        slope_topos, slope_fundos = coef_topos[0], coef_fundos[0]
        slope_medio  = (slope_topos + slope_fundos) / 2

        r2_topos  = _r_squared(idx, h, coef_topos)
        r2_fundos = _r_squared(idx, l, coef_fundos)
        ajuste_ok = (r2_topos >= r2_minimo) and (r2_fundos >= r2_minimo)

        canal_altista  = ajuste_ok and (slope_topos > 0) and (slope_fundos > 0)
        canal_baixista = ajuste_ok and (slope_topos < 0) and (slope_fundos < 0)
        return canal_altista, canal_baixista, slope_medio
    except Exception:
        return False, False, 0.0


def obter_vxbr_diaria() -> float | None:
    """Coleta VXBR (índice de volatilidade da B3) do dia atual.

    Tenta via API brapi.dev (gratuita, sem auth). Fallback: retorna None.
    VXBR é um índice, não há "série" — valor único por dia.

    API esperada: GET https://api.brapi.dev/api/v2/ibov-indices
    Resposta:
    ```json
    {
        "results": [
            {"name": "IBOV", "close": 120000.5},
            {"name": "VXBR", "close": 18.5},
            ...
        ]
    }
    ```

    Returns:
        float: Valor de fechamento do VXBR (ex: 18.5)
        None: Se API indisponível, timeout, ou VXBR não encontrado na resposta.
              Falhas não criam exceção, apenas loga warning (job gracefully degraded).
    """
    import requests
    try:
        resp = requests.get("https://api.brapi.dev/api/v2/ibov-indices", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Resposta esperada: {"results": [{"name": "VXBR", "close": 18.5}, ...]}
        for item in data.get("results", []):
            if item.get("name") == "VXBR":
                return float(item.get("close", 0.0))
    except Exception as e:
        logger = logging.getLogger("b3_api")
        logger.warning(f"Erro ao coletar VXBR: {e}")
    return None
