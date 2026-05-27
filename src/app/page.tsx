"use client"

import Link from "next/link"
import { Activity, BarChart2, ChevronRight, TrendingUp } from "lucide-react"
import LiveFeed from "@/components/LiveFeed"
import CollapseShell from "@/components/CollapseShell"
import MarketWidget from "@/components/MarketWidget"

export default function Dashboard() {
    return (
        <main className="main-content">
            {/* Page header */}
            <div className="page-header">
                <div>
                    <h1 className="font-serif">Advanced Options Analytics</h1>
                    <p className="mt-2 text-dw-ink-light text-base">
                        Scanner automatizado de volatilidade e oportunidades no mercado brasileiro de opções.
                    </p>
                </div>
            </div>

            {/* Editorial grid — 2fr | 1fr */}
            <div className="news-layout-container">

                {/* ── COLUNA PRINCIPAL ─────────────────────── */}
                <div className="flex flex-col gap-8">

                    {/* Live Scanner — card destaque */}
                    <div className="card" style={{ borderColor: "var(--dw-green)", borderWidth: "1.5px" }}>
                        <div className="label">Análise em tempo real</div>
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                                <h3 className="font-serif text-2xl mb-2">Live Scanner</h3>
                                <p className="text-sm text-dw-ink-light leading-relaxed mb-6">
                                    Varredura em tempo real por High IV, RSI Reversals e Gamma Squeezes no mercado B3.
                                    Identifica automaticamente as melhores oportunidades em opções de ações.
                                </p>
                                <Link
                                    href="/scanner"
                                    className="btn-demo inline-flex items-center gap-2"
                                    style={{ background: "var(--dw-green)" }}
                                >
                                    <TrendingUp className="w-4 h-4" />
                                    Abrir Scanner
                                    <ChevronRight className="w-4 h-4" />
                                </Link>
                            </div>
                            <div
                                className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0"
                                style={{ background: "var(--dw-green-soft)" }}
                            >
                                <TrendingUp className="w-7 h-7" style={{ color: "var(--dw-green)" }} />
                            </div>
                        </div>
                    </div>

                    {/* Live Feed — sinais recentes */}
                    <div>
                        <div
                            className="flex items-center justify-between mb-4 pb-2"
                            style={{ borderBottom: "2.5px solid var(--dw-ink)" }}
                        >
                            <span
                                className="text-xs font-extrabold uppercase"
                                style={{ color: "var(--dw-ink)", letterSpacing: "0.08em" }}
                            >
                                Sinais Recentes
                            </span>
                            <Link href="/signals" className="text-xs text-dw-blue hover:underline font-medium">
                                Ver todos →
                            </Link>
                        </div>
                        <LiveFeed />
                    </div>

                </div>

                {/* ── SIDEBAR ──────────────────────────────── */}
                <div className="flex flex-col gap-4">

                    <CollapseShell
                        icon={<BarChart2 size={18} />}
                        iconVariant="charts"
                        title="Backtesting"
                        pills={[
                            { label: "Black-Scholes", variant: "neu" },
                            { label: "Histórico", variant: "blue" },
                        ]}
                    >
                        <p className="text-sm text-dw-ink-light mb-4 leading-relaxed">
                            Simule estratégias com precificação histórica Black-Scholes e veja métricas de Sharpe, drawdown e win rate.
                        </p>
                        <Link href="/backtest" className="btn-secondary w-full justify-center text-sm">
                            Executar Simulação
                        </Link>
                    </CollapseShell>

<CollapseShell
                        icon={<Activity size={18} />}
                        iconVariant="green"
                        title="Greeks & Analytics"
                        pills={[
                            { label: "GEX", variant: "neu" },
                            { label: "Vol Smile", variant: "blue" },
                        ]}
                    >
                        <p className="text-sm text-dw-ink-light mb-4 leading-relaxed">
                            Gamma Exposure total (GEX) e análise do Volatility Smile para os principais ativos.
                        </p>
                        <Link href="/analytics" className="btn-secondary w-full justify-center text-sm">
                            Abrir Analytics
                        </Link>
                    </CollapseShell>

                    {/* Market Widget */}
                    <MarketWidget />
                </div>
            </div>
        </main>
    )
}
