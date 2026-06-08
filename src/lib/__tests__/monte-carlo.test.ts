import { describe, it, expect } from 'vitest';
import { randomNormal, runMonteCarlo } from '@/lib/monte-carlo';
import { getLongCallLegs } from '@/lib/strategies';

describe('randomNormal', () => {
  it('produces finite samples with a near-zero mean over many draws', () => {
    let sum = 0;
    const N = 20000;
    for (let i = 0; i < N; i++) {
      const x = randomNormal();
      expect(Number.isFinite(x)).toBe(true);
      sum += x;
    }
    expect(Math.abs(sum / N)).toBeLessThan(0.1);
  });
});

describe('runMonteCarlo', () => {
  const res = runMonteCarlo({
    S0: 100, mu: 0.1, sigma: 0.3, T: 30 / 365, steps: 30,
    numPaths: 2000, legs: getLongCallLegs(100), r: 0.1, q: 0,
  });

  it('caps the number of saved paths at 100', () => {
    expect(res.paths.length).toBeLessThanOrEqual(100);
  });

  it('produces a distribution sized to numPaths', () => {
    expect(res.finalPrices.length).toBe(2000);
    expect(res.pnlDistribution.length).toBe(2000);
  });

  it('reports a win rate within [0,1]', () => {
    expect(res.winRate).toBeGreaterThanOrEqual(0);
    expect(res.winRate).toBeLessThanOrEqual(1);
  });

  it('CVaR is no greater than VaR (tail mean ≤ percentile)', () => {
    expect(res.cvar95).toBeLessThanOrEqual(res.var95 + 1e-6);
  });
});

describe('runMonteCarlo — stockUnits', () => {
  const base = { S0: 100, mu: 0.3, sigma: 0.3, T: 1, steps: 50, numPaths: 8000, legs: [], r: 0.1, q: 0 };

  it('ação comprada → P&L médio positivo; vendida → negativo (mu>0)', () => {
    const long  = runMonteCarlo({ ...base, stockUnits: 1 });
    const short = runMonteCarlo({ ...base, stockUnits: -1 });
    expect(long.meanPnl).toBeGreaterThan(0);
    expect(short.meanPnl).toBeLessThan(0);
  });
});
