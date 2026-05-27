'use client';

import { useState, useMemo } from 'react';
import { Slider } from '@/components/ui/slider';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Leg, calculateStrategy } from '@/lib/strategies';
import { randomNormal } from '@/lib/monte-carlo';
import { fmtCcy, fmtNum } from '@/lib/format';

interface Props {
  legs: Leg[];
  S0: number;
  T: number; // in days
  sigma: number; // in %
  r: number; // in %
  q: number; // in %
}

export default function HedgingSimulator({ legs, S0, T, sigma, r, q }: Props) {
  const [multiplier, setMultiplier] = useState(1000); // 1000 estruturas
  const [realizedVol, setRealizedVol] = useState(sigma); // Vol realizada (em %)

  // Portfolio Current Greeks (aggregate of 1 unit of strategy)
  const baseResult = useMemo(() => {
    return calculateStrategy(legs, S0, T / 365, sigma / 100, r / 100, q / 100);
  }, [legs, S0, T, sigma, r, q]);

  // Delta Hedging logic
  const totalDelta = baseResult.greeks.delta * multiplier;
  const totalGamma = baseResult.greeks.gamma * multiplier;
  const totalTheta = baseResult.greeks.theta * multiplier;
  
  // To neutralize delta, we take the opposite position in the underlying asset
  const hedgeShares = -Math.round(totalDelta);

  // Gamma Scalping Path Simulation (1 path)
  const simulationPath = useMemo(() => {
    if (legs.length === 0 || T <= 0) return [];
    
    const steps = T;
    const dt = 1 / 365; // 1 day in years
    const rDec = r / 100;
    const qDec = q / 100;
    const impliedVolDec = sigma / 100;
    const realVolDec = realizedVol / 100;
    const drift = (rDec - qDec - 0.5 * realVolDec * realVolDec) * dt;
    const volStep = realVolDec * Math.sqrt(dt);

    let currentS = S0;
    let accumulatedHedgePnl = 0;
    
    // We start delta hedged
    let currentStrategyDelta = baseResult.greeks.delta * multiplier;
    let currentHedgeShares = -Math.round(currentStrategyDelta);

    const pathData = [];

    // T=0
    pathData.push({
      day: 0,
      S: currentS,
      portfolioValue: 0, // baseline
      hedgeValue: 0,
      netValue: 0,
    });

    const currentPortfolioCost = baseResult.totalCost * multiplier;

    for (let t = 1; t <= steps; t++) {
      // Simulate 1 day step
      const Z = randomNormal();
      const nextS = currentS * Math.exp(drift + volStep * Z);
      
      // Calculate PnL of hedge from S moving
      const hedgePnl = currentHedgeShares * (nextS - currentS);
      accumulatedHedgePnl += hedgePnl;

      // Re-evaluate Portfolio at new S and new T
      const timeRemaining = (T - t) / 365;
      const res = calculateStrategy(legs, nextS, timeRemaining > 0 ? timeRemaining : 0.0001, impliedVolDec, rDec, qDec);
      const newPortfolioValue = res.totalCost * multiplier;
      
      // PnL of portfolio compared to entry
      const portfolioPnl = newPortfolioValue - currentPortfolioCost;

      // Net PnL
      const netPnl = portfolioPnl + accumulatedHedgePnl;

      pathData.push({
        day: t,
        S: nextS,
        portfolioValue: portfolioPnl,
        hedgeValue: accumulatedHedgePnl,
        netValue: netPnl,
      });

      // Rebalance Hedge for next day
      currentS = nextS;
      currentStrategyDelta = res.greeks.delta * multiplier;
      currentHedgeShares = -Math.round(currentStrategyDelta);
    }

    return pathData;
  }, [legs, S0, T, sigma, realizedVol, multiplier, r, q, baseResult.totalCost, baseResult.greeks.delta]);

  return (
    <div className="hedging-simulator mt-8 bg-white border border-dw-rule rounded-xl p-6 shadow-sm">
      <div className="mb-6 border-b-2 border-dw-ink pb-2">
        <h2 className="text-xl font-serif text-dw-ink mb-1">Delta Hedging & Gamma Scalping</h2>
        <p className="text-sm text-dw-ink-muted">
          Simule a neutralização do risco direcional e a captura de prêmio através do rebalanceamento diário.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        {/* Controls */}
        <div className="p-4 bg-dw-bg-soft border border-dw-rule-soft rounded-xl flex flex-col justify-center">
          <label className="block text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">Parâmetros de Hedge</label>
          <div className="flex flex-col gap-2">
            <div className="text-xs font-medium text-dw-ink-mid flex justify-between">
              <span>Multiplicador (Tamanho)</span>
              <span className="font-mono font-bold text-dw-blue">{fmtNum(multiplier)}x</span>
            </div>
            <Slider value={[multiplier]} min={100} max={10000} step={100} onValueChange={([v]) => setMultiplier(v)} />
          </div>
          <div className="my-4"></div>
          <div className="flex flex-col gap-2">
            <div className="text-xs font-medium text-dw-ink-mid flex justify-between">
              <span>Vol. Realizada (vs {sigma}%)</span>
              <span className="font-mono font-bold text-dw-blue">{realizedVol}%</span>
            </div>
            <Slider value={[realizedVol]} min={5} max={100} step={1} onValueChange={([v]) => setRealizedVol(v)} />
          </div>
        </div>

        {/* Dashboard */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4 flex flex-col justify-center">
            <div className="text-[11px] text-dw-ink-muted mb-1 uppercase font-bold tracking-widest">Delta Total da Posição</div>
            <div className="text-xl font-mono font-bold text-dw-ink">{fmtNum(totalDelta)}</div>
            <div className="text-xs text-dw-ink-light mt-2">
              Você está {totalDelta > 0 ? 'comprado' : 'vendido'} em Risco de Preço.
            </div>
          </div>
          <div className="bg-dw-bg-soft border border-dw-blue rounded-xl p-4 flex flex-col justify-center" style={{ background: 'rgba(24, 95, 165, 0.05)' }}>
            <div className="text-[11px] text-dw-blue mb-1 uppercase font-bold tracking-widest">Ação Necessária (Zero Delta)</div>
            <div className="text-xl font-mono font-bold" style={{ color: hedgeShares > 0 ? 'var(--dw-green)' : 'var(--dw-red)' }}>
              {hedgeShares > 0 ? `Comprar ${fmtNum(hedgeShares)} ações` : hedgeShares < 0 ? `Vender a descoberto ${fmtNum(Math.abs(hedgeShares))} ações` : 'Posição já neutra'}
            </div>
            <div className="text-xs text-dw-blue mt-2 opacity-80">
              Isso neutraliza seu risco de S±R$1.
            </div>
          </div>
          <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4 flex flex-col justify-center">
            <div className="text-[11px] text-dw-ink-muted mb-1 uppercase font-bold tracking-widest">Perfil Gamma / Theta</div>
            <div className="text-sm font-mono font-bold mt-1">
              Gamma: <span className={totalGamma > 0 ? 'text-dw-green' : 'text-dw-red'}>{fmtNum(totalGamma)}</span>
            </div>
            <div className="text-sm font-mono font-bold mt-1">
              Theta/Dia: <span className={totalTheta > 0 ? 'text-dw-green' : 'text-dw-red'}>{fmtCcy(totalTheta)}</span>
            </div>
            <div className="text-[10px] text-dw-ink-light mt-2">
              {totalGamma > 0 ? 'Você precisa de Vol Realizada > Vol Implícita' : 'Você precisa de Vol Realizada < Vol Implícita'}
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4" style={{ height: 400 }}>
        <h3 className="text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">Simulação 1 Caminho: Gamma Scalping P&L</h3>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={simulationPath} margin={{ top: 10, right: 10, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
            <XAxis dataKey="day" fontSize={11} tickFormatter={(v) => `Dia ${v}`} />
            <YAxis fontSize={11} tickFormatter={(v) => `R$${Math.round(v)}`} />
            <Tooltip 
              contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
              formatter={fmtCcy}
              labelFormatter={(l) => `Dia ${l}`}
            />
            <Legend />
            <Line type="monotone" dataKey="portfolioValue" name="Opções P&L" stroke="#185FA5" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="hedgeValue" name="Hedge (Ações) P&L" stroke="#993C1D" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="netValue" name="Net P&L (Gamma Scalping)" stroke="#0F6E56" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
