/**
 * Black-Scholes Option Pricing & Greeks Calculator
 * Pure TypeScript — zero external dependencies
 *
 * Ported from gregas_fase1_expandido.html with full dividend yield support.
 * Uses Abramowitz-Stegun approximation for normalCDF (error < 7.5×10⁻⁸).
 */

// ── Distribution helpers ────────────────────────────────────────────────────

/** Error function approximation — Abramowitz-Stegun */
export function erf(x: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  const absX = Math.abs(x);
  const t = 1 / (1 + p * absX);
  const y =
    1 -
    ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) *
      t *
      Math.exp(-absX * absX);
  return sign * y;
}

/** Cumulative standard normal distribution — derived from erf(x / √2) */
export function normalCDF(x: number): number {
  return 0.5 * (1 + erf(x / Math.sqrt(2)));
}

/** Standard normal probability density function */
export function normalPDF(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

// ── Black-Scholes core ──────────────────────────────────────────────────────

/** d₁ = [ln(S/K) + (r − q + σ²/2)·T] / (σ·√T) */
export function calcD1(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number = 0,
): number {
  const sqT = Math.sqrt(T);
  return (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT);
}

/** d₂ = d₁ − σ·√T */
export function calcD2(d1: number, sigma: number, T: number): number {
  return d1 - sigma * Math.sqrt(T);
}

/** Call price: S·e^(−qT)·N(d₁) − K·e^(−rT)·N(d₂) */
export function callPrice(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number = 0,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  return S * Math.exp(-q * T) * normalCDF(d1) - K * Math.exp(-r * T) * normalCDF(d2);
}

/** Put price: K·e^(−rT)·N(−d₂) − S·e^(−qT)·N(−d₁) */
export function putPrice(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number = 0,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  return K * Math.exp(-r * T) * normalCDF(-d2) - S * Math.exp(-q * T) * normalCDF(-d1);
}

// ── Moneyness ───────────────────────────────────────────────────────────────

export type Moneyness = 'ITM' | 'ATM' | 'OTM';

/** Classify moneyness based on option type */
export function getMoneyness(
  S: number,
  K: number,
  tipo: 'call' | 'put',
): Moneyness {
  if (tipo === 'call') {
    return S > K ? 'ITM' : S < K ? 'OTM' : 'ATM';
  }
  return S < K ? 'ITM' : S > K ? 'OTM' : 'ATM';
}

// ── First-order Greeks ──────────────────────────────────────────────────────

/** Delta: e^(−qT)·N(d₁) [call] or e^(−qT)·(N(d₁)−1) [put] */
export function calcDelta(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  tipo: 'call' | 'put',
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const eqT = Math.exp(-q * T);
  return tipo === 'call' ? eqT * normalCDF(d1) : eqT * (normalCDF(d1) - 1);
}

/** Gamma: e^(−qT)·n(d₁) / (S·σ·√T) — same for call and put */
export function calcGamma(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  return (normalPDF(d1) * Math.exp(-q * T)) / (S * sigma * Math.sqrt(T));
}

/**
 * Theta (per calendar day, /365)
 * Full formula with dividend yield support.
 */
export function calcTheta(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  tipo: 'call' | 'put',
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  const sqT = Math.sqrt(T);
  const eqT = Math.exp(-q * T);
  const erT = Math.exp(-r * T);

  const commonTerm = -(S * eqT * normalPDF(d1) * sigma) / (2 * sqT);

  if (tipo === 'call') {
    return (commonTerm - r * K * erT * normalCDF(d2) + q * S * eqT * normalCDF(d1)) / 365;
  }
  return (commonTerm + r * K * erT * normalCDF(-d2) - q * S * eqT * normalCDF(-d1)) / 365;
}

/** Vega: S·e^(−qT)·n(d₁)·√T / 100  (per 1% change in vol) */
export function calcVega(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  return (S * Math.exp(-q * T) * normalPDF(d1) * Math.sqrt(T)) / 100;
}

// ── Second-order Greeks ─────────────────────────────────────────────────────

/** Vanna: −e^(−qT)·n(d₁)·d₂/σ */
export function calcVanna(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  return -normalPDF(d1) * d2 / sigma * Math.exp(-q * T);
}

/** Volga: Vega·d₁·d₂/σ */
export function calcVolga(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  const vega = calcVega(S, K, T, sigma, r, q);
  return (vega * d1 * d2) / sigma;
}

// ── Probability ITM ─────────────────────────────────────────────────────────

/** Probability of finishing in-the-money: N(d₂) for call, N(−d₂) for put */
export function calcProbITM(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  tipo: 'call' | 'put',
): number {
  const d1 = calcD1(S, K, T, sigma, r, q);
  const d2 = calcD2(d1, sigma, T);
  return tipo === 'call' ? normalCDF(d2) : normalCDF(-d2);
}

// ── Implied Volatility Solver ───────────────────────────────────────────────

/**
 * Newton-Raphson IV solver with bisection fallback.
 * Returns NaN if no solution exists (e.g. marketPrice ≤ 0 or below intrinsic).
 *
 * Note: calcVega returns vega per 1% vol change (÷100), so raw vega per unit σ = calcVega × 100.
 */
export function impliedVol(
  marketPrice: number,
  S: number,
  K: number,
  T: number,
  r: number,
  type: 'call' | 'put',
  q: number = 0,
  sigma0: number = 0.3,
): number {
  if (marketPrice <= 0 || T <= 0) return NaN;

  const bs = (s: number) =>
    type === 'call' ? callPrice(S, K, T, s, r, q) : putPrice(S, K, T, s, r, q);

  // Newton-Raphson
  let sigma = sigma0;
  for (let i = 0; i < 100; i++) {
    const price = bs(sigma);
    const diff = price - marketPrice;
    if (Math.abs(diff) < 1e-6) return sigma;
    const vega = calcVega(S, K, T, sigma, r, q) * 100; // per unit σ
    if (Math.abs(vega) < 1e-10) break;
    sigma = sigma - diff / vega;
    if (sigma <= 0) { sigma = 0.001; break; }
  }

  // Bisection fallback [0.001, 5.0]
  let lo = 0.001, hi = 5.0;
  if (Math.sign(bs(lo) - marketPrice) === Math.sign(bs(hi) - marketPrice)) return NaN;
  for (let i = 0; i < 100; i++) {
    const mid = (lo + hi) / 2;
    if (hi - lo < 1e-6) return mid;
    if (Math.sign(bs(mid) - marketPrice) === Math.sign(bs(lo) - marketPrice)) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

// ── All-in-one calculator ───────────────────────────────────────────────────

export interface BSResult {
  price: number;
  d1: number;
  d2: number;
  moneyness: Moneyness;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  vanna: number;
  volga: number;
  probITM: number;
}

/**
 * Calculate all BS outputs in a single pass (avoids redundant d1/d2 computation).
 * T is in years (e.g. 30/365 for 30 calendar days).
 */
export function calcAll(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  tipo: 'call' | 'put',
): BSResult {
  if (T <= 0 || sigma <= 0) {
    return {
      price: 0, d1: 0, d2: 0, moneyness: getMoneyness(S, K, tipo),
      delta: 0, gamma: 0, theta: 0, vega: 0, vanna: 0, volga: 0, probITM: 0,
    };
  }

  const sqT = Math.sqrt(T);
  const eqT = Math.exp(-q * T);
  const erT = Math.exp(-r * T);

  const d1 = (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqT);
  const d2 = d1 - sigma * sqT;

  const nd1 = normalCDF(d1);
  const nd2 = normalCDF(d2);
  const pd1 = normalPDF(d1);

  // Price
  let price: number;
  if (tipo === 'call') {
    price = S * eqT * nd1 - K * erT * nd2;
  } else {
    price = K * erT * normalCDF(-d2) - S * eqT * normalCDF(-d1);
  }

  // Delta
  const delta = tipo === 'call' ? eqT * nd1 : eqT * (nd1 - 1);

  // Gamma (same for call and put)
  const gamma = (pd1 * eqT) / (S * sigma * sqT);

  // Theta (per calendar day)
  const commonTheta = -(S * eqT * pd1 * sigma) / (2 * sqT);
  let theta: number;
  if (tipo === 'call') {
    theta = (commonTheta - r * K * erT * nd2 + q * S * eqT * nd1) / 365;
  } else {
    theta = (commonTheta + r * K * erT * normalCDF(-d2) - q * S * eqT * normalCDF(-d1)) / 365;
  }

  // Vega (per 1% vol change)
  const vega = (S * eqT * pd1 * sqT) / 100;

  // Vanna
  const vanna = (-pd1 * d2 / sigma) * eqT;

  // Volga
  const volga = (vega * d1 * d2) / sigma;

  // Probability ITM
  const probITM = tipo === 'call' ? nd2 : normalCDF(-d2);

  return {
    price, d1, d2,
    moneyness: getMoneyness(S, K, tipo),
    delta, gamma, theta, vega, vanna, volga, probITM,
  };
}
