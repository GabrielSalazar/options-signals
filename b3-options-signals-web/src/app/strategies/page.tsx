"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, BookOpen, TrendingUp, AlertTriangle, Activity, Star, Info } from "lucide-react"
import Link from "next/link"

type StrategyData = {
    rank: number
    name: string
    ptName: string
    popularity: number // 1-5
    risk: "Baixo" | "Baixo-Médio" | "Médio" | "Alto" | "Muito Alto"
    complexity: "Baixa" | "Média" | "Alta"
    legs: string
    winRate: string
    bestWhen: string
    entry: string[]
    exit: string[]
}

const STRATEGIES: StrategyData[] = [
    {
        rank: 1,
        name: "Covered Call",
        ptName: "Lançamento Coberto",
        popularity: 5,
        risk: "Baixo",
        complexity: "Baixa",
        legs: "2 (Long Stock + Short Call)",
        winRate: "70-82%",
        bestWhen: "Renda extra (neutro/leve alta)",
        entry: ["Tenha 100 ações em carteira.", "Venda 1 Call OTM (fora do dinheiro)."],
        exit: ["Se subir muito: Entregue as ações (lucro máx).", "Se cair/lateralizar: Fique com o prêmio e repita."]
    },
    {
        rank: 2,
        name: "Cash Secured Put",
        ptName: "Venda de Put Coberta por Caixa",
        popularity: 5,
        risk: "Baixo-Médio",
        complexity: "Baixa",
        legs: "1 (Short Put)",
        winRate: "80-88%",
        bestWhen: "Comprar ativo mais barato",
        entry: ["Tenha dinheiro em caixa para comprar o ativo.", "Venda 1 Put OTM no preço que deseja pagar."],
        exit: ["Se cair abaixo do strike: Exerça a compra do ativo.", "Se subir: Fique com o prêmio (lucro)."]
    },
    {
        rank: 3,
        name: "Protective Put",
        ptName: "Put de Proteção (Seguro)",
        popularity: 5,
        risk: "Baixo",
        complexity: "Baixa",
        legs: "2 (Long Stock + Long Put)",
        winRate: "75-85%",
        bestWhen: "Proteger carteira de quedas",
        entry: ["Tenha o ativo em carteira.", "Compre 1 Put OTM ou ATM."],
        exit: ["Queda forte: Put valoriza e compensa perda da ação.", "Alta: Put vira pó, ação valoriza."]
    },
    {
        rank: 4,
        name: "Iron Condor",
        ptName: "Condor de Ferro",
        popularity: 4,
        risk: "Baixo",
        complexity: "Média",
        legs: "4 (Bull Put + Bear Call Spreads)",
        winRate: "80-90%",
        bestWhen: "Mercado lateral / Baixa volatilidade",
        entry: ["Venda Put OTM + Compre Put OTM (mais abaixo).", "Venda Call OTM + Compre Call OTM (mais acima)."],
        exit: ["Lucro: O mercado fica no miolo e tudo vira pó.", "Prejuízo: Se explodir para qualquer lado (stop loss)."]
    },
    {
        rank: 5,
        name: "Bull Put Spread",
        ptName: "Trava de Alta com Put",
        popularity: 4,
        risk: "Baixo-Médio",
        complexity: "Média",
        legs: "2",
        winRate: "75-80%",
        bestWhen: "Alta moderada / Lateral",
        entry: ["Venda Put OTM (Strike Y).", "Compre Put OTM (Strike X < Y) para proteção."],
        exit: ["Lucro: Preço fica acima do Strike Y.", "Prejuízo: Preço cai abaixo de X."]
    },
    {
        rank: 6,
        name: "Bear Call Spread",
        ptName: "Trava de Baixa com Call",
        popularity: 4,
        risk: "Baixo-Médio",
        complexity: "Média",
        legs: "2",
        winRate: "75-82%",
        bestWhen: "Baixa moderada / Lateral",
        entry: ["Venda Call OTM (Strike A).", "Compre Call OTM (Strike B > A) para proteção."],
        exit: ["Lucro: Preço fica abaixo do Strike A.", "Prejuízo: Preço sobe acima de B."]
    },
    {
        rank: 7,
        name: "Long Call",
        ptName: "Compra a Seco de Call",
        popularity: 4,
        risk: "Médio", // Perda 100% do prêmio
        complexity: "Baixa",
        legs: "1",
        winRate: "40-50%",
        bestWhen: "Alta forte e rápida",
        entry: ["Compre Call ATM ou levemente OTM."],
        exit: ["Lucro: Ativo explode (Gamma a favor).", "Prejuízo: Ativo lateraliza (Theta contra) ou cai."]
    },
    {
        rank: 8,
        name: "Long Put",
        ptName: "Compra a Seco de Put",
        popularity: 4,
        risk: "Médio",
        complexity: "Baixa",
        legs: "1",
        winRate: "40-50%",
        bestWhen: "Queda forte e rápida",
        entry: ["Compre Put ATM ou levemente OTM."],
        exit: ["Lucro: Ativo derrete (Gamma a favor).", "Prejuízo: Ativo lateraliza ou sobe."]
    },
    {
        rank: 9,
        name: "Collar",
        ptName: "Collar (Proteção financiada)",
        popularity: 3,
        risk: "Baixo",
        complexity: "Média",
        legs: "3 (Long Stock + Long Put + Short Call)",
        winRate: "80-84%",
        bestWhen: "Proteção custo zero",
        entry: ["Tenha ação.", "Compre Put OTM (Seguro).", "Venda Call OTM (Financia o seguro)."],
        exit: ["Alta: Ganha até o strike da Call.", "Queda: Perda limitada ao strike da Put."]
    },
    {
        rank: 10,
        name: "Bull Call Spread",
        ptName: "Trava de Alta com Call",
        popularity: 3,
        risk: "Médio",
        complexity: "Média",
        legs: "2",
        winRate: "70-78%",
        bestWhen: "Alta moderada",
        entry: ["Compre Call ATM.", "Venda Call OTM (reduz custo)."],
        exit: ["Lucro Max: Ação acima da Call vendida.", "Prejuízo Max: Custo da entrada."]
    },
    {
        rank: 11,
        name: "Bear Put Spread",
        ptName: "Trava de Baixa com Put",
        popularity: 3,
        risk: "Médio",
        complexity: "Média",
        legs: "2",
        winRate: "70-80%",
        bestWhen: "Baixa moderada",
        entry: ["Compre Put ATM.", "Venda Put OTM (reduz custo)."],
        exit: ["Lucro Max: Ação abaixo da Put vendida.", "Prejuízo Max: Custo da entrada."]
    },
    {
        rank: 12,
        name: "Straddle",
        ptName: "Compra de Volatilidade (Straddle)",
        popularity: 3,
        risk: "Alto",
        complexity: "Média",
        legs: "2",
        winRate: "35-45%",
        bestWhen: "Alta Volatilidade (Explosão)",
        entry: ["Compre Call ATM.", "Compre Put ATM."],
        exit: ["Lucro: Movimento forte para qualquer lado.", "Prejuízo: Lateralidade (Theta alto)."]
    },
    {
        rank: 13,
        name: "Strangle",
        ptName: "Compra de Volatilidade (Strangle)",
        popularity: 3,
        risk: "Alto",
        complexity: "Média",
        legs: "2",
        winRate: "35-45%",
        bestWhen: "Volatilidade (Custo menor que Straddle)",
        entry: ["Compre Call OTM.", "Compre Put OTM."],
        exit: ["Lucro: Movimento muito forte.", "Prejuízo: Lateralidade."]
    },
    {
        rank: 14,
        name: "Butterfly Spread",
        ptName: "Borboleta",
        popularity: 2,
        risk: "Baixo",
        complexity: "Alta",
        legs: "3-4",
        winRate: "75-85%",
        bestWhen: "Alvo preciso (Lateral no strike)",
        entry: ["1 Trava de Alta + 1 Trava de Baixa (Corpo no miolo)."],
        exit: ["Lucro Max: No vencimento, preço exato no miolo.", "Prejuízo: Limitado ao custo."]
    },
    {
        rank: 15,
        name: "Iron Butterfly",
        ptName: "Borboleta de Ferro",
        popularity: 2,
        risk: "Baixo",
        complexity: "Alta",
        legs: "4",
        winRate: "80-88%",
        bestWhen: "Lateral Strike Único",
        entry: ["Venda Straddle ATM + Compre Straddle OTM (Asas de proteção)."],
        exit: ["Lucro: Fica no miolo.", "Prejuízo: Sai das asas."]
    },
    {
        rank: 16,
        name: "Calendar Spread",
        ptName: "Trava de Calendário",
        popularity: 2,
        risk: "Médio",
        complexity: "Alta",
        legs: "2",
        winRate: "70-79%",
        bestWhen: "Exploração de Theta/Vega diferenciado",
        entry: ["Venda Opção Curta.", "Compre Opção Longa (mesmo strike)."],
        exit: ["Lucro: Curta vira pó mais rápido que a Longa desvaloriza."]
    },
    {
        rank: 17,
        name: "Diagonal Spread",
        ptName: "Trava Diagonal",
        popularity: 2,
        risk: "Médio",
        complexity: "Alta",
        legs: "2",
        winRate: "75-83%",
        bestWhen: "Direcional + Tempo",
        entry: ["Venda Opção Curta OTM.", "Compre Opção Longa ATM/ITM."],
        exit: ["Lucro: Gestão ativa das rolagens."]
    },
    {
        rank: 18,
        name: "Covered Combo",
        ptName: "Combo Coberto",
        popularity: 1,
        risk: "Médio",
        complexity: "Média",
        legs: "3",
        winRate: "70-78%",
        bestWhen: "Renda turbinada",
        entry: ["Covered Call + Venda de Put OTM."],
        exit: ["Assumir dobro do ativo se cair muito."]
    },
    {
        rank: 19,
        name: "Jade Lizard",
        ptName: "Jade Lizard",
        popularity: 1,
        risk: "Médio",
        complexity: "Alta",
        legs: "3",
        winRate: "80-85%",
        bestWhen: "Neutro/Alta (Sem risco na alta)",
        entry: ["Venda Put OTM + Bear Call Spread."],
        exit: ["Crédito total se lateralizar."]
    },
    {
        rank: 20,
        name: "Broken Wing Butterfly",
        ptName: "Borboleta de Asa Quebrada",
        popularity: 1,
        risk: "Baixo",
        complexity: "Alta",
        legs: "4",
        winRate: "82-87%",
        bestWhen: "Direcional Barata / Grátis",
        entry: ["Borboleta com uma asa mais longe para financiar o custo."],
        exit: ["Lucro se não ultrapassar a asa quebrada."]
    }
]

export default function StrategiesPage() {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
            {/* Header */}
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-10 w-full">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                            <ArrowLeft className="h-5 w-5 text-emerald-400" />
                            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                                Voltar ao Dashboard
                            </h1>
                        </Link>
                    </div>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto space-y-8">
                    <div className="text-center space-y-4">
                        <h2 className="text-4xl font-light">
                            Top 20 <span className="font-semibold text-emerald-400">Estratégias de Opções</span>
                        </h2>
                        <p className="text-slate-400 max-w-2xl mx-auto">
                            Guia definitivo classificado por popularidade, risco e complexidade.
                            Baseado em dados globais de B3 e CME Group.
                        </p>
                    </div>

                    <div className="grid gap-6">
                        {STRATEGIES.map((strategy) => (
                            <Card key={strategy.rank} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
                                <CardHeader>
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <Badge variant="secondary" className="bg-slate-800 text-slate-300">#{strategy.rank}</Badge>
                                                <CardTitle className="text-xl text-emerald-100">
                                                    {strategy.name}
                                                </CardTitle>
                                            </div>
                                            <CardDescription className="text-slate-400 mt-1 font-medium">
                                                {strategy.ptName}
                                            </CardDescription>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <Badge variant={strategy.risk === "Alto" || strategy.risk === "Muito Alto" ? "destructive" : strategy.risk === "Médio" ? "outline" : "default"}
                                                className={strategy.risk === "Baixo" || strategy.risk === "Baixo-Médio" ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20" : ""}>
                                                Risco: {strategy.risk}
                                            </Badge>
                                            <Badge variant="secondary" className="bg-slate-800 text-amber-200">
                                                Complexidade: {strategy.complexity}
                                            </Badge>
                                            <div className="flex items-center gap-1 text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-full text-xs font-bold border border-yellow-500/20">
                                                <Star className="h-3 w-3 fill-current" />
                                                Rate: {strategy.winRate}
                                            </div>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-6 border-t border-slate-800 pt-6">
                                    <div className="grid md:grid-cols-2 gap-6">

                                        {/* Info Block */}
                                        <div className="col-span-2 md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4 mb-2">
                                            <div className="bg-slate-950/30 p-3 rounded border border-slate-800/50">
                                                <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">Pernas (Legs)</span>
                                                <p className="text-sm text-slate-300">{strategy.legs}</p>
                                            </div>
                                            <div className="bg-slate-950/30 p-3 rounded border border-slate-800/50">
                                                <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">Melhor Quando</span>
                                                <p className="text-sm text-emerald-300 font-medium">{strategy.bestWhen}</p>
                                            </div>
                                            <div className="bg-slate-950/30 p-3 rounded border border-slate-800/50">
                                                <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">Popularidade</span>
                                                <div className="flex gap-0.5 mt-1">
                                                    {Array.from({ length: 5 }).map((_, i) => (
                                                        <Star key={i} className={`h-3 w-3 ${i < strategy.popularity ? "text-yellow-500 fill-current" : "text-slate-700"}`} />
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800">
                                            <h3 className="font-semibold text-emerald-400 mb-2 flex items-center gap-2">
                                                <TrendingUp className="h-4 w-4" /> Como Montar (Entrada)
                                            </h3>
                                            <ul className="list-disc list-inside text-sm text-slate-300 space-y-2">
                                                {strategy.entry.map((step, idx) => (
                                                    <li key={idx}>{step}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800">
                                            <h3 className="font-semibold text-rose-400 mb-2 flex items-center gap-2">
                                                <Activity className="h-4 w-4" /> Como Desmontar (Saída)
                                            </h3>
                                            <ul className="list-disc list-inside text-sm text-slate-300 space-y-2">
                                                {strategy.exit.map((step, idx) => (
                                                    <li key={idx}>{step}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    )
}
