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

function buildFromSignals(signals: { ticker?: string; price?: number; change_pct?: number }[]): TickerItem[] {
    if (!signals?.length) return []
    return signals.slice(0, 10).map((s) => {
        const chg = s.change_pct ?? 0
        return {
            name: s.ticker ?? "—",
            price: s.price?.toFixed(2) ?? "—",
            change: `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%`,
            positive: chg >= 0,
        }
    })
}

export default function TickerBar() {
    const [items, setItems] = useState<TickerItem[]>(FALLBACK)

    useEffect(() => {
        const controller = new AbortController()
        const timer = setTimeout(() => controller.abort(), 3000)

        fetch(`${BACKEND_URL}/signals`, { signal: controller.signal })
            .then((r) => r.json())
            .then((data) => {
                const built = buildFromSignals(Array.isArray(data) ? data : data?.signals ?? [])
                if (built.length > 0) setItems(built)
            })
            .catch(() => {})
            .finally(() => clearTimeout(timer))
    }, [])

    const doubled = [...items, ...items]

    return (
        <div className="ticker-bar" aria-label="Dados de mercado">
            <span className="ticker-bar-label">Mercado</span>
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
