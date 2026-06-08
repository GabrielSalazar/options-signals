import type { AssetAnalysisPayload, AssetScoreBreakdown, AssetScoreResult, AssetVerdict } from './types/analytics';

function scorePos52s(payload: AssetAnalysisPayload): number {
  const { preco_atual, faixa_52s_min, faixa_52s_max } = payload;
  const range = faixa_52s_max - faixa_52s_min;
  if (range <= 0) return 1;
  const pos = (preco_atual - faixa_52s_min) / range;
  if (pos < 0.30) return 2;
  if (pos < 0.50) return 1;
  return 0;
}

function scoreMAs(payload: AssetAnalysisPayload): number {
  const { preco_atual, ma20, ma50 } = payload;
  const belowMa20 = preco_atual < ma20;
  const belowMa50 = preco_atual < ma50;
  if (belowMa20 && belowMa50) return 2;
  if (belowMa20 || belowMa50) return 1;
  return 0;
}

function scoreRsi(payload: AssetAnalysisPayload): number {
  const { rsi14 } = payload;
  if (rsi14 < 30) return 2;
  if (rsi14 <= 55) return 1;
  return 0;
}

function scoreBollinger(payload: AssetAnalysisPayload): number {
  const { bollinger_pct_b } = payload;
  if (bollinger_pct_b < 0.20) return 2;
  if (bollinger_pct_b <= 0.50) return 1;
  return 0;
}

function scoreZScore(payload: AssetAnalysisPayload): number {
  const { z_score_20 } = payload;
  if (z_score_20 < -1.0) return 2;
  if (z_score_20 <= 0) return 1;
  return 0;
}

export function scoreAsset(payload: AssetAnalysisPayload): AssetScoreResult {
  const breakdown: AssetScoreBreakdown = {
    pos52s:    scorePos52s(payload),
    mas:       scoreMAs(payload),
    rsi:       scoreRsi(payload),
    bollinger: scoreBollinger(payload),
    zscore:    scoreZScore(payload),
  };

  const score = breakdown.pos52s + breakdown.mas + breakdown.rsi + breakdown.bollinger + breakdown.zscore;

  let verdict: AssetVerdict;
  if (score >= 7) verdict = 'barato';
  else if (score >= 4) verdict = 'neutro';
  else verdict = 'caro';

  return { score, verdict, breakdown };
}
