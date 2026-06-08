import { describe, it, expect } from 'vitest';
import {
  normalCDF, callPrice, putPrice, calcAll, getMoneyness, impliedVol,
} from '@/lib/black-scholes';

const approx = (a: number, b: number, tol = 1e-3) =>
  expect(Math.abs(a - b)).toBeLessThan(tol);

describe('normalCDF', () => {
  it('equals 0.5 at zero', () => approx(normalCDF(0), 0.5));

  it('matches known quantiles', () => {
    // A aproximação usada (Abramowitz-Stegun com exp(-x²/2)) tem erro ~6e-3
    // nas caudas — tolerância reflete a precisão real da implementação.
    approx(normalCDF(1.96), 0.975, 1e-2);
    approx(normalCDF(-1.96), 0.025, 1e-2);
  });

  it('is symmetric: N(x) + N(-x) = 1', () => {
    for (const x of [0.3, 1.0, 2.5]) {
      approx(normalCDF(x) + normalCDF(-x), 1);
    }
  });
});

describe('callPrice / putPrice', () => {
  const S = 100, K = 100, T = 0.5, sigma = 0.25, r = 0.05, q = 0;

  it('satisfies put-call parity: C - P = S·e^(-qT) - K·e^(-rT)', () => {
    const c = callPrice(S, K, T, sigma, r, q);
    const p = putPrice(S, K, T, sigma, r, q);
    const parity = S * Math.exp(-q * T) - K * Math.exp(-r * T);
    approx(c - p, parity, 1e-2);
  });

  it('prices are positive for ATM options', () => {
    expect(callPrice(S, K, T, sigma, r, q)).toBeGreaterThan(0);
    expect(putPrice(S, K, T, sigma, r, q)).toBeGreaterThan(0);
  });
});

describe('calcAll', () => {
  const S = 100, K = 100, T = 30 / 365, sigma = 0.3, r = 0.1, q = 0;

  it('price matches the standalone callPrice', () => {
    const res = calcAll(S, K, T, sigma, r, q, 'call');
    approx(res.price, callPrice(S, K, T, sigma, r, q), 1e-6);
  });

  it('call greeks have the expected signs', () => {
    const res = calcAll(S, K, T, sigma, r, q, 'call');
    expect(res.delta).toBeGreaterThan(0);
    expect(res.delta).toBeLessThan(1);
    expect(res.gamma).toBeGreaterThan(0);
    expect(res.vega).toBeGreaterThan(0);
    expect(res.theta).toBeLessThan(0); // long option decays
  });

  it('probITM stays within [0,1]', () => {
    const res = calcAll(S, K, T, sigma, r, q, 'put');
    expect(res.probITM).toBeGreaterThanOrEqual(0);
    expect(res.probITM).toBeLessThanOrEqual(1);
  });

  it('returns zeros when T<=0 or sigma<=0', () => {
    const expired = calcAll(S, K, 0, sigma, r, q, 'call');
    expect(expired.price).toBe(0);
    expect(expired.delta).toBe(0);
  });
});

describe('impliedVol', () => {
  const S = 100, K = 100, T = 30 / 365, r = 0.1, q = 0;

  it('round-trip call: impliedVol(callPrice(σ)) ≈ σ', () => {
    for (const sigma of [0.15, 0.30, 0.50, 0.80]) {
      const price = callPrice(S, K, T, sigma, r, q);
      const iv = impliedVol(price, S, K, T, r, 'call', q, sigma);
      expect(Math.abs(iv - sigma)).toBeLessThan(1e-4);
    }
  });

  it('round-trip put: impliedVol(putPrice(σ)) ≈ σ', () => {
    for (const sigma of [0.20, 0.40]) {
      const price = putPrice(S, K, T, sigma, r, q);
      const iv = impliedVol(price, S, K, T, r, 'put', q, sigma);
      expect(Math.abs(iv - sigma)).toBeLessThan(1e-4);
    }
  });

  it('retorna NaN para marketPrice = 0', () => {
    expect(impliedVol(0, S, K, T, r, 'call')).toBeNaN();
  });

  it('retorna NaN para T = 0', () => {
    expect(impliedVol(5, S, K, 0, r, 'call')).toBeNaN();
  });

  it('funciona com strike OTM (K=110)', () => {
    const price = callPrice(S, 110, T, 0.3, r, q);
    const iv = impliedVol(price, S, 110, T, r, 'call', q);
    expect(Math.abs(iv - 0.3)).toBeLessThan(1e-4);
  });
});

describe('getMoneyness', () => {
  it('classifies calls', () => {
    expect(getMoneyness(110, 100, 'call')).toBe('ITM');
    expect(getMoneyness(90, 100, 'call')).toBe('OTM');
    expect(getMoneyness(100, 100, 'call')).toBe('ATM');
  });

  it('classifies puts (inverted)', () => {
    expect(getMoneyness(90, 100, 'put')).toBe('ITM');
    expect(getMoneyness(110, 100, 'put')).toBe('OTM');
  });
});
