'use client';

import { useState, useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import {
  StrategyId, STRATEGY_DEFS, instantiateLegs, calculatePayoffCurve,
} from '@/lib/strategies';

interface Props {
  id: StrategyId;
  s0: number;
  strikes: number[];
}

const GREEN = '#1D9E75';
const RED = '#E24B4A';

/**
 * Mini-gráfico de payoff no vencimento para os exemplos do Guia de Estratégias.
 * Recolhido por padrão; aparece via toggle "Gráfico".
 * O traço fica vermelho onde P&L < 0 e verde onde ≥ 0 (gradiente vertical cortado no zero).
 */
export function StrategyExampleChart({ id, s0, strikes }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mb-4 -mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 text-[11px] font-bold text-dw-blue border border-dw-blue/30 rounded-md px-2 py-1 hover:bg-blue-50 transition-colors"
      >
        <BarChart3 className="w-3 h-3" />
        {open ? 'Ocultar gráfico' : 'Gráfico'}
      </button>
      {open && (
        <div className="mt-2 bg-dw-bg-soft border border-dw-rule-soft rounded-lg p-3">
          <MiniPayoff id={id} s0={s0} strikes={strikes} />
        </div>
      )}
    </div>
  );
}

function MiniPayoff({ id, s0, strikes }: Props) {
  const def = STRATEGY_DEFS[id];

  const { data, off, domain } = useMemo(() => {
    const legs = instantiateLegs(def, strikes);
    const curve = calculatePayoffCurve(legs, s0, 30 / 365, 0.3, 0.1475, 0, 0.4, 80, def.stockUnits);
    const ys = curve.map((p) => p.payoffExpiration);
    const yMax = Math.max(...ys);
    const yMin = Math.min(...ys);
    const pad = (yMax - yMin) * 0.08 || 1;
    const top = yMax + pad;
    const bot = yMin - pad;
    // fração (do topo) onde está a linha do zero — divide verde (acima) de vermelho (abaixo)
    const offset = top <= 0 ? 0 : bot >= 0 ? 1 : top / (top - bot);
    return { data: curve, off: offset, domain: [bot, top] as [number, number] };
  }, [def, s0, strikes]);

  const gid = `grad-${id}-${s0}-${strikes.join('_')}`;

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-1.5 text-[11px] text-dw-ink-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: GREEN }} />
          P&amp;L no vencimento (R$/ação)
        </span>
        <span>Strikes: {strikes.map((k) => k.toFixed(2).replace('.', ',')).join(' / ')}</span>
      </div>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={data} margin={{ top: 22, right: 10, bottom: 2, left: -10 }}>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset={0} stopColor={GREEN} />
              <stop offset={off} stopColor={GREEN} />
              <stop offset={off} stopColor={RED} />
              <stop offset={1} stopColor={RED} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.5} />
          <XAxis
            dataKey="S" type="number" domain={['dataMin', 'dataMax']}
            stroke="var(--dw-ink-muted)" fontSize={10} tickLine={false} axisLine={false}
            tickFormatter={(v) => `R$${Number(v).toFixed(0)}`}
          />
          <YAxis
            domain={domain}
            stroke="var(--dw-ink-muted)" fontSize={10} tickLine={false} axisLine={false} width={46}
            tickFormatter={(v) => `${v < 0 ? '-' : '+'}R$${Math.abs(Number(v)).toFixed(1)}`}
          />
          <Tooltip
            contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 11 }}
            formatter={(v: number | string | undefined) => [
              typeof v === 'number' ? `R$ ${v.toFixed(2)}/ação` : (v ?? '—'), 'P&L',
            ]}
            labelFormatter={(l) => `Preço: R$ ${Number(l).toFixed(2)}`}
          />
          <ReferenceLine y={0} stroke="var(--dw-ink-muted)" strokeDasharray="3 3" />
          <ReferenceLine
            x={s0} stroke="var(--dw-blue)" strokeDasharray="3 3"
            label={{ position: 'top', value: 'Atual', fill: 'var(--dw-blue)', fontSize: 9 }}
          />
          <Line
            type="linear" dataKey="payoffExpiration"
            stroke={`url(#${gid})`} strokeWidth={2.5} dot={false} isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}
