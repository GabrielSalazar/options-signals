"use client"

import React, { useState, useEffect } from 'react';
import { fetchBacktestStrategies, runBacktest, BacktestParams } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Activity, Play, ArrowLeft } from 'lucide-react';
import BacktestMetrics from '@/components/BacktestMetrics';
import EquityChart from '@/components/EquityChart';
import Link from 'next/link';

export default function BacktestPage() {
    // State
    const [strategies, setStrategies] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState('');

    // Form Params
    const [ticker, setTicker] = useState('PETR4');
    const [selectedStrategy, setSelectedStrategy] = useState('');
    const [days, setDays] = useState([252]); // Array for Slider
    const [capital, setCapital] = useState(10000);

    // Initial Load
    useEffect(() => {
        async function loadStrategies() {
            try {
                const list = await fetchBacktestStrategies();
                setStrategies(list);
                if (list.length > 0) setSelectedStrategy(list[0]);
            } catch (err) {
                console.error("Failed to load strategies", err);
            }
        }
        loadStrategies();
    }, []);

    const handleRun = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setResult(null);

        try {
            const params: BacktestParams = {
                ticker: ticker.toUpperCase(),
                strategy_name: selectedStrategy,
                days: days[0],
                initial_capital: Number(capital)
            };

            const data = await runBacktest(params);
            setResult(data.metrics);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || 'Simulation failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
            <div className="max-w-6xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="p-2 hover:bg-slate-900 rounded-full transition-colors">
                            <ArrowLeft className="w-6 h-6 text-slate-400" />
                        </Link>
                        <div>
                            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                                Backtest Engine
                            </h1>
                            <p className="text-slate-400 mt-1">
                                Simulate option strategies with historical Black-Scholes pricing.
                            </p>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                    {/* Sidebar Configuration */}
                    <Card className="bg-slate-900 border-slate-800 lg:col-span-1 h-fit">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <Activity className="w-5 h-5 text-cyan-400" /> Configuration
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleRun} className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-400">Ticker</label>
                                    <Input
                                        value={ticker}
                                        onChange={(e) => setTicker(e.target.value)}
                                        className="bg-slate-950 border-slate-700 font-mono uppercase"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-400">Strategy</label>
                                    <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                                        <SelectTrigger className="bg-slate-950 border-slate-700">
                                            <SelectValue placeholder="Select Strategy" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
                                            {strategies.map((s) => (
                                                <SelectItem key={s} value={s}>{s}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex justify-between">
                                        <label className="text-sm font-medium text-slate-400">Period (Days)</label>
                                        <span className="text-sm font-mono text-cyan-400">{days[0]}d</span>
                                    </div>
                                    <Slider
                                        value={days}
                                        onValueChange={setDays}
                                        max={500}
                                        min={30}
                                        step={10}
                                        className="py-2"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-400">Initial Capital (R$)</label>
                                    <Input
                                        type="number"
                                        value={capital}
                                        onChange={(e) => setCapital(Number(e.target.value))}
                                        className="bg-slate-950 border-slate-700 font-mono"
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold h-12"
                                >
                                    {loading ? "Simulating..." : (
                                        <span className="flex items-center gap-2">
                                            <Play className="w-4 h-4 fill-current" /> Run Simulation
                                        </span>
                                    )}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Results Area */}
                    <div className="lg:col-span-3 space-y-6">
                        {error && (
                            <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-300">
                                Error: {error}
                            </div>
                        )}

                        {!result && !loading && !error && (
                            <div className="h-full flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-lg text-slate-600">
                                <Activity className="w-12 h-12 mb-4 opacity-20" />
                                <p className="text-lg">Select parameters and click Run Simulation</p>
                            </div>
                        )}

                        {result && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                                <BacktestMetrics metrics={result} />

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {result.equity_curve && (
                                        <EquityChart data={result.equity_curve} />
                                    )}
                                </div>

                                {/* Trades Log */}
                                <Card className="bg-slate-900 border-slate-800">
                                    <CardHeader>
                                        <CardTitle className="text-white">Recent Trades</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm text-left text-slate-400">
                                                <thead className="text-xs text-slate-500 uppercase bg-slate-950/50">
                                                    <tr>
                                                        <th className="px-4 py-3">Date</th>
                                                        <th className="px-4 py-3">Signal</th>
                                                        <th className="px-4 py-3">Type</th>
                                                        <th className="px-4 py-3">Strike</th>
                                                        <th className="px-4 py-3">Price</th>
                                                        <th className="px-4 py-3 text-right">PnL</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {result.trades_log && result.trades_log.map((trade: any, i: number) => (
                                                        <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/50">
                                                            <td className="px-4 py-3 font-mono">{new Date(trade.entry_date).toLocaleDateString()}</td>
                                                            <td className={`px-4 py-3 font-bold ${trade.signal_type === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                                                                {trade.signal_type}
                                                            </td>
                                                            <td className="px-4 py-3">{trade.option_type}</td>
                                                            <td className="px-4 py-3">{trade.strike}</td>
                                                            <td className="px-4 py-3">R$ {trade.entry_price.toFixed(2)}</td>
                                                            <td className={`px-4 py-3 text-right font-mono ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {trade.pnl ? `R$ ${trade.pnl.toFixed(2)}` : '-'}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    )
}
