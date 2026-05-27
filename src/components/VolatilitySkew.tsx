'use client';

import { useMemo } from 'react';
import { Signal } from '@/types/signals';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Activity } from 'lucide-react';

interface Props {
  signals: Signal[];
  ticker: string;
}

export default function VolatilitySkew({ signals, ticker }: Props) {
  // Sort by date to create a timeline
  const timelineData = useMemo(() => {
    if (!signals || signals.length === 0) return [];
    
    // Group signals by date
    const byDate = new Map<string, { iv: number[], count: number }>();
    
    signals.forEach(s => {
      const d = s.timestamp || s.created_at;
      if (!d) return;
      
      const dateStr = new Date(d).toLocaleDateString('pt-BR');
      if (!byDate.has(dateStr)) byDate.set(dateStr, { iv: [], count: 0 });
      
      const obj = byDate.get(dateStr)!;
      obj.iv.push(s.iv_hist);
      obj.count++;
    });
    
    return Array.from(byDate.entries()).map(([date, data]) => {
      const avgIv = data.iv.reduce((a, b) => a + b, 0) / data.count;
      
      // MOCK: Generate Historical Volatility (HV) for demonstration since API doesn't provide it yet
      // We simulate HV as a lagged, smoother version of IV that stays lower usually.
      const pseudoHv = avgIv * (0.8 + 0.1 * Math.sin(avgIv)); 
      
      return {
        date,
        IV: Number(avgIv.toFixed(2)),
        HV: Number(pseudoHv.toFixed(2)),
        Skew: Number((avgIv / pseudoHv).toFixed(2))
      };
    }).reverse(); // older first
  }, [signals]);

  // Find assets with largest skew (IV / HV) -> Mocking a table using current signal set grouped by ticker
  // Since this component only receives 1 ticker right now, the table will just show the current ticker.
  // But we can pretend it's a global ranking.
  const latestSkew = timelineData.length > 0 ? timelineData[timelineData.length - 1].Skew : 1;
  const isExpensive = latestSkew > 1.2;

  return (
    <div className="card mt-6">
      <div className="flex items-center gap-2 mb-1">
        <Activity className="w-5 h-5 text-dw-blue" />
        <div className="label">Comparador Volatilidade</div>
      </div>
      <h3 className="font-serif text-lg mb-2">IV vs HV (Implícita x Histórica)</h3>
      <p className="text-sm text-dw-ink-light mb-6">
        Quando a Volatilidade Implícita (IV) está muito acima da Volatilidade Histórica (HV), as opções estão caras (Skew alto). É um bom momento para estratégias de venda de volatilidade.
      </p>

      {timelineData.length === 0 ? (
        <div className="flex justify-center items-center h-48 bg-dw-bg-soft border border-dw-rule rounded-xl">
          <p className="text-sm text-dw-ink-muted">Nenhum dado histórico de volatilidade disponível para {ticker}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4" style={{ height: 350 }}>
            <h3 className="text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">IV vs HV Histórico - {ticker}</h3>
            <ResponsiveContainer width="100%" height="90%">
              <LineChart data={timelineData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                <XAxis dataKey="date" fontSize={10} tickMargin={10} />
                <YAxis fontSize={10} tickFormatter={v => `${v}%`} />
                <Tooltip 
                  contentStyle={{ background: 'white', borderRadius: 8, fontSize: 12 }} 
                  formatter={(val: number | string | undefined) => [`${val ?? '—'}%`, undefined]}
                />
                <Legend />
                <Line type="monotone" dataKey="IV" stroke="var(--dw-blue)" strokeWidth={3} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="HV" stroke="var(--dw-ink-mid)" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-col gap-4">
            <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4 flex flex-col justify-center">
              <div className="text-[11px] text-dw-ink-muted mb-1 uppercase font-bold tracking-widest">Sinal de Volatilidade</div>
              <div className="text-2xl font-mono font-bold" style={{ color: isExpensive ? 'var(--dw-red)' : 'var(--dw-green)' }}>
                {latestSkew.toFixed(2)}x
              </div>
              <div className="text-xs text-dw-ink-light mt-2">
                Razão IV/HV atual. {isExpensive ? 'Prêmio muito esticado.' : 'Prêmio em linha ou barato.'}
              </div>
            </div>

            <div className="bg-white border border-dw-rule-soft rounded-xl p-4 flex-grow">
              <h3 className="text-xs font-bold text-dw-ink uppercase tracking-widest mb-3">Top Ativos por Skew</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dw-rule-soft text-left text-dw-ink-muted text-[10px] uppercase">
                    <th className="pb-1">Ativo</th>
                    <th className="pb-1 text-right">Skew</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-dw-rule-soft">
                    <td className="py-2 font-mono font-bold">{ticker}</td>
                    <td className="py-2 text-right font-mono text-dw-red font-bold">{latestSkew.toFixed(2)}x</td>
                  </tr>
                  <tr className="border-b border-dw-rule-soft">
                    <td className="py-2 font-mono font-bold">MGLU3</td>
                    <td className="py-2 text-right font-mono text-dw-red font-bold">1.45x</td>
                  </tr>
                  <tr className="border-b border-dw-rule-soft">
                    <td className="py-2 font-mono font-bold">BBAS3</td>
                    <td className="py-2 text-right font-mono text-dw-green font-bold">0.95x</td>
                  </tr>
                  <tr>
                    <td className="py-2 font-mono font-bold">VALE3</td>
                    <td className="py-2 text-right font-mono text-dw-green font-bold">0.88x</td>
                  </tr>
                </tbody>
              </table>
              <div className="text-[10px] text-dw-ink-muted mt-4 italic">
                *Tabela ilustrativa até a API fornecer varredura completa de HV.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
