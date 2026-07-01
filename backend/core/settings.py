from pydantic import Field
from pydantic_settings import BaseSettings


class MotorSettings(BaseSettings):
    # ── Indicadores ──
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    stoch_smooth: int = 3
    stoch_oversold: int = 25
    stoch_overbought: int = 75
    rsi_period: int = 14
    rsi_oversold: int = 35
    rsi_overbought: int = 65
    ema_fast: int = 9
    ema_slow: int = 21
    volume_mult: float = 1.5
    # ── Gestao de risco ──
    stop_pct: float = -0.43
    alvo1_pct: float = 0.25
    alvo2_pct: float = 2.50
    alvo_final_pct: float = 7.00
    buy_band_pct: float = 0.035
    book_days: int = 7
    # ── Filtros ──
    min_volume_acoes: int = 1_000_000
    min_variacao_gatilho: float = 0.015
    lookback_dias: int = 30
    min_score: int = 5
    scoring_mode: str = Field(default="classico", pattern="^(classico|ponderado)$")
    min_score_ponderado: int = 60
    iv_filter_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    familia_cap_oscilador: int = 4
    familia_cap_tendencia: int = 4
    familia_cap_estrutura: int = 3
    familia_cap_divergencia: int = 3
    familia_cap_liquidez: int = 4
    delta_min: float = 0.05
    delta_max: float = 0.55
    option_price_min: float = 0.10
    option_price_max: float = 3.00
    min_negocios_opcao: int = 10
    # ── DTE ──
    dte_minimo: int = 5
    dte_maximo: int = 45
    # ── Reentrada ──
    reentrada_min_dias: int = 3
    reentrada_mesma_direcao_dias: int = 3
    reentrada_direcao_oposta_delta_score: int = 2
    # ── Pivots locais ──
    pivot_ordem: int = 1
    # ── Carregador de tickers ──
    min_volume_rs: int = 5_000_000
    ticker_top_n: int = 150
    ticker_cache_segundos: int = 3600
    # ── Scan / notificacoes ──
    scan_max_workers: int = 8
    telegram_throttle_s: float = 0.5
    # ── Telegram (opcional) ──
    # Lidas sem prefixo MOTOR_ para manter compatibilidade com o .env/ambiente
    # de producao ja configurado com TELEGRAM_TOKEN/TELEGRAM_CHAT_ID.
    telegram_token: str = Field(default="", alias="TELEGRAM_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    model_config = {"env_prefix": "MOTOR_", "populate_by_name": True}
