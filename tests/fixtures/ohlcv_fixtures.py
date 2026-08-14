"""
Fixtures determinísticas de OHLCV para testes.

Estes dados são congelados e utilizados pelo golden master.
Qualquer mudança no motor de sinais deve passar pelo golden master
com exatamente os mesmos dados de entrada.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

def create_ohlcv_fixture(
    name: str,
    dates: int = 30,
    close: float = 100,
    volatility: float = 0.02,
    trend: float = 0.001,
    pattern: str = "normal"
) -> pd.DataFrame:
    """
    Cria um fixture OHLCV determinístico.

    Args:
        name: Nome do fixture
        dates: Número de dias
        close: Preço de fechamento inicial
        volatility: Volatilidade (desvio padrão)
        trend: Tendência diária (drift)
        pattern: Tipo de padrão ("normal", "empate", "volume_baixo", "veto", "cooldown")

    Returns:
        DataFrame com OHLCV
    """
    dates_list = [datetime(2026, 8, 1) + timedelta(days=i) for i in range(dates)]

    # Gerar preços com movimento browniano geométrico
    np.random.seed(42 + hash(name) % 1000)
    returns = np.random.normal(trend, volatility, dates)
    prices = close * np.exp(np.cumsum(returns))

    data = {
        'data': dates_list,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, dates)),
        'high': prices * (1 + np.abs(np.random.normal(0.01, 0.01, dates))),
        'low': prices * (1 - np.abs(np.random.normal(0.01, 0.01, dates))),
        'close': prices,
        'volume': np.random.uniform(1e6, 1e7, dates)
    }

    # Aplicar padrão especial
    if pattern == "empate":
        # Alta = Baixa (empate entre máxima e mínima)
        data['high'] = data['close']
        data['low'] = data['close']

    elif pattern == "volume_baixo":
        # Volume abaixo do limite mínimo (pode não gerar sinal)
        data['volume'] = np.full(dates, 1e4)

    elif pattern == "veto":
        # Preço muito alto (pode sofrer veto por prêmio caro)
        data['close'] = np.full(dates, 1000.0)
        data['open'] = data['close'] * 1.01
        data['high'] = data['close'] * 1.02
        data['low'] = data['close'] * 0.99

    elif pattern == "cooldown":
        # Padrão que dispara o cooldown de reentrada
        data['close'][:10] = 105
        data['close'][10:] = 95
        data['high'] = data['close'] * 1.01
        data['low'] = data['close'] * 0.99

    df = pd.DataFrame(data)
    df['data'] = pd.to_datetime(df['data'])
    df.set_index('data', inplace=True)

    return df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })


# ============================================================================
# 12 FIXTURES CONGELADOS (Casos de Teste)
# ============================================================================

FIXTURE_CALL_TENDENCIA_ALTA = create_ohlcv_fixture(
    name="call_tendencia_alta",
    dates=30,
    close=100,
    volatility=0.015,
    trend=0.002,
    pattern="normal"
)
"""CALL: Tendência de alta clara. Deve gerar sinal."""

FIXTURE_PUT_TENDENCIA_BAIXA = create_ohlcv_fixture(
    name="put_tendencia_baixa",
    dates=30,
    close=100,
    volatility=0.015,
    trend=-0.002,
    pattern="normal"
)
"""PUT: Tendência de baixa clara. Deve gerar sinal."""

FIXTURE_CALL_SIDEWAYS = create_ohlcv_fixture(
    name="call_sideways",
    dates=30,
    close=100,
    volatility=0.01,
    trend=0.0,
    pattern="normal"
)
"""CALL: Movimento lateral (sem tendência). Pode não gerar sinal."""

FIXTURE_PUT_SIDEWAYS = create_ohlcv_fixture(
    name="put_sideways",
    dates=30,
    close=100,
    volatility=0.01,
    trend=0.0,
    pattern="normal"
)
"""PUT: Movimento lateral. Pode não gerar sinal."""

FIXTURE_EMPATE_ALTA_BAIXA = create_ohlcv_fixture(
    name="empate_alta_baixa",
    dates=30,
    close=100,
    volatility=0.0,  # Sem volatilidade
    trend=0.0,
    pattern="empate"
)
"""EDGE: Alta = Baixa. Caso limite de fechamento sem movimento."""

FIXTURE_VOLUME_ABAIXO_MINIMO = create_ohlcv_fixture(
    name="volume_abaixo_minimo",
    dates=30,
    close=100,
    volatility=0.02,
    trend=0.002,
    pattern="volume_baixo"
)
"""EDGE: Volume abaixo do mínimo aceitável. Deve não gerar sinal."""

FIXTURE_PREMIO_CARO_VETO = create_ohlcv_fixture(
    name="premio_caro_veto",
    dates=30,
    close=100,
    volatility=0.001,
    trend=0.0,
    pattern="veto"
)
"""EDGE: Prêmio muito caro (preço alto). Deve sofrer veto."""

FIXTURE_COOLDOWN_REENTRADA = create_ohlcv_fixture(
    name="cooldown_reentrada",
    dates=30,
    close=100,
    volatility=0.01,
    trend=0.0,
    pattern="cooldown"
)
"""EDGE: Padrão que testa cooldown de reentrada."""

FIXTURE_CALL_ALTA_VOLATILIDADE = create_ohlcv_fixture(
    name="call_alta_volatilidade",
    dates=30,
    close=100,
    volatility=0.05,  # 5% volatilidade alta
    trend=0.001,
    pattern="normal"
)
"""CALL: Alta volatilidade. IV deve estar elevada."""

FIXTURE_PUT_ALTA_VOLATILIDADE = create_ohlcv_fixture(
    name="put_alta_volatilidade",
    dates=30,
    close=100,
    volatility=0.05,
    trend=-0.001,
    pattern="normal"
)
"""PUT: Alta volatilidade. IV deve estar elevada."""

FIXTURE_CALL_REVERSAO = create_ohlcv_fixture(
    name="call_reversao",
    dates=30,
    close=100,
    volatility=0.02,
    trend=0.0,
    pattern="normal"
)
"""CALL: Padrão de reversão (topo seguido de queda)."""
# Simular reversão
df_reversao = FIXTURE_CALL_REVERSAO.copy()
df_reversao.iloc[:15, df_reversao.columns.get_loc('Close')] = 105
df_reversao.iloc[15:, df_reversao.columns.get_loc('Close')] = 95
FIXTURE_CALL_REVERSAO = df_reversao

FIXTURE_PUT_REVERSAO = create_ohlcv_fixture(
    name="put_reversao",
    dates=30,
    close=100,
    volatility=0.02,
    trend=0.0,
    pattern="normal"
)
"""PUT: Padrão de reversão (fundo seguido de subida)."""
df_put_rev = FIXTURE_PUT_REVERSAO.copy()
df_put_rev.iloc[:15, df_put_rev.columns.get_loc('Close')] = 95
df_put_rev.iloc[15:, df_put_rev.columns.get_loc('Close')] = 105
FIXTURE_PUT_REVERSAO = df_put_rev


# Dicionário de fixtures para fácil acesso
FIXTURES: Dict[str, pd.DataFrame] = {
    'call_tendencia_alta': FIXTURE_CALL_TENDENCIA_ALTA,
    'put_tendencia_baixa': FIXTURE_PUT_TENDENCIA_BAIXA,
    'call_sideways': FIXTURE_CALL_SIDEWAYS,
    'put_sideways': FIXTURE_PUT_SIDEWAYS,
    'empate_alta_baixa': FIXTURE_EMPATE_ALTA_BAIXA,
    'volume_abaixo_minimo': FIXTURE_VOLUME_ABAIXO_MINIMO,
    'premio_caro_veto': FIXTURE_PREMIO_CARO_VETO,
    'cooldown_reentrada': FIXTURE_COOLDOWN_REENTRADA,
    'call_alta_volatilidade': FIXTURE_CALL_ALTA_VOLATILIDADE,
    'put_alta_volatilidade': FIXTURE_PUT_ALTA_VOLATILIDADE,
    'call_reversao': FIXTURE_CALL_REVERSAO,
    'put_reversao': FIXTURE_PUT_REVERSAO,
}


def get_fixture(name: str) -> pd.DataFrame:
    """Recuperar um fixture por nome."""
    if name not in FIXTURES:
        raise ValueError(f"Fixture '{name}' não encontrado. Disponíveis: {list(FIXTURES.keys())}")
    return FIXTURES[name].copy()


def list_fixtures() -> Dict[str, str]:
    """Listar todos os fixtures com descrição."""
    return {
        'call_tendencia_alta': 'CALL com tendência de alta clara',
        'put_tendencia_baixa': 'PUT com tendência de baixa clara',
        'call_sideways': 'CALL em movimento lateral',
        'put_sideways': 'PUT em movimento lateral',
        'empate_alta_baixa': 'Edge case: alta = baixa',
        'volume_abaixo_minimo': 'Edge case: volume insuficiente',
        'premio_caro_veto': 'Edge case: prêmio muito caro',
        'cooldown_reentrada': 'Edge case: teste de cooldown',
        'call_alta_volatilidade': 'CALL com IV elevada',
        'put_alta_volatilidade': 'PUT com IV elevada',
        'call_reversao': 'CALL com padrão de reversão',
        'put_reversao': 'PUT com padrão de reversão',
    }
