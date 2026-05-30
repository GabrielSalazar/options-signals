'use client';

import { useState } from 'react';
import { FlaskConical, BarChart2, TrendingUp, TrendingDown, Activity, Award } from 'lucide-react';
import { runBacktest, BacktestMetrics } from '@/lib/api';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function BacktestPage() {
  const [ticker, setTicker] = useState('PETR4');
  const [strategy, setStrategy] = useState('Covered Call');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<BacktestMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<number[]>([]);
  const [resultLabel, setResultLabel] = useState('');

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMetrics(null);
    setEquityCurve([]);
    try {
      const result = await runBacktest({ ticker, start_date: startDate, end_date: endDate });
      if (!result.metrics) {
        setError('Nenhum sinal encontrado para este ticker e período. Tente um intervalo maior ou outro ativo.');
        return;
      }
      setMetrics(result.metrics);
      setEquityCurve(result.equity_curve);
      setResultLabel(`${ticker} — ${strategy}`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      const msg = e?.response?.data?.detail || e?.message || 'Erro de conexão.';
      setError(`Falha: ${msg}. O backend pode estar dormindo (Render free tier — aguarde 30s e tente novamente).`);
    } finally {
      setLoading(false);
    }
  };

  const chartData = equityCurve.map((equity, i) => ({ trade: i, equity }));

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <div className="label mb-2">Simulação quantitativa</div>
          <h1 className="font-serif">Laboratório de Backtest</h1>
          <p className="mt-2 text-dw-ink-light text-base">
            Simule estratégias com dados históricos da B3 e valide sua expectância matemática.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Formulário */}
        <div className="card h-fit">
          <div className="label mb-4">Parâmetros da simulação</div>

          <form onSubmit={handleRun} className="flex flex-col gap-5">
            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>
                Ativo (Ticker B3)
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2"
                style={{
                  border: '1.5px solid var(--dw-rule)',
                  background: 'var(--dw-bg-soft)',
                  color: 'var(--dw-ink)',
                  '--tw-ring-color': 'var(--dw-blue)',
                } as React.CSSProperties}
                placeholder="Ex: PETR4"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>
                Estratégia
              </label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2"
                style={{
                  border: '1.5px solid var(--dw-rule)',
                  background: 'var(--dw-bg-soft)',
                  color: 'var(--dw-ink)',
                  '--tw-ring-color': 'var(--dw-blue)',
                } as React.CSSProperties}
              >
                <option>Covered Call</option>
                <option>Cash Secured Put</option>
                <option>Iron Condor</option>
                <option>Straddle Long</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>Data Início</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
                  style={{ border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)', color: 'var(--dw-ink)' }}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>Data Fim</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
                  style={{ border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)', color: 'var(--dw-ink)' }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-demo w-full flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
              style={{ background: 'var(--dw-blue)' }}
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <FlaskConical className="w-4 h-4" />
                  Executar Simulação
                </>
              )}
            </button>

            {loading && (
              <p className="text-center text-xs" style={{ color: 'var(--dw-ink-muted)' }}>
                Pode levar 30–90 s (download de dados históricos)
              </p>
            )}
          </form>
        </div>

        {/* Resultados */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {error && (
            <div className="rounded-xl px-4 py-3 text-sm"
              style={{ background: 'var(--dw-red)15', border: '1px solid var(--dw-red)40', color: 'var(--dw-red)' }}>
              {error}
            </div>
          )}

          {!metrics && !loading && !error && (
            <div
              className="min-h-[400px] rounded-2xl flex flex-col items-center justify-center p-8 text-center"
              style={{ border: '2px dashed var(--dw-rule)', background: 'var(--dw-bg-soft)' }}
            >
              <BarChart2 className="w-14 h-14 mb-4" style={{ color: 'var(--dw-rule)' }} />
              <h3 className="text-lg font-semibold" style={{ color: 'var(--dw-ink-mid)' }}>Nenhum dado simulado</h3>
              <p className="mt-2 text-sm" style={{ color: 'var(--dw-ink-muted)' }}>
                Ajuste os parâmetros ao lado e clique em Executar Simulação.
              </p>
            </div>
          )}

          {loading && (
            <div
              className="min-h-[400px] rounded-2xl flex flex-col items-center justify-center"
              style={{ border: '1px solid var(--dw-rule)', background: 'white' }}
            >
              <span className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin mb-4"
                style={{ borderColor: 'var(--dw-rule)', borderTopColor: 'var(--dw-blue)' }} />
              <p className="text-sm font-medium animate-pulse" style={{ color: 'var(--dw-blue)' }}>
                Calculando sinais históricos via Black-Scholes...
              </p>
            </div>
          )}

          {metrics && (
            <>
              {/* KPIs */}
              <div className="card">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <div className="label mb-1">Resumo de Performance</div>
                    <h3 className="font-serif text-xl">{resultLabel}</h3>
                  </div>
                  <span className="ct-pill blue">{metrics.trades} trades</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    {
                      label: 'Win Rate',
                      value: `${metrics.win_rate}%`,
                      icon: <Award className="w-4 h-4" />,
                      color: 'var(--dw-green)',
                    },
                    {
                      label: 'Retorno Total',
                      value: `${metrics.total_return >= 0 ? '+' : ''}${metrics.total_return}%`,
                      icon: <TrendingUp className="w-4 h-4" />,
                      color: metrics.total_return >= 0 ? 'var(--dw-green)' : 'var(--dw-red)',
                    },
                    {
                      label: 'Max Drawdown',
                      value: `${metrics.max_drawdown}%`,
                      icon: <TrendingDown className="w-4 h-4" />,
                      color: 'var(--dw-red)',
                    },
                    {
                      label: 'Sharpe Ratio',
                      value: String(metrics.sharpe_ratio),
                      icon: <Activity className="w-4 h-4" />,
                      color: 'var(--dw-blue)',
                    },
                    {
                      label: 'Sortino Ratio',
                      value: String(metrics.sortino_ratio ?? 0),
                      icon: <Activity className="w-4 h-4" />,
                      color: 'var(--dw-blue)',
                    },
                    {
                      label: 'Calmar Ratio',
                      value: String(metrics.calmar_ratio ?? 0),
                      icon: <Activity className="w-4 h-4" />,
                      color: 'var(--dw-blue)',
                    },
                    {
                      label: 'Expectância (R$)',
                      value: `R$${metrics.expectancy ?? 0}`,
                      icon: <Award className="w-4 h-4" />,
                      color: (metrics.expectancy ?? 0) >= 0 ? 'var(--dw-green)' : 'var(--dw-red)',
                    },
                  ].map(({ label, value, icon, color }) => (
                    <div key={label} className="rounded-xl p-4" style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
                      <div className="flex items-center gap-1.5 mb-2" style={{ color: 'var(--dw-ink-muted)' }}>
                        <span style={{ color }}>{icon}</span>
                        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
                      </div>
                      <p className="text-2xl font-bold font-mono" style={{ color }}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Equity Curve */}
              <div className="card">
                <div className="label mb-1">Evolução do Capital</div>
                <h3 className="font-serif text-lg mb-4">Equity Curve</h3>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                      <XAxis
                        dataKey="trade"
                        stroke="var(--dw-ink-muted)"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `T${v}`}
                      />
                      <YAxis
                        stroke="var(--dw-ink-muted)"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `R$${(v / 1000).toFixed(1)}k`}
                        domain={['auto', 'auto']}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'white',
                          border: '1px solid var(--dw-rule)',
                          borderRadius: 8,
                          fontSize: 12,
                          color: 'var(--dw-ink)',
                        }}
                        formatter={(v: number | undefined) => [`R$ ${(v ?? 0).toFixed(2)}`, 'Equity']}
                        labelFormatter={(l) => `Trade ${l}`}
                      />
                      <Area
                        type="monotone"
                        dataKey="equity"
                        stroke="var(--dw-blue)"
                        fill="var(--dw-blue)"
                        fillOpacity={0.15}
                        strokeWidth={2}
                        activeDot={{ r: 5 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
