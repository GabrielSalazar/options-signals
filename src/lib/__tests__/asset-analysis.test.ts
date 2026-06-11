import { describe, it, expect } from 'vitest';
import { scoreAsset } from '@/lib/asset-analysis';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';

const base: AssetAnalysisPayload = {
  ticker: 'TEST4',
  preco_atual: 38,
  hv_20: 0.30, hv_60: 0.28,
  ma20: 40, ma50: 42, ma200: 45,
  sigma_20: 0.018,
  rsi14: 25,
  bollinger_pct_b: 0.10,
  z_score_20: -1.5,
  faixa_52s_min: 28, faixa_52s_max: 60,
  macd_diff: -0.2, stoch_k: 20, stoch_d: 25, adx: 18,
  preco_graham: null, preco_dcf: null,
  chain: [],
};

describe('scoreAsset — veredito barato', () => {
  it('ativo com todos os indicadores baratos → barato (score ≥ 7)', () => {
    // preco(38) < ma20(40) < ma50(42), RSI=25, %B=0.10, z=-1.5, pos52s=(38-28)/(60-28)=31% → <30%? no, 31% → 1pt
    const r = scoreAsset(base);
    expect(r.verdict).toBe('barato');
    expect(r.score).toBeGreaterThanOrEqual(7);
  });

  it('breakdown soma ao total', () => {
    const r = scoreAsset(base);
    const sum = Object.values(r.breakdown).reduce((a, b) => a + b, 0);
    expect(sum).toBe(r.score);
  });
});

describe('scoreAsset — veredito caro', () => {
  it('ativo com todos os indicadores caros → caro (score ≤ 3)', () => {
    const caro: AssetAnalysisPayload = {
      ...base,
      preco_atual: 58,
      ma20: 50, ma50: 45, ma200: 40,
      rsi14: 80,
      bollinger_pct_b: 0.95,
      z_score_20: 1.5,
      faixa_52s_min: 28, faixa_52s_max: 60,
    };
    const r = scoreAsset(caro);
    expect(r.verdict).toBe('caro');
    expect(r.score).toBeLessThanOrEqual(3);
  });
});

describe('scoreAsset — veredito neutro', () => {
  it('indicadores mistos → neutro (score 4–6)', () => {
    const neutro: AssetAnalysisPayload = {
      ...base,
      preco_atual: 38,
      ma20: 37, ma50: 42,   // abaixo ma50 (1pt), acima ma20 (0pt parcial)
      rsi14: 50,            // 1pt
      bollinger_pct_b: 0.40, // 1pt
      z_score_20: -0.5,     // 1pt
      faixa_52s_min: 28, faixa_52s_max: 60, // pos52s ≈ 31% → 1pt
    };
    const r = scoreAsset(neutro);
    expect(r.verdict).toBe('neutro');
    expect(r.score).toBeGreaterThanOrEqual(4);
    expect(r.score).toBeLessThanOrEqual(6);
  });
});

describe('scoreAsset — casos extremos', () => {
  it('faixa 52s com range = 0 não lança erro', () => {
    const payload = { ...base, faixa_52s_min: 38, faixa_52s_max: 38 };
    expect(() => scoreAsset(payload)).not.toThrow();
  });

  it('RSI = 30 (fronteira) → 1pt', () => {
    const r = scoreAsset({ ...base, rsi14: 30 });
    expect(r.breakdown.rsi).toBe(1);
  });

  it('Bollinger %B = 0.20 (fronteira) → 1pt', () => {
    const r = scoreAsset({ ...base, bollinger_pct_b: 0.20 });
    expect(r.breakdown.bollinger).toBe(1);
  });

  it('z-score = 0 (fronteira) → 1pt', () => {
    const r = scoreAsset({ ...base, z_score_20: 0 });
    expect(r.breakdown.zscore).toBe(1);
  });
});
