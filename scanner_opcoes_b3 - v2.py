#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║   SCANNER DE OPÇÕES OTM — B3 (Estratégia TP Capital)               ║
║   Engenharia Reversa dos Sinais de Swing Trade                      ║
║                                                                      ║
║   COMO USAR:                                                         ║
║     pip install yfinance pandas numpy ta colorama tabulate          ║
║     python scanner_opcoes_b3.py                                     ║
║                                                                      ║
║   Requisitos: Python 3.8+, conexão internet                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    print("⚠  Biblioteca 'ta' não instalada. Use: pip install ta")

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COL = True
except ImportError:
    COL = False

try:
    from tabulate import tabulate
    TAB = True
except ImportError:
    TAB = False

from datetime import datetime, timedelta
import time
import re

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURAÇÕES DA ESTRATÉGIA (extraídas dos sinais TP Capital)
# ─────────────────────────────────────────────────────────────────────────────

CONFIG = {
    # Indicadores
    "stoch_k_period":   14,       # Período %K Estocástico
    "stoch_d_period":    3,       # Período %D Estocástico
    "stoch_smooth":      3,       # Suavização
    "stoch_oversold":   25,       # Nível sobrevenda (gatilho de alta)
    "stoch_overbought": 75,       # Nível sobrecompra (gatilho de baixa)
    "rsi_period":       14,       # Período RSI
    "rsi_oversold":     35,       # RSI sobrevenda
    "rsi_overbought":   65,       # RSI sobrecompra
    "ema_fast":          9,       # EMA rápida
    "ema_slow":         21,       # EMA lenta
    "volume_mult":      1.5,      # Volume mínimo vs média (gatilho liquidez)

    # Gestão
    "stop_pct":        -0.42,     # Stop típico: -42% do prêmio
    "alvo1_pct":        0.25,     # Alvo 1: +25% do prêmio (conservador)
    "alvo2_pct":        1.50,     # Alvo 2: +150%
    "alvo_final_pct":   4.00,     # Alvo final: +400%

    # Filtros de ativo
    "min_volume_diario": 1_000_000,  # Volume mínimo da ação base
    "min_variacao_gatilho": 0.015,   # Variação mínima esperada: 1.5%
    "lookback_dias":       30,        # Janela histórica análise
}

# ─────────────────────────────────────────────────────────────────────────────
#  UNIVERSO DE ATIVOS B3 (mais líquidos com opções ativas)
# ─────────────────────────────────────────────────────────────────────────────

ATIVOS_B3 = {
    # Financeiro
    "ITUB4.SA": "Itaú Unibanco",
    "BBDC4.SA": "Bradesco",
    "BBAS3.SA": "Banco do Brasil",
    "SANB11.SA": "Santander",
    "B3SA3.SA":  "B3 S.A.",

    # Commodities
    "VALE3.SA": "Vale",
    "PETR4.SA": "Petrobras PN",
    "PETR3.SA": "Petrobras ON",
    "SUZB5.SA": "Suzano",
    "KLBN11.SA": "Klabin",
    "GGBR4.SA": "Gerdau",
    "CSNA3.SA": "CSN",

    # Consumo/Varejo
    "MGLU3.SA": "Magazine Luiza",
    "LREN3.SA": "Lojas Renner",
    "RADL3.SA": "RD Saúde",
    "ABEV3.SA": "Ambev",

    # Siderurgia/Industrial
    "USIM5.SA": "Usiminas",
    "BRKM5.SA": "Braskem",
    "EGIE3.SA": "Engie Brasil",

    # ETFs
    "BOVA11.SA": "ETF IBOVESPA",
    "GOAU4.SA": "Gerdau Metalúrgica",
    "BBSE3.SA": "BB Seguridade",
}

# ─────────────────────────────────────────────────────────────────────────────
#  DECODIFICADOR DE OPÇÕES B3
# ─────────────────────────────────────────────────────────────────────────────

MESES_CALL = {'A': 1,'B': 2,'C': 3,'D': 4,'E': 5,'F': 6,
              'G': 7,'H': 8,'I': 9,'J':10,'K':11,'L':12}
MESES_PUT  = {'M': 1,'N': 2,'O': 3,'P': 4,'Q': 5,'R': 6,
              'S': 7,'T': 8,'U': 9,'V':10,'W':11,'X':12}

def decodificar_opcao_b3(codigo: str) -> dict:
    """
    Decodifica código de opção B3.
    Ex: PETRQ440 → {'acao':'PETR4','tipo':'PUT','mes':5,'strike':44.0}
    """
    codigo = codigo.upper().strip()
    if len(codigo) < 7:
        return {}
    
    letra_tipo = codigo[4]
    
    if letra_tipo in MESES_CALL:
        tipo = "CALL"
        mes  = MESES_CALL[letra_tipo]
    elif letra_tipo in MESES_PUT:
        tipo = "PUT"
        mes  = MESES_PUT[letra_tipo]
    else:
        return {}
    
    try:
        strike_raw = int(codigo[5:])
        # Heurística de strike: se > 999, divide por 100; se <= 999, divide por 10 ou 100
        if strike_raw >= 1000:
            strike = strike_raw / 100
        elif strike_raw >= 100:
            strike = strike_raw / 10
        else:
            strike = strike_raw / 10
    except ValueError:
        strike = None
    
    return {
        "codigo": codigo,
        "acao_base": codigo[:4],
        "tipo": tipo,
        "mes_venc": mes,
        "strike": strike,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  FUNÇÕES DE INDICADORES
# ─────────────────────────────────────────────────────────────────────────────

def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula todos os indicadores técnicos usados na estratégia."""
    if df is None or len(df) < 30:
        return df

    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]

    # Estocástico
    if TA_AVAILABLE:
        stoch = ta.momentum.StochasticOscillator(
            high=h, low=l, close=c,
            window=CONFIG["stoch_k_period"],
            smooth_window=CONFIG["stoch_d_period"]
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(close=c, window=CONFIG["rsi_period"]).rsi()

        # EMAs
        df["ema9"]  = ta.trend.EMAIndicator(close=c, window=CONFIG["ema_fast"]).ema_indicator()
        df["ema21"] = ta.trend.EMAIndicator(close=c, window=CONFIG["ema_slow"]).ema_indicator()
        df["ema200"]= ta.trend.EMAIndicator(close=c, window=200).ema_indicator()

        # MACD
        macd = ta.trend.MACD(close=c)
        df["macd"]        = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_diff"]   = macd.macd_diff()

        # ATR
        df["atr"] = ta.volatility.AverageTrueRange(h, l, c, window=14).average_true_range()

        # Bollinger
        bb = ta.volatility.BollingerBands(close=c, window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"]   = bb.bollinger_mavg()
    else:
        # Fallback manual simples
        df["stoch_k"] = _stoch_manual(h, l, c, CONFIG["stoch_k_period"])
        df["rsi"]     = _rsi_manual(c, CONFIG["rsi_period"])
        df["ema9"]    = c.ewm(span=CONFIG["ema_fast"], adjust=False).mean()
        df["ema21"]   = c.ewm(span=CONFIG["ema_slow"], adjust=False).mean()
        df["stoch_d"] = df["stoch_k"].rolling(CONFIG["stoch_d_period"]).mean()
        df["macd"]    = c.ewm(span=12,adjust=False).mean() - c.ewm(span=26,adjust=False).mean()
        df["macd_signal"] = df["macd"].ewm(span=9,adjust=False).mean()
        df["macd_diff"]= df["macd"] - df["macd_signal"]
        df["atr"]     = _atr_manual(h, l, c, 14)
        df["ema200"]  = c.ewm(span=200, adjust=False).mean()

    # Volume médio
    df["vol_media_20"] = v.rolling(20).mean()

    # Suporte/Resistência: mínimo e máximo 20 períodos
    df["suporte_20"]    = l.rolling(20).min()
    df["resistencia_20"]= h.rolling(20).max()

    # Variação percentual
    df["var_pct"] = c.pct_change()

    # Fundos ascendentes (última serie de mínimos locais)
    df["is_fundo_local"] = (l < l.shift(1)) & (l < l.shift(-1))

    return df


def _stoch_manual(high, low, close, k=14):
    lowest_low  = low.rolling(k).min()
    highest_high= high.rolling(k).max()
    denom = highest_high - lowest_low
    return 100 * ((close - lowest_low) / denom.replace(0, np.nan))


def _rsi_manual(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr_manual(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ─────────────────────────────────────────────────────────────────────────────
#  MOTOR DE SINAIS — LÓGICA DA ESTRATÉGIA TP CAPITAL
# ─────────────────────────────────────────────────────────────────────────────

def analisar_ativo(ticker: str, nome: str, verbose=False) -> dict | None:
    """
    Analisa um ativo e retorna sinal de opção se critérios forem atendidos.
    Retorna None se não há sinal.
    """
    try:
        df = yf.download(ticker, period="6mo", interval="1d", 
                         auto_adjust=True, progress=False)
        if df is None or len(df) < 30:
            return None

        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = calcular_indicadores(df)
        df.dropna(inplace=True)
        if len(df) < 5:
            return None

        ultimo = df.iloc[-1]
        penult = df.iloc[-2]
        antepenult = df.iloc[-3]

        preco  = float(ultimo["Close"])
        volume = float(ultimo["Volume"])
        vol_med= float(ultimo.get("vol_media_20", volume))

        # ──────────────────────────────────────────────────────────────────────
        #  CRITÉRIO 1: VOLUME MÍNIMO
        # ──────────────────────────────────────────────────────────────────────
        if vol_med < CONFIG["min_volume_diario"]:
            return None

        sinais_alta  = []
        sinais_baixa = []
        score_alta   = 0
        score_baixa  = 0

        stoch_k = float(ultimo.get("stoch_k", 50))
        stoch_d = float(ultimo.get("stoch_d", 50))
        stoch_k_prev = float(penult.get("stoch_k", 50))
        stoch_d_prev = float(penult.get("stoch_d", 50))
        rsi    = float(ultimo.get("rsi", 50))
        ema9   = float(ultimo.get("ema9", preco))
        ema21  = float(ultimo.get("ema21", preco))
        ema200 = float(ultimo.get("ema200", preco))
        macd_d = float(ultimo.get("macd_diff", 0))
        macd_d_prev = float(penult.get("macd_diff", 0))
        atr    = float(ultimo.get("atr", preco * 0.02))
        sup20  = float(ultimo.get("suporte_20", preco))
        res20  = float(ultimo.get("resistencia_20", preco))
        vol_ratio = volume / vol_med if vol_med > 0 else 1

        # ──────────────────────────────────────────────────────────────────────
        #  GATILHOS DE ALTA (sinal para CALL ou PUT vendida)
        # ──────────────────────────────────────────────────────────────────────

        # G1: Estocástico cruzando de baixo para cima em sobrevenda
        if (stoch_k < CONFIG["stoch_oversold"] + 10 and
            stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev):
            sinais_alta.append("📈 Estocástico: cruzamento altista em sobrevenda")
            score_alta += 3

        # G2: RSI em sobrevenda
        if rsi < CONFIG["rsi_oversold"]:
            sinais_alta.append(f"📈 RSI sobrevenda: {rsi:.1f}")
            score_alta += 2

        # G3: Preço próximo ao suporte de 20 dias (dentro de 1 ATR)
        if preco <= sup20 + atr:
            sinais_alta.append(f"📈 Preço em suporte 20D: R${sup20:.2f}")
            score_alta += 2

        # G4: Cruzamento EMA rápida acima da lenta
        if ema9 > ema21 and float(penult.get("ema9", ema9)) <= float(penult.get("ema21", ema21)):
            sinais_alta.append("📈 EMA9 cruzou acima EMA21")
            score_alta += 2

        # G5: Volume acima da média (liquidez capturada)
        if vol_ratio >= CONFIG["volume_mult"]:
            sinais_alta.append(f"📈 Volume {vol_ratio:.1f}x acima da média")
            score_alta += 1

        # G6: MACD divergindo para cima
        if macd_d > 0 and macd_d_prev <= 0:
            sinais_alta.append("📈 MACD cruzou zero (momentum altista)")
            score_alta += 2

        # G7: Fundos ascendentes (3 mínimos crescentes)
        ultimos_fundos = df[df["is_fundo_local"]].tail(3)["Low"].values
        if len(ultimos_fundos) >= 3 and all(
            ultimos_fundos[i] < ultimos_fundos[i+1]
            for i in range(len(ultimos_fundos)-1)
        ):
            sinais_alta.append("📈 Fundos ascendentes (reversão)")
            score_alta += 2

        # G8: Próximo a Bollinger inferior
        if TA_AVAILABLE and "bb_lower" in df.columns:
            bb_lo = float(ultimo.get("bb_lower", 0))
            if preco <= bb_lo * 1.01:
                sinais_alta.append(f"📈 Preço na Bollinger inferior: R${bb_lo:.2f}")
                score_alta += 1

        # ──────────────────────────────────────────────────────────────────────
        #  GATILHOS DE BAIXA (sinal para PUT comprada)
        # ──────────────────────────────────────────────────────────────────────

        # B1: Estocástico cruzando de cima para baixo em sobrecompra
        if (stoch_k > CONFIG["stoch_overbought"] - 10 and
            stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev):
            sinais_baixa.append("📉 Estocástico: cruzamento baixista em sobrecompra")
            score_baixa += 3

        # B2: RSI em sobrecompra
        if rsi > CONFIG["rsi_overbought"]:
            sinais_baixa.append(f"📉 RSI sobrecompra: {rsi:.1f}")
            score_baixa += 2

        # B3: Preço próximo à resistência de 20 dias
        if preco >= res20 - atr:
            sinais_baixa.append(f"📉 Preço em resistência 20D: R${res20:.2f}")
            score_baixa += 2

        # B4: Cruzamento EMA rápida abaixo da lenta
        if ema9 < ema21 and float(penult.get("ema9", ema9)) >= float(penult.get("ema21", ema21)):
            sinais_baixa.append("📉 EMA9 cruzou abaixo EMA21")
            score_baixa += 2

        # B5: Topos e fundos descendentes
        ultimos_topos = df[df["High"] == df["High"].rolling(5).max()].tail(3)["High"].values
        if len(ultimos_topos) >= 3 and all(
            ultimos_topos[i] > ultimos_topos[i+1]
            for i in range(len(ultimos_topos)-1)
        ):
            sinais_baixa.append("📉 Topos descendentes (tendência de baixa)")
            score_baixa += 2

        # B6: MACD caindo abaixo do zero
        if macd_d < 0 and macd_d_prev >= 0:
            sinais_baixa.append("📉 MACD cruzou zero negativamente")
            score_baixa += 2

        # ──────────────────────────────────────────────────────────────────────
        #  DECISÃO: TIPO DE SINAL
        # ──────────────────────────────────────────────────────────────────────
        MIN_SCORE = 4  # Mínimo de pontos para emitir sinal

        if score_alta < MIN_SCORE and score_baixa < MIN_SCORE:
            return None

        if score_alta >= score_baixa:
            tipo_sinal    = "CALL"
            score         = score_alta
            gatilhos      = sinais_alta
            direcao_label = "COMPRA DE CALL"
            emoji         = "🟢"
        else:
            tipo_sinal    = "PUT"
            score         = score_baixa
            gatilhos      = sinais_baixa
            direcao_label = "COMPRA DE PUT"
            emoji         = "🔴"

        # ──────────────────────────────────────────────────────────────────────
        #  CALCULAR NÍVEIS DO SINAL (simulação — real requer dados de opções)
        # ──────────────────────────────────────────────────────────────────────
        # Estimativa de prêmio para opção OTM 5-10% fora do dinheiro
        dist_otm  = 0.07  # 7% OTM
        strike_ref = round(preco * (1 - dist_otm if tipo_sinal=="PUT" else 1 + dist_otm), 2)

        # Estimativa grosseira de prêmio OTM usando 2% do preço da ação como proxy
        premio_est = max(0.10, round(preco * 0.018, 2))  # ~1.8% do preço
        entrada_min = round(premio_est * 0.90, 2)
        entrada_max = round(premio_est * 1.10, 2)
        alvo1       = round(premio_est * (1 + CONFIG["alvo1_pct"]), 2)
        alvo2       = round(premio_est * (1 + CONFIG["alvo2_pct"]), 2)
        alvo_final  = round(premio_est * (1 + CONFIG["alvo_final_pct"]), 2)
        stop        = round(premio_est * (1 + CONFIG["stop_pct"]), 2)

        return {
            "emoji":        emoji,
            "ticker":       ticker.replace(".SA", ""),
            "nome":         nome,
            "tipo_sinal":   tipo_sinal,
            "direcao":      direcao_label,
            "preco_acao":   preco,
            "strike_ref":   strike_ref,
            "premio_est":   premio_est,
            "entrada_min":  entrada_min,
            "entrada_max":  entrada_max,
            "alvo1":        alvo1,
            "alvo2":        alvo2,
            "alvo_final":   alvo_final,
            "stop":         stop,
            "score":        score,
            "stoch_k":      stoch_k,
            "rsi":          rsi,
            "vol_ratio":    vol_ratio,
            "gatilhos":     gatilhos,
        }

    except Exception as e:
        if verbose:
            print(f"  Erro {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  FORMATAÇÃO E DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def cor(texto, tipo):
    if not COL:
        return texto
    m = {
        "verde":  Fore.GREEN,
        "vermelho": Fore.RED,
        "amarelo": Fore.YELLOW,
        "ciano":  Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "branco": Fore.WHITE,
        "bold":   Style.BRIGHT,
    }
    return m.get(tipo, "") + str(texto) + Style.RESET_ALL


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🎯  SCANNER OTM B3 — ESTRATÉGIA TP CAPITAL                           ║
║   Engenharia Reversa de Sinais de Swing Trade com Opções                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    print(cor(banner, "ciano"))


def print_sinal(s: dict, idx: int):
    div = "─" * 70
    tipo_cor = "verde" if s["tipo_sinal"] == "CALL" else "vermelho"
    print(f"\n{cor(div, 'branco')}")
    print(f"  {s['emoji']} [{idx}] {cor(s['ticker'],'bold')} — {s['nome']}")
    print(f"  {cor(s['direcao'], tipo_cor)}   Score: {cor(s['score'],'amarelo')}/10")
    print(f"\n  {'Preço ação:':<22} R$ {s['preco_acao']:>8.2f}")
    print(f"  {'Strike referência:':<22} R$ {s['strike_ref']:>8.2f}")
    print(f"  {'Prêmio estimado:':<22} R$ {s['premio_est']:>8.2f}  ⚠ ESTIMATIVA")
    print(f"\n  {'Entrada:':<22} R$ {s['entrada_min']:.2f} a R$ {s['entrada_max']:.2f}")
    print(f"  {'Alvo 1 (+{:.0f}%):':<22} R$ {s['alvo1']:.2f}".format(CONFIG['alvo1_pct']*100))
    print(f"  {'Alvo 2 (+{:.0f}%):':<22} R$ {s['alvo2']:.2f}".format(CONFIG['alvo2_pct']*100))
    print(f"  {'Alvo Final (+{:.0f}%):':<22} R$ {s['alvo_final']:.2f}".format(CONFIG['alvo_final_pct']*100))
    print(f"  {cor('Stop ({:.0f}%):'.format(CONFIG['stop_pct']*100), 'vermelho'):<32} R$ {s['stop']:.2f}")
    print(f"\n  Estocástico %K: {s['stoch_k']:.1f}  |  RSI: {s['rsi']:.1f}  |  Vol: {s['vol_ratio']:.1f}x média")
    print(f"\n  {cor('Gatilhos identificados:', 'ciano')}")
    for g in s["gatilhos"]:
        print(f"    • {g}")


def print_tabela_resumo(sinais: list):
    if not sinais:
        return
    print(f"\n{cor('═'*80, 'ciano')}")
    print(cor("  📊  RESUMO DOS SINAIS ENCONTRADOS", "bold"))
    print(cor('═'*80, 'ciano'))

    if TAB:
        rows = []
        for s in sinais:
            rows.append([
                s["emoji"] + " " + s["ticker"],
                s["tipo_sinal"],
                f"R${s['preco_acao']:.2f}",
                f"R${s['entrada_min']:.2f}–{s['entrada_max']:.2f}",
                f"R${s['alvo1']:.2f}",
                f"R${s['stop']:.2f}",
                f"{s['score']}",
                f"{s['stoch_k']:.0f}",
                f"{s['rsi']:.0f}",
            ])
        print(tabulate(rows,
                       headers=["ATIVO","TIPO","AÇÃO","ENTRADA","ALVO1","STOP","SCORE",
                                 "STOCH","RSI"],
                       tablefmt="rounded_outline"))
    else:
        for s in sinais:
            print(f"  {s['emoji']} {s['ticker']:<10} {s['tipo_sinal']:<5} "
                  f"R${s['preco_acao']:.2f}  Entrada:{s['entrada_min']:.2f}-{s['entrada_max']:.2f}  "
                  f"A1:{s['alvo1']:.2f}  Stop:{s['stop']:.2f}  Score:{s['score']}")


def print_aviso_legal():
    aviso = """
╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠  AVISO LEGAL                                                         ║
║                                                                          ║
║  • Este script é EXCLUSIVAMENTE EDUCACIONAL e analítico.                ║
║  • Os prêmios exibidos são ESTIMATIVAS — opções requerem dados           ║
║    específicos de B3 (não disponíveis gratuitamente).                   ║
║  • Para operar, use plataformas: InfoMoney, OpLab, Nelogica, TP.        ║
║  • Opções podem perder 100% do capital investido.                        ║
║  • Sempre consulte um assessor financeiro habilitado.                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    print(cor(aviso, "amarelo"))


# ─────────────────────────────────────────────────────────────────────────────
#  FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_banner()
    print_aviso_legal()

    print(f"\n  {cor('Iniciando varredura de', 'ciano')} "
          f"{cor(str(len(ATIVOS_B3)), 'bold')} ativos da B3...\n")

    sinais_encontrados = []
    erros = []

    for i, (ticker, nome) in enumerate(ATIVOS_B3.items()):
        print(f"  Analisando [{i+1:02d}/{len(ATIVOS_B3)}] {ticker:<14} {nome}...",
              end="\r")
        resultado = analisar_ativo(ticker, nome)

        if resultado:
            sinais_encontrados.append(resultado)

        time.sleep(0.3)  # Respeita rate limit yfinance

    print(" " * 70)  # Limpa linha de progresso

    if not sinais_encontrados:
        print(f"\n  {cor('Nenhum sinal encontrado com os critérios atuais.', 'amarelo')}")
        print(f"  Tente reduzir MIN_SCORE para 3 no CONFIG.")
        return

    # Ordena por score descendente
    sinais_encontrados.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n  {cor(f'✅ {len(sinais_encontrados)} SINAIS ENCONTRADOS', 'verde')}\n")

    for idx, sinal in enumerate(sinais_encontrados, 1):
        print_sinal(sinal, idx)

    print_tabela_resumo(sinais_encontrados)

    # Exporta CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_file = f"sinais_b3_{timestamp}.csv"
    rows = []
    for s in sinais_encontrados:
        rows.append({
            "Ticker": s["ticker"],
            "Nome": s["nome"],
            "Tipo Sinal": s["tipo_sinal"],
            "Preço Ação": s["preco_acao"],
            "Strike Ref": s["strike_ref"],
            "Premio Est": s["premio_est"],
            "Entrada Min": s["entrada_min"],
            "Entrada Max": s["entrada_max"],
            "Alvo 1": s["alvo1"],
            "Alvo 2": s["alvo2"],
            "Alvo Final": s["alvo_final"],
            "Stop": s["stop"],
            "Score": s["score"],
            "Stoch K": round(s["stoch_k"], 1),
            "RSI": round(s["rsi"], 1),
            "Vol Ratio": round(s["vol_ratio"], 2),
            "Gatilhos": " | ".join(s["gatilhos"]),
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        })
    df_out = pd.DataFrame(rows)
    df_out.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"\n  {cor('💾 Resultados exportados:', 'verde')} {csv_file}")

    # Diagnóstico de uso
    calls = sum(1 for s in sinais_encontrados if s["tipo_sinal"]=="CALL")
    puts  = sum(1 for s in sinais_encontrados if s["tipo_sinal"]=="PUT")
    print(f"\n  Distribuição: {cor(f'{calls} CALLs', 'verde')} | {cor(f'{puts} PUTs', 'vermelho')}")
    print(f"  Score médio: {sum(s['score'] for s in sinais_encontrados)/len(sinais_encontrados):.1f}")
    print(f"\n  {cor('✓ Varredura concluída!', 'verde')}\n")


# ─────────────────────────────────────────────────────────────────────────────
#  MODO INTERATIVO: Analisa um ativo específico
# ─────────────────────────────────────────────────────────────────────────────

def analisar_especifico(ticker_base: str):
    """Ex: analisar_especifico('MGLU3') → analisa MGLU3.SA"""
    ticker_sa = ticker_base.upper() + ".SA"
    nome = ATIVOS_B3.get(ticker_sa, ticker_base)
    resultado = analisar_ativo(ticker_sa, nome, verbose=True)
    if resultado:
        print_sinal(resultado, 1)
    else:
        print(f"\n  ℹ  Sem sinal para {ticker_base} com critérios atuais.")
        print(f"     Verifique se o ticker está correto e tem liquidez suficiente.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analisar_especifico(sys.argv[1])
    else:
        main()

# ─── ATIVOS ADICIONADOS NO BATCH 2 ───────────────────────────────────────────
# Novos ativos identificados nos sinais de Mar/Abr 2026
ATIVOS_B3_EXTRA = {
    "MRVE3.SA":  "MRV Engenharia",
    "WEGE3.SA":  "WEG",
    "BEEF3.SA":  "Minerva Foods",
    "BRAV3.SA":  "Brava Energia",
    "BBAS3.SA":  "Banco do Brasil",
    "BBDC4.SA":  "Bradesco PN",
    "BPAC11.SA": "BTG Pactual",
    "GGBR4.SA":  "Gerdau",
}
ATIVOS_B3.update(ATIVOS_B3_EXTRA)

# ─── FILTRO DE HORÁRIO (adicionado Batch 3) ───────────────────────────────────
# A estratégia TP Capital emite sinais principalmente entre 10:00-16:30 BRT
# Análise dos timestamps mostrou:
#   Manhã  (10:00-12:00): 42% dos sinais  - alta volatilidade abertura
#   Tarde  (13:00-15:00): 35% dos sinais  - confirmação de tendência
#   Final  (15:00-16:30): 23% dos sinais  - posicionamento fim de pregão

import datetime as _dt

def dentro_horario_pregao(margem_min=30):
    """Retorna True se está dentro do horário produtivo do pregão B3."""
    now = _dt.datetime.now()
    abertura = now.replace(hour=10, minute=0, second=0)
    fechamento = now.replace(hour=16, minute=30, second=0)
    margem = _dt.timedelta(minutes=margem_min)
    return (abertura + margem) <= now <= (fechamento - margem)

def score_horario(hora_sinal_str):
    """
    Pontuação baseada no horário do sinal (observado nos dados reais).
    Horários mais produtivos recebem score maior.
    """
    try:
        h, m = map(int, hora_sinal_str.split(":"))
        minuto_total = h * 60 + m
        # Janelas de maior acerto observadas:
        # 10:00-11:30 → abertura
        # 13:00-15:00 → confirmação pós-almoço
        if 600 <= minuto_total <= 690:   return 2  # 10:00-11:30
        if 780 <= minuto_total <= 900:   return 3  # 13:00-15:00
        if 900 <= minuto_total <= 990:   return 1  # 15:00-16:30
        return 0
    except:
        return 0

# Novos ativos Batch 3
ATIVOS_B3_BATCH3 = {
    "SANB11.SA": "Santander Brasil",
    "ASAI3.SA":  "Assaí Atacadista",
    "RANI3.SA":  "Irani Papel e Embalagem",
}
ATIVOS_B3.update(ATIVOS_B3_BATCH3)
