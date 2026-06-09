export interface ChainItem {
  strike: number;
  preco: number;
  tipo: 'call' | 'put';
  negocios: number;
}

export interface AssetAnalysisPayload {
  ticker: string;
  preco_atual: number;
  hv_20: number;
  hv_60: number;
  ma20: number;
  ma50: number;
  ma200: number;
  sigma_20: number;
  rsi14: number;
  bollinger_pct_b: number;
  z_score_20: number;
  faixa_52s_min: number;
  faixa_52s_max: number;
  macd_diff: number;
  stoch_k: number;
  stoch_d: number;
  adx: number;
  chain: ChainItem[];
}

export type AssetVerdict = 'barato' | 'neutro' | 'caro';
export type OptionVerdict = 'barata' | 'neutra' | 'cara';

export interface AssetScoreBreakdown {
  pos52s: number;
  mas: number;
  rsi: number;
  bollinger: number;
  zscore: number;
}

export interface AssetScoreResult {
  score: number;
  verdict: AssetVerdict;
  breakdown: AssetScoreBreakdown;
}
