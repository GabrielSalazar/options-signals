"use client"

import { useEffect, useState } from "react"
import { BACKEND_URL } from "@/lib/config"

interface TickerItem {
    name: string
    price: string
    change: string
    positive: boolean
}

const FALLBACK: TickerItem[] = [
    { name: "IBOV",   price: "131.420",  change: "+0,84%",  positive: true  },
    { name: "IBRA",   price: "3.218,50", change: "+0,71%",  positive: true  },
    { name: "VALE3",  price: "58,12",    change: "-0,43%",  positive: false },
    { name: "PETR4",  price: "36,88",    change: "+1,12%",  positive: true  },
    { name: "ITUB4",  price: "33,45",    change: "+0,30%",  positive: true  },
    { name: "WEGE3",  price: "52,70",    change: "-0,19%",  positive: false },
    { name: "ABEV3",  price: "11,94",    change: "+0,59%",  positive: true  },
    { name: "BBAS3",  price: "28,72",    change: "-0,28%",  positive: false },
    { name: "MGLU3",  price: "4,35",     change: "+2,11%",  positive: true  },
    { name: "USD/BRL", price: "5,1420",  change: "-0,15%",  positive: false },
    { name: "DI Jan26", price: "14,87%", change: "+0,02pp", positive: false },
]

interface MarketQuote {
    ticker: string
    price: number | string
    chg_pct: number
}

export default function TickerBar() {
    const [items, setItems] = useState<TickerItem[]>(FALLBACK)
    const [isFallback, setIsFallback] = useState(true)

    useEffect(() => {
        const controller = new AbortController()
        const timer = setTimeout(() => controller.abort(), 8000)

        fetch(`${BACKEND_URL}/market`, { signal: controller.signal })
            .then((r) => r.json())
            .then((data) => {
                const list: TickerItem[] = []
                if (data.indices) {
                    data.indices.forEach((ind: MarketQuote) => {
                        list.push({
                            name: ind.ticker,
                            price: typeof ind.price === "number" 
                                ? ind.price.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                : ind.price,
                            change: `${ind.chg_pct >= 0 ? "+" : ""}${ind.chg_pct.toFixed(2)}%`,
                            positive: ind.chg_pct >= 0,
                        })
                    })
                }
                if (data.acoes) {
                    data.acoes.forEach((ac: MarketQuote) => {
                        list.push({
                            name: ac.ticker,
                            price: typeof ac.price === "number"
                                ? ac.price.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                : ac.price,
                            change: `${ac.chg_pct >= 0 ? "+" : ""}${ac.chg_pct.toFixed(2)}%`,
                            positive: ac.chg_pct >= 0,
                        })
                    })
                }
                if (list.length > 0) {
                    setItems(list)
                    setIsFallback(false)
                }
            })
            .catch(() => {})
            .finally(() => clearTimeout(timer))
    }, [])

    const doubled = [...items, ...items]

    return (
        <div className="ticker-bar" aria-label="Dados de mercado">
            <span className="ticker-bar-label">
                Mercado {isFallback && <span style={{ fontSize: "10px", opacity: 0.6, marginLeft: "4px", fontWeight: "normal" }}>(Simulado)</span>}
            </span>
            <div className="ticker-track-wrap">
                <div className="ticker-track">
                    {doubled.map((item, i) => (
                        <div key={i} className="ticker-pill">
                            <span className="ticker-pill-name">{item.name}</span>
                            <span className="ticker-pill-price">{item.price}</span>
                            <span className={`ticker-pill-change ${item.positive ? "pos" : "neg"}`}>
                                {item.change}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
