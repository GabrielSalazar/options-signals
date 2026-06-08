/**
 * Monte Carlo Simulation for Option Pricing & Risk (VaR / CVaR)
 */

import { calcAll } from './black-scholes';
import { Leg, legIntrinsic, legSign } from './strategies';

// Helper to generate N(0,1) random variables using Box-Muller transform for normal distribution random generation
export function randomNormal(): number {
  let u = 0, v = 0;
  while(u === 0) u = Math.random(); //Converting [0,1) to (0,1)
  while(v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

export interface MonteCarloResult {
  paths: number[][]; // S_t for each step
  finalPrices: number[];
  pnlDistribution: number[];
  var95: number;
  cvar95: number;
  meanPnl: number;
  winRate: number;
}

export interface MonteCarloParams {
  S0: number;
  mu: number; // expected drift (annualized)
  sigma: number; // implied volatility (annualized)
  T: number; // time to expiration (years)
  steps: number; // number of time steps (e.g. days)
  numPaths: number; // number of simulations (e.g. 10000)
  legs: Leg[]; // options portfolio
  r: number; // risk-free rate
  q: number; // dividend yield
  stockUnits?: number; // +1 long, -1 short, 0 nenhum (default 0)
}

export function runMonteCarlo({
  S0, mu, sigma, T, steps, numPaths, legs, r, q, stockUnits = 0
}: MonteCarloParams): MonteCarloResult {
  const dt = T / steps;
  const drift = (mu - 0.5 * sigma * sigma) * dt;
  const vol = sigma * Math.sqrt(dt);

  const paths: number[][] = [];
  const finalPrices = new Float32Array(numPaths);

  // We might not want to save ALL paths in memory if numPaths is 100,000 (OOM risk).
  // We will save only max 100 paths for visualization, but compute final PnL for all.
  const saveMaxPaths = 100;

  for (let p = 0; p < numPaths; p++) {
    const path = new Float32Array(steps + 1);
    path[0] = S0;
    let St = S0;

    for (let t = 1; t <= steps; t++) {
      const Z = randomNormal();
      St = St * Math.exp(drift + vol * Z);
      if (p < saveMaxPaths) {
        path[t] = St;
      }
    }
    
    if (p < saveMaxPaths) {
      paths.push(Array.from(path));
    }
    finalPrices[p] = St;
  }

  // Calculate Entry Cost for the Portfolio
  let entryCost = 0;
  for (const leg of legs) {
    const bs = calcAll(S0, leg.strike, T, sigma, r, q, leg.type);
    entryCost += bs.price * leg.quantity * legSign(leg);
  }

  // Calculate PnL at expiration for each simulated final price
  const pnlDistribution = new Float32Array(numPaths);
  let wins = 0;
  let sumPnl = 0;

  for (let p = 0; p < numPaths; p++) {
    const ST = finalPrices[p];
    let payoff = 0;
    for (const leg of legs) {
      payoff += legIntrinsic(leg, ST) * leg.quantity * legSign(leg);
    }
    const pnl = payoff - entryCost + stockUnits * (ST - S0);
    pnlDistribution[p] = pnl;
    sumPnl += pnl;
    if (pnl > 0) wins++;
  }

  // Sort PnL for VaR and CVaR
  const sortedPnl = Array.from(pnlDistribution).sort((a, b) => a - b);
  
  // VaR 95% (5th percentile)
  const varIndex = Math.floor(numPaths * 0.05);
  const var95 = sortedPnl[varIndex];

  // CVaR 95% (Average of bottom 5%)
  let cvarSum = 0;
  for (let i = 0; i <= varIndex; i++) {
    cvarSum += sortedPnl[i];
  }
  const cvar95 = cvarSum / (varIndex + 1);

  return {
    paths,
    finalPrices: Array.from(finalPrices),
    pnlDistribution: Array.from(pnlDistribution),
    var95,
    cvar95,
    meanPnl: sumPnl / numPaths,
    winRate: wins / numPaths
  };
}
