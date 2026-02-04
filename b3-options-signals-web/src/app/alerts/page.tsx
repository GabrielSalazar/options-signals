"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ArrowLeft, History, RefreshCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchSignalHistory } from "@/lib/api"
import { Signal } from "@/types/signals"
import { Badge } from "@/components/ui/badge"

export default function AlertsPage() {
    const [signals, setSignals] = useState<Signal[]>([])
    const [loading, setLoading] = useState(true)

    const loadHistory = async () => {
        setLoading(true)
        try {
            const data = await fetchSignalHistory(100)
            setSignals(data)
        } catch (error) {
            console.error("Failed to fetch history", error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadHistory()
    }, [])

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
            {/* Header */}
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-10">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                            <ArrowLeft className="h-5 w-5 text-emerald-400" />
                            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                                Dashboard
                            </h1>
                        </Link>
                    </div>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-8">
                <div className="max-w-6xl mx-auto space-y-6">
                    <div className="flex items-center justify-between">
                        <h1 className="text-3xl font-bold flex items-center gap-2">
                            <History className="h-8 w-8 text-cyan-400" /> Signal History
                        </h1>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={loadHistory}
                            disabled={loading}
                            className="border-slate-700 hover:bg-slate-800"
                        >
                            <RefreshCcw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </Button>
                    </div>

                    <Card className="bg-slate-900 border-slate-800">
                        <CardHeader>
                            <CardTitle className="text-slate-300">Latest Alerts</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left text-slate-400">
                                    <thead className="text-xs text-slate-500 uppercase bg-slate-950/50">
                                        <tr>
                                            <th className="px-4 py-3">Time</th>
                                            <th className="px-4 py-3">Ticker</th>
                                            <th className="px-4 py-3">Strategy</th>
                                            <th className="px-4 py-3">Type</th>
                                            <th className="px-4 py-3">Price</th>
                                            <th className="px-4 py-3">Risk</th>
                                            <th className="px-4 py-3">Recommendation</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {signals.map((signal, i) => (
                                            <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/50">
                                                <td className="px-4 py-3 whitespace-nowrap font-mono text-xs">
                                                    {new Date(signal.timestamp).toLocaleString()}
                                                </td>
                                                <td className="px-4 py-3 font-bold text-white">
                                                    {signal.ticker}
                                                </td>
                                                <td className="px-4 py-3 text-slate-300">
                                                    {signal.strategy}
                                                </td>
                                                <td className={`px-4 py-3 font-semibold ${signal.signal_type.includes('BUY') ? 'text-green-400' :
                                                        signal.signal_type.includes('SELL') ? 'text-red-400' : 'text-blue-400'
                                                    }`}>
                                                    {signal.signal_type}
                                                </td>
                                                <td className="px-4 py-3 font-mono">
                                                    R$ {signal.spot_price.toFixed(2)}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Badge variant="outline" className={`
                                                        ${signal.risk_level === 'Alto' ? 'border-red-500/50 text-red-500' :
                                                            signal.risk_level === 'Médio' ? 'border-yellow-500/50 text-yellow-500' :
                                                                'border-green-500/50 text-green-500'}
                                                    `}>
                                                        {signal.risk_level}
                                                    </Badge>
                                                </td>
                                                <td className="px-4 py-3 text-xs text-slate-500 max-w-[200px] truncate" title={signal.recommendation}>
                                                    {signal.recommendation}
                                                </td>
                                            </tr>
                                        ))}
                                        {!loading && signals.length === 0 && (
                                            <tr>
                                                <td colSpan={7} className="text-center py-8 text-slate-600">
                                                    No history found. Run a scan to generate signals.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    )
}
