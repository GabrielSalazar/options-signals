"use client"

import { useState } from "react"
import { ScanResponse, Signal } from "@/types/signals"
import { fetchScan } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Activity, Search, TrendingUp, AlertTriangle } from "lucide-react"

export default function Dashboard() {
    const [ticker, setTicker] = useState("PETR4")
    const [results, setResults] = useState<Signal[]>([])
    const [loading, setLoading] = useState(false)

    const handleScan = async () => {
        setLoading(true)
        try {
            const data: ScanResponse = await fetchScan(ticker)
            setResults(data.results)
        } catch (error) {
            console.error("Scan failed", error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
            {/* Header */}
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-10">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Activity className="h-6 w-6 text-emerald-400" />
                        <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                            B3 Option Signals
                        </h1>
                    </div>
                    <nav className="flex gap-4 text-sm text-slate-400">
                        <a href="#" className="hover:text-emerald-400">Dashboard</a>
                        <a href="#" className="hover:text-emerald-400">Estratégias</a>
                        <a href="#" className="hover:text-emerald-400">Alertas</a>
                    </nav>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-8">
                {/* Search Section */}
                <section className="mb-12 flex flex-col items-center justify-center space-y-4">
                    <h2 className="text-3xl font-light text-center">
                        Encontre oportunidades de <span className="font-semibold text-emerald-400">Opções</span> em segundos.
                    </h2>
                    <div className="flex w-full max-w-md items-center space-x-2">
                        <Input
                            type="text"
                            placeholder="Digite o ativo (ex: PETR4, VALE3)"
                            className="bg-slate-900 border-slate-700 text-white"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        />
                        <Button onClick={handleScan} disabled={loading} className="bg-emerald-600 hover:bg-emerald-500 text-white">
                            {loading ? "Escaneando..." : <><Search className="mr-2 h-4 w-4" /> Buscar</>}
                        </Button>
                    </div>
                </section>

                {/* Results Grid */}
                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {results.map((signal, index) => (
                        <Card key={index} className="bg-slate-900 border-slate-800 hover:border-emerald-500/50 transition-colors">
                            <CardHeader className="pb-2">
                                <div className="flex justify-between items-start">
                                    <Badge variant={signal.strategy.includes("High IV") ? "destructive" : "default"} className="mb-2">
                                        {signal.strategy}
                                    </Badge>
                                    <span className="text-xs text-slate-500 font-mono">{signal.ticker}</span>
                                </div>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    {signal.option_symbol}
                                    <span className="text-sm font-normal text-slate-400">(Strike: R$ {signal.strike.toFixed(2)})</span>
                                </CardTitle>
                                <CardDescription className="text-slate-400 pt-1">
                                    {signal.reason}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div className="flex justify-between text-sm py-2 border-b border-slate-800">
                                        <span className="text-slate-400">Spot Price</span>
                                        <span className="font-medium text-white">R$ {signal.spot_price.toFixed(2)}</span>
                                    </div>

                                    {signal.greeks && (
                                        <div className="grid grid-cols-2 gap-2 text-xs">
                                            <div className="bg-slate-950 p-2 rounded">
                                                <span className="block text-slate-500">Delta</span>
                                                <span className="font-mono text-emerald-400">{signal.greeks.delta.toFixed(3)}</span>
                                            </div>
                                            <div className="bg-slate-950 p-2 rounded">
                                                <span className="block text-slate-500">Gamma</span>
                                                <span className="font-mono text-cyan-400">{signal.greeks.gamma.toFixed(3)}</span>
                                            </div>
                                            <div className="bg-slate-950 p-2 rounded">
                                                <span className="block text-slate-500">Theta</span>
                                                <span className="font-mono text-amber-400">{signal.greeks.theta.toFixed(3)}</span>
                                            </div>
                                            <div className="bg-slate-950 p-2 rounded">
                                                <span className="block text-slate-500">Vega</span>
                                                <span className="font-mono text-purple-400">{signal.greeks.vega.toFixed(3)}</span>
                                            </div>
                                        </div>
                                    )}

                                    <div className="pt-2">
                                        <Button variant="outline" className="w-full border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300">
                                            <TrendingUp className="mr-2 h-4 w-4" /> Analisar Gráfico
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}

                    {results.length === 0 && !loading && (
                        <div className="col-span-full text-center py-20 text-slate-600">
                            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                            <p>Nenhum sinal encontrado ainda. Tente buscar por um ativo.</p>
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
