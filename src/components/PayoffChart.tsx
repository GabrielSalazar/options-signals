"use client";

import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import api from '@/lib/api';

interface PayoffLeg {
    type: 'call' | 'put';
    strike: number;
    entry_price: number;
    side: 'buy' | 'sell';
    qty: number;
}

interface PayoffChartProps {
    spotPrice: number;
    legs: PayoffLeg[];
}

export default function PayoffChart({ spotPrice, legs }: PayoffChartProps) {
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        let isMounted = true;

        async function fetchCurve() {
            setLoading(true);
            try {
                const response = await api.post('/signals/payoff', {
                    spot_price: spotPrice,
                    legs: legs
                });

                if (isMounted) {
                    if (response.data.error) {
                        setError(response.data.error);
                    } else {
                        setData(response.data.curve || []);
                    }
                }
            } catch (err: any) {
                if (isMounted) setError("Erro ao carregar gráfico de payoff");
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        // Só busca se tiver legs válidas
        if (legs && legs.length > 0) {
            fetchCurve();
        } else {
            setData([]);
            setLoading(false);
        }

        return () => { isMounted = false; };
    }, [spotPrice, legs]);

    if (loading) return <div className="h-48 w-full animate-pulse bg-slate-800/50 rounded-lg flex items-center justify-center text-slate-500">Calculando Curva...</div>;
    if (error) return <div className="text-red-400 text-sm p-4">{error}</div>;
    if (data.length === 0) return null;

    // Acha max e min PnL para setar as cores
    const gradientOffset = () => {
        const dataMax = Math.max(...data.map(i => i.pnl));
        const dataMin = Math.min(...data.map(i => i.pnl));

        if (dataMax <= 0) return 0;
        if (dataMin >= 0) return 1;

        return dataMax / (dataMax - dataMin);
    };

    const off = gradientOffset();

    return (
        <div className="h-64 w-full mt-4">
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Curva de Payoff (Vencimento)</h4>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={data}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis
                        dataKey="spot_price"
                        stroke="#94a3b8"
                        fontSize={12}
                        tickFormatter={(val) => `R$${val}`}
                    />
                    <YAxis
                        stroke="#94a3b8"
                        fontSize={12}
                        tickFormatter={(val) => `R$${val}`}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                        itemStyle={{ color: '#e2e8f0' }}
                        formatter={(value: any) => [`R$ ${Number(value).toFixed(2)}`, 'PnL']}
                        labelFormatter={(label) => `Spot: R$ ${label}`}
                    />

                    <defs>
                        <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                            <stop offset={off} stopColor="#10b981" stopOpacity={0.8} />
                            <stop offset={off} stopColor="#ef4444" stopOpacity={0.8} />
                        </linearGradient>
                    </defs>

                    <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
                    <ReferenceLine x={spotPrice} stroke="#38bdf8" label={{ position: 'top', value: 'Atual', fill: '#38bdf8', fontSize: 10 }} />

                    <Area
                        type="monotone"
                        dataKey="pnl"
                        stroke="#10b981"
                        fill="url(#splitColor)"
                        isAnimationActive={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
