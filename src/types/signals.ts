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
  iv_hist: number
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
  gatilhos: string[]
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
