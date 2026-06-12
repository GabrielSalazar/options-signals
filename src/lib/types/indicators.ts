export type SetupStatus = 'ativo' | 'armado' | 'inativo';
export type SetupVies = 'alta' | 'baixa' | 'neutro';

export interface SetupItem {
  nome: string;
  status: SetupStatus;
  vies: SetupVies;
  descricao: string;
}

export type VolRead = 'premio_gordo' | 'premio_barato' | 'neutro' | 'indisponivel';

export interface IndicatorsPayload {
  ticker: string;
  preco_atual: number;
  hora: string;
  rsi14: number;
  stoch_k: number;
  stoch_d: number;
  vol_ratio: number;
  ma20: number; ma50: number; ma200: number;
  adx: number;
  macd_diff: number;
  bollinger_pct_b: number;
  z_score_20: number;
  atr14: number;
  vwap: number;
  vwap_dist_pct: number;
  hv_20: number; hv_60: number;
  sigma_20: number;
  expected_move: number;
  expected_move_pct: number;
  faixa_1sigma: [number, number];
  dte_proximo_venc: number;
  iv_atm: number | null;
  iv_hv_ratio: number | null;
  vol_read: VolRead;
  faixa_52s_min: number;
  faixa_52s_max: number;
  setups: SetupItem[];
}
