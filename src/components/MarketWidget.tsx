"use client"

import { useState, useEffect, useCallback } from "react"
import { RefreshCw } from "lucide-react"
import api from "@/lib/api"

interface MktRow {
    ticker: string
    price: number
    chg_pct: number
}

interface OpcaoRow {
    ticker_opcao: string
    ticker_subjacente: string
    tipo: "CALL" | "PUT"
    strike: number
    preco: number
    negocios: number
}

interface MarketData {
    indices: MktRow[]
    acoes: MktRow[]
}

// Static fallback shown while loading or when backend is offline
const FALLBACK: MarketData = {
    indices: [
        { ticker: "IBOV", price: 131420, chg_pct: 0 },
    ],
    acoes: [
        { ticker: "PETR4", price: 36.88, chg_pct: 0 },
        { ticker: "VALE3", price: 58.12, chg_pct: 0 },
        { ticker: "ITUB4", price: 33.45, chg_pct: 0 },
        { ticker: "WEGE3", price: 52.70, chg_pct: 0 },
        { ticker: "ABEV3", price: 11.94, chg_pct: 0 },
        { ticker: "BBAS3", price: 28.72, chg_pct: 0 },
        { ticker: "MGLU3", price: 4.35,  chg_pct: 0 },
        { ticker: "RENT3", price: 51.60, chg_pct: 0 },
    ],
}

// Opções mock — formato B3: [4 letras ativo][1 letra CALL(A-L)/PUT(M-X) + mês][3 dígitos strike]
// Usado apenas se o endpoint /market/opcoes falhar
const OPCOES_FALLBACK: OpcaoRow[] = [
    { ticker_opcao: "VALEF580", ticker_subjacente: "VALE3", tipo: "CALL", strike: 58.00, preco: 1.42, negocios: 0 },
    { ticker_opcao: "PETRF370", ticker_subjacente: "PETR4", tipo: "CALL", strike: 37.00, preco: 0.88, negocios: 0 },
    { ticker_opcao: "ITUBR330", ticker_subjacente: "ITUB4", tipo: "PUT",  strike: 33.00, preco: 0.54, negocios: 0 },
    { ticker_opcao: "VALER580", ticker_subjacente: "VALE3", tipo: "PUT",  strike: 58.00, preco: 2.10, negocios: 0 },
    { ticker_opcao: "WEGEF530", ticker_subjacente: "WEGE3", tipo: "CALL", strike: 53.00, preco: 0.32, negocios: 0 },
    { ticker_opcao: "MGLUF049", ticker_subjacente: "MGLU3", tipo: "CALL", strike: 4.90,  preco: 0.18, negocios: 0 },
]

const REFRESH_MS = 5 * 60 * 1000 // 5 min

function formatPrice(n: number): string {
    if (n > 1000) return n.toLocaleString("pt-BR", { maximumFractionDigits: 0 })
    return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const TABS = ["Índices", "Ações", "Opções"]

export default function MarketWidget() {
    const [activeTab, setActiveTab] = useState(0)
    const [data, setData] = useState<MarketData | null>(null)
    const [loading, setLoading] = useState(true)
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

    const [opcoes, setOpcoes] = useState<OpcaoRow[] | null>(null)
    const [opcoesLoading, setOpcoesLoading] = useState(false)
    const [opcoesAttempted, setOpcoesAttempted] = useState(false)
    const [opcoesLastUpdate, setOpcoesLastUpdate] = useState<Date | null>(null)

    const [opcoesTicker, setOpcoesTicker] = useState("PETR4")
    const [opcoesTickerInput, setOpcoesTickerInput] = useState("PETR4")

    const fetchMarket = useCallback(async () => {
        try {
            const res = await api.get("/market")
            setData(res.data)
            setLastUpdate(new Date())
        } catch {
            // silently fall back to static data
        } finally {
            setLoading(false)
        }
    }, [])

    const fetchOpcoes = useCallback(async () => {
        setOpcoesLoading(true)
        try {
            const res = await api.get(`/market/opcoes/chain/${opcoesTicker}`)
            setOpcoes(res.data?.chain ?? null)
            setOpcoesLastUpdate(new Date())
        } catch {
            setOpcoes(null) // mantém null → frontend usa fallback
        } finally {
            setOpcoesLoading(false)
            setOpcoesAttempted(true)
        }
    }, [opcoesTicker])

    useEffect(() => {
        fetchMarket()
        const interval = setInterval(fetchMarket, REFRESH_MS)
        return () => clearInterval(interval)
    }, [fetchMarket])

    // Lazy load + auto-refresh: busca opções na 1ª ativação E a cada 5min enquanto a tab estiver ativa
    useEffect(() => {
        if (activeTab !== 2) return
        if (!opcoesAttempted && !opcoesLoading) fetchOpcoes()
        const interval = setInterval(fetchOpcoes, REFRESH_MS)
        return () => clearInterval(interval)
    }, [activeTab, opcoesAttempted, opcoesLoading, fetchOpcoes])

    const displayed = data ?? FALLBACK
    const opcoesRows: OpcaoRow[] = opcoes && opcoes.length > 0 ? opcoes : OPCOES_FALLBACK
    const opcoesFromFallback = !opcoes || opcoes.length === 0

    return (
        <div className="market-widget">
            <div className="flex items-center justify-between mb-1">
                <div className="market-widget-title">Mercado ao Vivo</div>
                <button
                    onClick={() => {
                        if (activeTab === 2) {
                            setOpcoesAttempted(false)
                            fetchOpcoes()
                        } else {
                            setLoading(true)
                            fetchMarket()
                        }
                    }}
                    className="opacity-50 hover:opacity-100 transition-opacity"
                    title={(() => {
                        const ts = activeTab === 2 ? opcoesLastUpdate : lastUpdate
                        return ts ? `Atualizado às ${ts.toLocaleTimeString("pt-BR")}` : ""
                    })()}
                >
                    <RefreshCw className={`h-3 w-3 ${loading || opcoesLoading ? "animate-spin" : ""}`} style={{ color: "var(--dw-ink-muted)" }} />
                </button>
            </div>

            <div className="mw-tab-bar">
                {TABS.map((tab, i) => (
                    <button
                        key={i}
                        className={`mw-tab-btn${activeTab === i ? " active" : ""}`}
                        onClick={() => setActiveTab(i)}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            <div className="mw-tab-panels">
                <div className="mw-tab-panel active">
                    <table className="mkt-table">
                        <thead>
                            {activeTab === 2 ? (
                                <>
                                    <tr>
                                        <td colSpan={3} className="p-2">
                                            <form
                                                onSubmit={(e) => {
                                                    e.preventDefault()
                                                    setOpcoesTicker(opcoesTickerInput.toUpperCase())
                                                }}
                                                className="flex gap-2"
                                            >
                                                <input
                                                    type="text"
                                                    value={opcoesTickerInput}
                                                    onChange={(e) => setOpcoesTickerInput(e.target.value)}
                                                    placeholder="Ticker (ex: PETR4)"
                                                    className="w-full text-xs px-2 py-1 rounded bg-transparent border focus:outline-none"
                                                    style={{ borderColor: "var(--dw-rule)", color: "var(--dw-ink)" }}
                                                />
                                                <button type="submit" className="text-xs px-2 rounded btn-secondary">
                                                    Buscar
                                                </button>
                                            </form>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Preço</th>
                                        <th>Strike</th>
                                    </tr>
                                </>
                            ) : (
                                <tr>
                                    <th>Ticker</th>
                                    <th>Preço</th>
                                    <th>Var.</th>
                                </tr>
                            )}
                        </thead>
                        <tbody>
                            {activeTab === 2 ? (
                                // Tab Opções
                                opcoesLoading && !opcoes ? (
                                    Array.from({ length: 4 }).map((_, i) => (
                                        <tr key={i}>
                                            <td colSpan={3}>
                                                <div className="h-3 rounded animate-pulse" style={{ background: "var(--dw-rule)" }} />
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    opcoesRows.map((op, j) => (
                                        <tr key={`${op.ticker_opcao}-${j}`}>
                                            <td className="mkt-ticker">
                                                {op.ticker_opcao}
                                                <span
                                                    className="ml-1.5 text-[9px] font-bold px-1 py-0.5 rounded"
                                                    style={{
                                                        background: op.tipo === "CALL" ? "var(--dw-green-soft)" : "var(--dw-red-soft)",
                                                        color: op.tipo === "CALL" ? "var(--dw-green)" : "var(--dw-red)",
                                                    }}
                                                >
                                                    {op.tipo}
                                                </span>
                                            </td>
                                            <td className="mkt-price">{formatPrice(op.preco)}</td>
                                            <td className="mkt-price" style={{ color: "var(--dw-ink-muted)" }}>
                                                {formatPrice(op.strike)}
                                            </td>
                                        </tr>
                                    ))
                                )
                            ) : (
                                // Tabs Índices / Ações
                                (() => {
                                    const rows = activeTab === 0 ? displayed.indices : displayed.acoes
                                    if (loading && rows.length === 0) {
                                        return Array.from({ length: 4 }).map((_, i) => (
                                            <tr key={i}>
                                                <td colSpan={3}>
                                                    <div className="h-3 rounded animate-pulse" style={{ background: "var(--dw-rule)" }} />
                                                </td>
                                            </tr>
                                        ))
                                    }
                                    return rows.map((row, j) => (
                                        <tr key={`${row.ticker}-${j}`}>
                                            <td className="mkt-ticker">{row.ticker}</td>
                                            <td className="mkt-price">{formatPrice(row.price)}</td>
                                            <td className={`mkt-chg ${row.chg_pct >= 0 ? "pos" : "neg"}`}>
                                                {row.chg_pct >= 0 ? "+" : ""}{row.chg_pct.toFixed(2).replace(".", ",")}%
                                                {!data && <span className="opacity-40 text-xs"> —</span>}
                                            </td>
                                        </tr>
                                    ))
                                })()
                            )}
                        </tbody>
                    </table>

                    {activeTab === 2 && opcoesFromFallback && opcoesAttempted && (
                        <p className="text-xs mt-2 text-center" style={{ color: "var(--dw-ink-muted)" }}>
                            Backend offline — opções de exemplo
                        </p>
                    )}
                    {activeTab === 2 && !opcoesFromFallback && (
                        <p className="text-xs mt-2 text-center" style={{ color: "var(--dw-ink-muted)" }}>
                            {opcoesRows.length} opções líquidas · opcoes.net.br
                        </p>
                    )}
                    {activeTab !== 2 && !data && !loading && (
                        <p className="text-xs mt-2 text-center" style={{ color: "var(--dw-ink-muted)" }}>
                            Backend offline — dados estáticos
                        </p>
                    )}
                </div>
            </div>
        </div>
    )
}
