"""Constantes globais do projeto.

Consolidação de valores hardcoded espalhados pelo código.
Usar este arquivo como fonte única de verdade para tuning.

Categorizado por domínio:
- BACKTEST: parâmetros de simulação
- TRADING: limiares, thresholds, períodos
- CACHE: TTL, limites de tamanho
- TIME: horários de pregão, fusos
- API: limites de rate limiting
"""

# ============================================================================
# BACKTEST: Simulação de estratégias
# ============================================================================

BACKTEST_INITIAL_EQUITY = 10000.0  # R$ - Saldo inicial para simulação
BACKTEST_PRECISION_DECIMAL = 2  # Casas decimais para cálculos monetários


# ============================================================================
# TRADING: Indicadores técnicos & gatilhos
# ============================================================================

## RSI (Relative Strength Index)
RSI_PERIOD = 14  # Candles
RSI_OVERSOLD = 35  # Threshold (<35 = oversold)
RSI_OVERBOUGHT = 65  # Threshold (>65 = overbought)
RSI_NEUTRAL_DEFAULT = 50.0  # Fallback quando RSI indisponível

## Stochastic (%K, %D)
STOCH_K_PERIOD = 14  # Candles
STOCH_D_PERIOD = 3  # EMA do %K
STOCH_OVERSOLD = 25  # Threshold (<25 = oversold)
STOCH_OVERBOUGHT = 75  # Threshold (>75 = overbought)
STOCH_NEUTRAL_DEFAULT = 50.0  # Fallback quando Stoch indisponível

## EMA (Exponential Moving Average)
EMA_FAST_PERIOD = 9  # Candles (curto prazo)
EMA_SLOW_PERIOD = 21  # Candles (longo prazo)

## ADX (Average Directional Index)
ADX_VETO_MIN = 15.0  # ADX abaixo = lateralidade (veto sinal)
ADX_REDUTOR_MIN = 20.0  # ADX abaixo = redutor -2% score
ADX_GATILHO_MIN = 25.0  # ADX acima = gatilho G18/B18

## MFI (Money Flow Index)
MFI_OVERSOLD = 30.0
MFI_OVERBOUGHT = 70.0

## IV (Implied Volatility)
IV_RANK_BLOQUEIO = 80  # >80 = bloqueia sinal
IV_RANK_ATENCAO = 70  # >70 = reduz score
IV_RANK_PISO = 10  # <10 = alerta de baixa vol

## Scoring
MIN_SCORE_PONDERADO = 60  # Mínimo para sinal ser emitido
LOOKBACK_DIAS = 30  # Período de análise histórica


# ============================================================================
# CACHE: TTL e limites de memória
# ============================================================================

CACHE_DEFAULT_TTL_SECONDS = 300  # 5 minutos - padrão
CACHE_MEM_MAX_ENTRIES = 1000  # Max entradas em memória (prune ao exceder)
CACHE_LONG_TTL_SECONDS = 3600  # 1 hora - cache longo (daily data)
CACHE_SHORT_TTL_SECONDS = 60  # 1 minuto - cache curto (real-time)


# ============================================================================
# TIME: Horários e fusos
# ============================================================================

## Pregão (horários em minutos desde 00:00 em São Paulo)
PREGAO_ABERTURA_MINUTOS = 570  # 09:30
PREGAO_ENCERRAMENTO_MINUTOS = 990  # 16:30

## Períodos intraday (horário de SP)
PERIODO_1_INICIO_MINUTOS = 600  # 10:00
PERIODO_1_FIM_MINUTOS = 690  # 11:30
PERIODO_2_INICIO_MINUTOS = 780  # 13:00
PERIODO_2_FIM_MINUTOS = 900  # 15:00
PERIODO_3_INICIO_MINUTOS = 900  # 15:00
PERIODO_3_FIM_MINUTOS = 990  # 16:30

## Margem de segurança (minutos antes/depois do pregão)
PREGAO_MARGEM_SEGURANCA_MINUTOS = 30


# ============================================================================
# API: Rate limiting, timeouts
# ============================================================================

RATE_LIMIT_REQUESTS_PER_MINUTE = 200  # Limite geral
RATE_LIMIT_BY_IP_PER_MINUTE = 50  # Limite por IP
TIMEOUT_BRAPI_SEGUNDOS = 10  # Timeout para BrAPI calls
TIMEOUT_SUPABASE_SEGUNDOS = 30  # Timeout para queries


# ============================================================================
# LOGGING & MONITORING
# ============================================================================

LOG_LEVEL_DEFAULT = "INFO"
LOG_LEVEL_PRODUCTION = "WARNING"
LOG_LEVEL_DEVELOPMENT = "DEBUG"


# ============================================================================
# FEATURE FLAGS (para A/B testing ou rollout gradual)
# ============================================================================

FEATURE_IV_SCORING = True  # Usar IV no scoring de sinais
FEATURE_ADX_GATILHO = True  # Usar ADX como gatilho
FEATURE_MFI_FILTER = True  # Filtro por MFI


# ============================================================================
# Utilidades para uso
# ============================================================================

def get_periodo_by_minuto(minuto: int) -> int:
    """Retorna período (1, 2, 3) baseado em minuto do dia."""
    if PERIODO_1_INICIO_MINUTOS <= minuto < PERIODO_1_FIM_MINUTOS:
        return 1
    elif PERIODO_2_INICIO_MINUTOS <= minuto < PERIODO_2_FIM_MINUTOS:
        return 2
    elif PERIODO_3_INICIO_MINUTOS <= minuto < PERIODO_3_FIM_MINUTOS:
        return 3
    return 0  # Fora do pregão
