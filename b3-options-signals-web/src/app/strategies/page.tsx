"use client"

import { useEffect, useState } from "react"
import { fetchStrategies } from "@/lib/api"
import { Activity, Shield, TrendingUp, Zap } from "lucide-react"

interface Strategy {
    name: string
    description: string
    risk_level: string
}

export default function StrategiesPage() {
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function load() {
            try {
                const data = await fetchStrategies()
                // Adjust based on the actual API response structure { active_strategies: [...] }
                setStrategies(data.active_strategies)
            } catch (e) {
                console.error(e)
            } finally {
                setLoading(false)
            }
        }
        load()
    }, [])

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
                        <a href="/" className="hover:text-emerald-400">Dashboard</a>
                        <a href="/strategies" className="text-emerald-400 font-semibold">Estratégias</a>
                        <a href="#" className="hover:text-emerald-400">Alertas</a>
                    </nav>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-8">
                <div className="mb-8">
                    <h2 className="text-3xl font-light">
                        Estratégias <span className="font-semibold text-cyan-400">Ativas</span>
                    </h2>
                    <p className="text-slate-400 mt-2">
                        Conheça os algoritmos que monitoram o mercado em tempo real.
                    </p>
                </div>

                {loading ? (
                    <div className="text-center py-20 text-slate-600">Carregando estratégias...</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {strategies.map((strategy, idx) => (
                            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-cyan-500/50 transition-all group">
                                <div className="flex justify-between items-start mb-4">
                                    <div className={`p-2 rounded-lg ${strategy.risk_level === 'High' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
                                        {strategy.risk_level === 'High' ? <Zap className="h-6 w-6" /> : <Shield className="h-6 w-6" />}
                                    </div>
                                    <span className={`text-xs font-bold px-2 py-1 rounded border ${strategy.risk_level === 'High' ? 'border-red-900 bg-red-950 text-red-400' : 'border-blue-900 bg-blue-950 text-blue-400'}`}>
                                        {strategy.risk_level.toUpperCase()} RISK
                                    </span>
                                </div>

                                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-400 transition-colors">
                                    {strategy.name}
                                </h3>

                                <p className="text-slate-400 text-sm leading-relaxed">
                                    {strategy.description}
                                </p>

                                <div className="mt-6 pt-4 border-t border-slate-800 text-center">
                                    <button className="text-sm text-emerald-400 hover:text-emerald-300 font-medium inline-flex items-center">
                                        <TrendingUp className="h-4 w-4 mr-1" />
                                        Ver Sinais Recentes
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    )
}
