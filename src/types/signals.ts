// Matches exactly the dict returned by core_engine.analisar_ativo()
export interface Signal {
  ticker: string
  nome: string
  tipo_sinal: 'CALL' | 'PUT'
  direcao: string
  preco_acao: number
  ticker_opcao: string
  strike_ref: number
  dist_otm_pct: number
  hv_20d: number
  dte: number
  mes_venc: number
  ano_venc: number
  premio_est: number
  preco_tela: number | null
  entrada_min: number
  entrada_max: number
  alvo1: number
  alvo2: number
  alvo_final: number
  stop: number
  rr_alvo1: number
  rr_alvo2: number
  rr_final: number
  score: number
  stoch_k: number
  rsi: number
  vol_ratio: number
  vol_media_20?: number
  gatilhos: string[]
  // v4.0: Greeks (Black-Scholes) + book + score ponderado
  book_until?: string
  greeks?: {
    delta: number
    gamma: number
    theta: number
    vega: number
    rho: number
    prob_profit: number
  }
  score_ponderado?: number | null
  ponderado_passou?: boolean | null
  ponderado_reasons?: string[]
  // Matriz v2 — Fase 2 (classe shadow / sizing)
  classe_v2?: 'A' | 'B' | 'C' | null
  razoes_downgrade_classe?: string[] | null
  divergencia_premio_pct?: number | null
  sizing_sugerido_pct?: number | null
  // Matriz v2 — gatilhos shadow (G12-G22, texto + IDs)
  gatilhos_v2?: string[] | null
  gatilhos_v2_ids?: string[] | null
  // Matriz v2 — Fase 3 (executabilidade, dados D-1 da B3)
  oi?: number | null
  bid?: number | null
  ask?: number | null
  spread_pct?: number | null
  vxbr?: number | null
  evento_label?: string | null
  filtro_liquidez_decisao?: 'normal' | 'atencao' | 'bloquear' | null
  filtro_liquidez_motivo?: string | null
  // Camada PUCK (níveis no ativo subjacente + telemetria, shadow)
  ativo_entrada?: number | null
  ativo_stop?: number | null
  ativo_tp1?: number | null
  ativo_tp2?: number | null
  absorcao?: boolean | null
  fluxo_persistencia_dias?: number | null
  cmf_z?: number | null
  cmf_norm?: number | null
  // From Supabase rows
  id?: string
  timestamp?: string
  created_at?: string
}

export interface ScanResponse {
  sinal?: Signal          // Single-ticker scan: POST /signals/scan/{ticker}
  results?: Signal[]      // Batch scan legacy
  data?: Signal[]         // GET /signals (Supabase) and scan/all
  message?: string
}
