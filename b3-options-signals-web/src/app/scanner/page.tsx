'use client';

import React, { useState } from 'react';
import { fetchScan } from '@/lib/api';
import { Signal, ScanResponse } from '@/types/signals';
import SignalCard from '@/components/SignalCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AlertCircle, Search, Activity, ArrowRight } from 'lucide-react';

export default function ScannerPage() {
    const [ticker, setTicker] = useState('PETR4'); // Default suggestion
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<Signal[]>([]);
    const [error, setError] = useState('');
    const [searchedTicker, setSearchedTicker] = useState('');

    const handleScan = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!ticker) return;

        setLoading(true);
        setError('');
        setResults([]);
        setSearchedTicker('');

        try {
            const data: ScanResponse = await fetchScan(ticker);
            setResults(data.results || []); // Ensure array
            setSearchedTicker(ticker.toUpperCase());
            if (data.results.length === 0) {
                setError(`No signals found for ${ticker.toUpperCase()} with current strategies.`);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.message || err.message || 'Failed to scan ticker. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
            <div className="max-w-6xl mx-auto space-y-8">

                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-center gap-4 border-b border-slate-800 pb-6">
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                            Opportunity Scanner
                        </h1>
                        <p className="text-slate-400 mt-2">
                            Run vectorized strategies on real-time B3 options chains.
                        </p>
                    </div>
                    <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800" onClick={() => window.history.back()}>
                        Back to Dashboard
                    </Button>
                </div>

                {/* Search Box */}
                <Card className="bg-slate-900 border-slate-800 shadow-xl">
                    <CardHeader>
                        <CardTitle className="text-xl flex items-center gap-2 text-white">
                            <Search className="w-5 h-5 text-blue-400" />
                            Run New Scan
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleScan} className="flex flex-col sm:flex-row gap-4 items-end">
                            <div className="w-full sm:w-1/3 space-y-2">
                                <label className="text-sm font-medium text-slate-400">Ticker Symbol</label>
                                <Input
                                    value={ticker}
                                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                    placeholder="e.g. PETR4, VALE3"
                                    className="bg-slate-950 border-slate-700 text-white placeholder:text-slate-600 font-mono text-lg uppercase tracking-wider"
                                />
                            </div>
                            <Button
                                type="submit"
                                disabled={loading}
                                className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 h-11 w-full sm:w-auto transition-all"
                            >
                                {loading ? (
                                    <span className="flex items-center gap-2">
                                        <Activity className="w-4 h-4 animate-spin" /> Scanning...
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        Scan Now <ArrowRight className="w-4 h-4" />
                                    </span>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Status \u0026 Results */}

                {error && (
                    <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-lg flex items-center gap-3 text-red-300 animate-in fade-in slide-in-from-top-2">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <p>{error}</p>
                    </div>
                )}

                {!loading && searchedTicker && results.length > 0 && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                        <div className="flex items-center gap-2 text-green-400 bg-green-950/30 w-fit px-4 py-1.5 rounded-full border border-green-900/50">
                            <Activity className="w-4 h-4" />
                            <span className="text-sm font-semibold">{results.length} Opportunities Found for {searchedTicker}</span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {results.map((signal, idx) => (
                                <SignalCard key={idx} signal={signal} />
                            ))}
                        </div>
                    </div>
                )}

                {!loading && searchedTicker && results.length === 0 && !error && (
                    <div className="text-center py-12 text-slate-500">
                        <p>No signals found matching your active strategies.</p>
                    </div>
                )}

            </div>
        </div>
    );
}
