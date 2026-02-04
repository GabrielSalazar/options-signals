"use client"

import Link from "next/link"
import { Activity, BarChart2, BookOpen, ChevronRight, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function Dashboard() {
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
                        <span className="text-emerald-400">Dashboard</span>
                        <Link href="/strategies" className="hover:text-emerald-400 transition-colors">Strategies</Link>
                        <Link href="/scanner" className="hover:text-emerald-400 transition-colors">Scanner</Link>
                        <Link href="/alerts" className="hover:text-emerald-400 transition-colors">History</Link>
                    </nav>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-12">
                <div className="text-center mb-16 space-y-4">
                    <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                        Advanced Options Analytics
                    </h1>
                    <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                        Automated volatility scanning and backtesting for the Brazilian Market.
                    </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Tool 1: Scanner */}
                    <Card className="bg-slate-900 border-slate-800 hover:border-emerald-500/50 transition-all hover:shadow-[0_0_20px_rgba(16,185,129,0.1)] group">
                        <CardHeader>
                            <TrendingUp className="w-10 h-10 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
                            <CardTitle className="text-white">Live Scanner</CardTitle>
                            <CardDescription className="text-slate-400">
                                Real-time scan for High IV, RSI Reversions, and Gamma Squeezes.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Link href="/scanner">
                                <Button className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium group-hover:pl-4 transition-all">
                                    Open Scanner <ChevronRight className="ml-2 w-4 h-4" />
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>

                    {/* Tool 2: Backtest */}
                    <Card className="bg-slate-900 border-slate-800 hover:border-cyan-500/50 transition-all hover:shadow-[0_0_20px_rgba(6,182,212,0.1)] group">
                        <CardHeader>
                            <BarChart2 className="w-10 h-10 text-cyan-400 mb-2 group-hover:scale-110 transition-transform" />
                            <CardTitle className="text-white">Backtesting</CardTitle>
                            <CardDescription className="text-slate-400">
                                Simulate strategies with historical Black-Scholes pricing.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Link href="/backtest">
                                <Button className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium group-hover:pl-4 transition-all">
                                    Run Simulation <ChevronRight className="ml-2 w-4 h-4" />
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>

                    {/* Tool 3: Strategies */}
                    <Card className="bg-slate-900 border-slate-800 hover:border-purple-500/50 transition-all hover:shadow-[0_0_20px_rgba(168,85,247,0.1)] group">
                        <CardHeader>
                            <BookOpen className="w-10 h-10 text-purple-400 mb-2 group-hover:scale-110 transition-transform" />
                            <CardTitle className="text-white">Strategy Library</CardTitle>
                            <CardDescription className="text-slate-400">
                                Browse available algorithms and their risk profiles.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Link href="/strategies">
                                <Button variant="outline" className="w-full border-slate-700 text-slate-300 hover:bg-slate-800 group-hover:text-purple-400">
                                    View Library
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>

                    {/* Tool 4: History/Alerts */}
                    <Card className="bg-slate-900 border-slate-800 hover:border-amber-500/50 transition-all hover:shadow-[0_0_20px_rgba(245,158,11,0.1)] group">
                        <CardHeader>
                            <Activity className="w-10 h-10 text-amber-400 mb-2 group-hover:scale-110 transition-transform" />
                            <CardTitle className="text-white">Signal History</CardTitle>
                            <CardDescription className="text-slate-400">
                                Log of all past generated alerts and opportunities.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Link href="/alerts">
                                <Button variant="outline" className="w-full border-slate-700 text-slate-300 hover:bg-slate-800 group-hover:text-amber-400">
                                    View History
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    )
}
