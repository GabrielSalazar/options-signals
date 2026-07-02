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
    # Thresholds do filtro de IV (matriz v2 §2.5: banda operável 10-70, veto >80)
    iv_rank_bloqueio: int = 80
    iv_rank_atencao: int = 70
    iv_rank_piso: int = 10
    # Caps por família (matriz v2 §5: oscilador/momentum/tendencia/estrutura 4, liquidez 3).
    # MOMENTUM (MACD + divergência RSI; futuramente MFI/OBV/CMF) substitui a antiga DIVERGENCIA.
    familia_cap_oscilador: int = 4
    familia_cap_momentum: int = 4
    familia_cap_tendencia: int = 4
    familia_cap_estrutura: int = 4
    familia_cap_liquidez: int = 3
    # Tolerância de distância a suporte/resistência 20D em múltiplos de ATR (matriz v2 §2.4)
    sr_tolerancia_atr: float = 1.5
    # ── Matriz v2 — Fase 1 (gatilhos novos, redutores e vetos técnicos) ──
    # "shadow": avalia e reporta nos campos *_v2 do sinal, sem afetar score/emissão.
    # "ativo": gatilhos novos somam no score, redutores subtraem e vetos bloqueiam.
    matriz_v2_gatilhos_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    veto_adx_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    veto_supertrend_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    veto_bw_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    veto_ema200_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    adx_veto_min: float = 15.0      # ADX abaixo disso = lateralidade (veto)
    adx_redutor_min: float = 20.0   # ADX abaixo disso = redutor -2
    adx_gatilho_min: float = 25.0   # ADX acima disso = gatilho G18/B18
    bw_compressao_max: float = 0.10  # BW abaixo disso = compressão (G19/B19)
    bw_aberto_min: float = 0.25      # BW acima disso + preço no meio = veto
    mfi_oversold: float = 30.0
    mfi_overbought: float = 70.0
    cci_extremo: float = 100.0
    # ── Camada PUCK (HC institucional, fluxo normalizado, breakout) ──
    # "shadow": gatilhos G20/B20/G21/B21 reportam com 0 pontos; modificadores
    # de classe só registram razões. "ativo": pontos reais e classe alterada.
    puck_gatilhos_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    absorcao_classe_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    fluxo_upgrade_mode: str = Field(default="shadow", pattern="^(shadow|ativo)$")
    hc_fator_volume: float = 1.5        # HC exige volume > fator × média20 (institucional)
    cmf_z_periodo: int = 21             # janela do z-score do CMF (PUCK v4.4 §5)
    cmf_z_gatilho: float = 1.0          # z mínimo p/ G20/B20 (1.0=padrão, 1.5=seletivo)
    absorcao_clv_max: float = 0.1       # |CLV| abaixo disso = fluxo neutro (absorção)
    fluxo_persistencia_clv: float = 0.3 # CLV direcional mínimo p/ contar persistência
    fluxo_persistencia_min: int = 3     # dias consecutivos p/ candidato a upgrade C→B
    atr_mult_stop: float = 1.5          # stop no ativo = entrada ∓ mult × ATR
    atr_mult_tp1: float = 1.5           # TP1 (realizar 50%)
    atr_mult_tp2: float = 3.0           # TP2 (R:R 2:1)
    # Banda de delta = veto absoluto da matriz v2 §4 (a faixa ideal 0,15-0,45 é
    # critério de classe, não de emissão)
    delta_min: float = 0.10
    delta_max: float = 0.50
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
