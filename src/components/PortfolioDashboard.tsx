'use client';

import { useState, useMemo } from 'react';
import { Plus, Trash2, ShieldAlert } from 'lucide-react';
import { calcAll } from '@/lib/black-scholes';
import { fmtCcy, fmtNum } from '@/lib/format';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine, Legend
} from 'recharts';

type PosType = 'call' | 'put' | 'stock';

interface Position {
  id: string;
  ticker: string;
  type: PosType;
  quantity: number; // positive = long, negative = short
  strike?: number;
  T?: number; // days to expiry
  sigma?: number; // implied vol
  S0: number; // current price
}

export default function PortfolioDashboard() {
  const [positions, setPositions] = useState<Position[]>([
    { id: '1', ticker: 'PETR4', type: 'call', quantity: 1000, strike: 35, T: 30, sigma: 25, S0: 36.5 },
    { id: '2', ticker: 'PETR4', type: 'stock', quantity: -500, S0: 36.5 }, // partial hedge
    { id: '3', ticker: 'VALE3', type: 'put', quantity: 2000, strike: 60, T: 45, sigma: 30, S0: 62.0 },
  ]);

  const [newTicker, setNewTicker] = useState('BOVA11');
  const [newType, setNewType] = useState<PosType>('call');

  const r = 10.75 / 100;
  const q = 0; // simple dividend assumption

  // Calculate Greeks per position
  const evaluatedPositions = useMemo(() => {
    return positions.map(pos => {
      let delta = 0, gamma = 0, theta = 0, vega = 0, value = 0;

      if (pos.type === 'stock') {
        value = pos.S0 * pos.quantity;
        delta = 1 * pos.quantity;
      } else if (pos.T && pos.sigma && pos.strike) {
        const bs = calcAll(pos.S0, pos.strike, pos.T / 365, pos.sigma / 100, r, q, pos.type);
        value = bs.price * pos.quantity;
        delta = bs.delta * pos.quantity;
        gamma = bs.gamma * pos.quantity;
        theta = bs.theta * pos.quantity;
        vega = bs.vega * pos.quantity;
      }

      return {
        ...pos,
        value,
        delta,
        gamma,
        theta,
        vega
      };
    });
  }, [positions, r, q]);

  // Aggregate Greeks (Note: Delta is technically per underlying, but we sum them for a naive view, ideally should be Beta-weighted)
  const totalValue = evaluatedPositions.reduce((acc, p) => acc + p.value, 0);
  const totalDelta = evaluatedPositions.reduce((acc, p) => acc + p.delta, 0);
  const totalGamma = evaluatedPositions.reduce((acc, p) => acc + p.gamma, 0);
  const totalTheta = evaluatedPositions.reduce((acc, p) => acc + p.theta, 0);
  const totalVega = evaluatedPositions.reduce((acc, p) => acc + p.vega, 0);

  // Group Greeks by Ticker
  const greeksByTicker = useMemo(() => {
    const map = new Map<string, { delta: number, gamma: number, vega: number, theta: number }>();
    for (const p of evaluatedPositions) {
      if (!map.has(p.ticker)) map.set(p.ticker, { delta: 0, gamma: 0, vega: 0, theta: 0 });
      const obj = map.get(p.ticker)!;
      obj.delta += p.delta;
      obj.gamma += p.gamma;
      obj.vega += p.vega;
      obj.theta += p.theta;
    }
    return Array.from(map.entries()).map(([ticker, g]) => ({ ticker, ...g }));
  }, [evaluatedPositions]);

  const addPosition = () => {
    const p: Position = {
      id: Date.now().toString(),
      ticker: newTicker,
      type: newType,
      quantity: 100,
      S0: 100,
      ...(newType !== 'stock' ? { strike: 100, T: 30, sigma: 20 } : {})
    };
    setPositions([...positions, p]);
  };

  const removePosition = (id: string) => {
    setPositions(positions.filter(p => p.id !== id));
  };

  const updatePosition = (id: string, field: keyof Position, val: string | number) => {
    setPositions(positions.map(p => {
      if (p.id === id) {
        return { ...p, [field]: typeof val === 'string' && field !== 'ticker' && field !== 'type' ? Number(val) : val };
      }
      return p;
    }));
  };

  return (
    <div className="portfolio-dashboard">
      
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <RiskCard label="Net Liquidation Value" value={fmtCcy(totalValue)} color="var(--dw-ink)" />
        <RiskCard label="Total Delta (Ações)" value={fmtNum(totalDelta)} color={totalDelta > 0 ? "var(--dw-green)" : "var(--dw-red)"} desc="Beta-weighted proxy" />
        <RiskCard label="Total Gamma" value={fmtNum(totalGamma)} color={totalGamma > 0 ? "var(--dw-green)" : "var(--dw-red)"} />
        <RiskCard label="Total Vega" value={fmtCcy(totalVega)} color={totalVega > 0 ? "var(--dw-green)" : "var(--dw-red)"} desc="Impacto de +1% na Vol" />
        <RiskCard label="Total Theta" value={fmtCcy(totalTheta)} color={totalTheta > 0 ? "var(--dw-green)" : "var(--dw-red)"} desc="Decay Diário" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Positions Table */}
        <div className="lg:col-span-2 card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-serif text-lg">Livro de Posições</h3>
            <div className="flex gap-2 items-center">
              <input type="text" value={newTicker} onChange={e => setNewTicker(e.target.value.toUpperCase())} className="border border-dw-rule rounded px-2 py-1 text-sm font-mono w-24" />
              <select value={newType} onChange={e => setNewType(e.target.value as PosType)} className="border border-dw-rule rounded px-2 py-1 text-sm bg-white">
                <option value="call">Call</option>
                <option value="put">Put</option>
                <option value="stock">Ação</option>
              </select>
              <button onClick={addPosition} className="btn-secondary py-1 px-2 flex items-center gap-1"><Plus className="w-4 h-4"/> Add</button>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-dw-rule text-left text-xs uppercase text-dw-ink-muted">
                <tr>
                  <th className="pb-2">Ativo</th>
                  <th className="pb-2">Qtd</th>
                  <th className="pb-2">S₀</th>
                  <th className="pb-2">Strike</th>
                  <th className="pb-2">DTE</th>
                  <th className="pb-2">Vol(%)</th>
                  <th className="pb-2 text-right">Valor</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody>
                {evaluatedPositions.map(pos => (
                  <tr key={pos.id} className="border-b border-dw-rule-soft last:border-0 hover:bg-dw-bg-soft transition-colors">
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold">{pos.ticker}</span>
                        <span className={`text-[10px] uppercase px-1.5 py-0.5 rounded font-bold ${
                          pos.type==='call'?'bg-green-100 text-green-700':pos.type==='put'?'bg-red-100 text-red-700':'bg-blue-100 text-blue-700'
                        }`}>{pos.type}</span>
                      </div>
                    </td>
                    <td className="py-2">
                      <input type="number" value={pos.quantity} onChange={e => updatePosition(pos.id, 'quantity', e.target.value)} className="w-20 border rounded px-1 font-mono text-xs" />
                    </td>
                    <td className="py-2">
                      <input type="number" value={pos.S0} onChange={e => updatePosition(pos.id, 'S0', e.target.value)} className="w-16 border rounded px-1 font-mono text-xs" />
                    </td>
                    <td className="py-2">
                      {pos.type !== 'stock' && <input type="number" value={pos.strike} onChange={e => updatePosition(pos.id, 'strike', e.target.value)} className="w-16 border rounded px-1 font-mono text-xs" />}
                    </td>
                    <td className="py-2">
                      {pos.type !== 'stock' && <input type="number" value={pos.T} onChange={e => updatePosition(pos.id, 'T', e.target.value)} className="w-12 border rounded px-1 font-mono text-xs" />}
                    </td>
                    <td className="py-2">
                      {pos.type !== 'stock' && <input type="number" value={pos.sigma} onChange={e => updatePosition(pos.id, 'sigma', e.target.value)} className="w-12 border rounded px-1 font-mono text-xs" />}
                    </td>
                    <td className="py-2 text-right font-mono font-bold" style={{ color: pos.value >= 0 ? 'var(--dw-ink)' : 'var(--dw-red)' }}>
                      {fmtCcy(pos.value)}
                    </td>
                    <td className="py-2 text-right">
                      <button onClick={() => removePosition(pos.id)} className="text-dw-ink-muted hover:text-dw-red transition-colors"><Trash2 className="w-4 h-4"/></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Re-Hedging Global */}
        <div className="card bg-dw-bg-soft border border-dw-rule flex flex-col justify-between">
          <div>
            <h3 className="font-serif text-lg mb-2 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-dw-blue" />
              Gestão de Risco Global
            </h3>
            <p className="text-sm text-dw-ink-light mb-4">
              Monitoramento das concentrações de gregas por ativo base. Se o Delta estiver muito distorcido, você deve realocar comprando ou vendendo a ação.
            </p>
            
            <div className="space-y-3">
              {greeksByTicker.map(g => (
                <div key={g.ticker} className="bg-white border border-dw-rule-soft rounded-lg p-3">
                  <div className="font-mono font-bold text-sm mb-1">{g.ticker}</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>Delta: <span className={g.delta > 0 ? "text-dw-green" : "text-dw-red font-bold"}>{fmtNum(g.delta)}</span></div>
                    <div>Gamma: <span className={g.gamma > 0 ? "text-dw-green" : "text-dw-red font-bold"}>{fmtNum(g.gamma)}</span></div>
                  </div>
                  {Math.abs(g.delta) > 500 && (
                    <div className="mt-2 pt-2 border-t border-dw-rule-soft text-xs text-dw-blue font-semibold">
                      → Sugestão: {g.delta > 0 ? `Vender ${fmtNum(g.delta)} ações` : `Comprar ${fmtNum(Math.abs(g.delta))} ações`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Heatmap/Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card" style={{ height: 350 }}>
          <h3 className="text-xs font-bold uppercase tracking-widest text-dw-blue mb-4">Exposição Delta por Ativo</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={greeksByTicker} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" fontSize={11} />
              <YAxis dataKey="ticker" type="category" fontSize={11} width={80} />
              <Tooltip formatter={fmtNum} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <ReferenceLine x={0} stroke="var(--dw-ink)" />
              <Bar dataKey="delta">
                {greeksByTicker.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.delta >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ height: 350 }}>
          <h3 className="text-xs font-bold uppercase tracking-widest text-dw-blue mb-4">Decay (Theta) vs Vega por Ativo</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={greeksByTicker} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="ticker" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip formatter={fmtCcy} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <ReferenceLine y={0} stroke="var(--dw-ink)" />
              <Legend />
              <Bar dataKey="theta" name="Theta (Dia)" fill="var(--dw-red)" />
              <Bar dataKey="vega" name="Vega (1%)" fill="var(--dw-blue)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}

function RiskCard({ label, value, color, desc }: { label: string; value: string; color: string; desc?: string }) {
  return (
    <div className="bg-white border border-dw-rule rounded-xl p-4 flex flex-col justify-center">
      <div className="text-[11px] text-dw-ink-muted mb-1 uppercase font-bold tracking-widest">{label}</div>
      <div className="text-xl font-mono font-bold" style={{ color }}>{value}</div>
      {desc && <div className="text-[10px] text-dw-ink-light mt-1">{desc}</div>}
    </div>
  );
}
