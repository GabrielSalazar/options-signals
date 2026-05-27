'use client'

import { useState } from 'react'
import { Signal } from '@/types/signals'

export default function SignalCard({ signal }: { signal: Signal }) {
    const [expanded, setExpanded] = useState(false)
    const isCall = signal.tipo_sinal === 'CALL'
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    return (
        <div
            className="card cursor-pointer"
            style={{
                borderLeft: `3px solid ${isCall ? 'var(--dw-green)' : 'var(--dw-red)'}`,
                gap: '12px',
            }}
            onClick={() => setExpanded(!expanded)}
        >
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="font-serif text-lg font-bold text-dw-ink">{signal.ticker}</span>
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{
                                background: isCall ? 'var(--dw-green-soft)' : 'var(--dw-red-soft)',
                                color: isCall ? 'var(--dw-green)' : 'var(--dw-red)',
                            }}
                        >
                            {signal.tipo_sinal}
                        </span>
                    </div>
                    <p className="text-xs text-dw-ink-muted">{signal.nome}</p>
                </div>
                <div className="text-right">
                    <span className="label">Score</span>
                    <div className="font-mono font-bold text-dw-ink text-lg">{signal.score}<span className="text-dw-ink-muted text-sm">/10</span></div>
                </div>
            </div>

            {/* Preços */}
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-dw-rule-soft">
                <div>
                    <p className="label">Preço Ação</p>
                    <p className="font-mono font-bold text-dw-ink-mid">R$ {signal.preco_acao?.toFixed(2)}</p>
                </div>
                <div>
                    <p className="label">Strike ({signal.dist_otm_pct?.toFixed(0)}% OTM)</p>
                    <p className="font-mono font-bold text-dw-ink-mid">R$ {signal.strike_ref?.toFixed(2)}</p>
                </div>
            </div>

            {/* Entrada / Alvos */}
            <div className="bg-dw-bg-soft rounded-lg p-3 space-y-2">
                <div>
                    <p className="label">Zona de Entrada</p>
                    <p className="font-mono font-semibold text-dw-ink">
                        R$ {signal.entrada_min?.toFixed(2)} – {signal.entrada_max?.toFixed(2)}
                    </p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs pt-1 border-t border-dw-rule-soft">
                    <div>
                        <p className="label">Alvo 1</p>
                        <p className="font-mono font-bold text-dw-green">R$ {signal.alvo1?.toFixed(2)}</p>
                        <p className="text-dw-ink-muted mt-0.5">R/R {signal.rr_alvo1?.toFixed(1)}x</p>
                    </div>
                    <div>
                        <p className="label">Alvo 2</p>
                        <p className="font-mono font-bold text-dw-green">R$ {signal.alvo2?.toFixed(2)}</p>
                        <p className="text-dw-ink-muted mt-0.5">R/R {signal.rr_alvo2?.toFixed(1)}x</p>
                    </div>
                    <div>
                        <p className="label">Stop</p>
                        <p className="font-mono font-bold text-dw-red">R$ {signal.stop?.toFixed(2)}</p>
                        <p className="text-dw-ink-muted mt-0.5">-42%</p>
                    </div>
                </div>
            </div>

            {/* Indicadores */}
            <div className="grid grid-cols-3 gap-2 text-xs">
                {[
                    { label: 'Stoch %K', value: signal.stoch_k?.toFixed(1) ?? '—' },
                    { label: 'RSI', value: signal.rsi?.toFixed(1) ?? '—' },
                    { label: 'Vol Ratio', value: signal.vol_ratio != null ? `${signal.vol_ratio.toFixed(1)}x` : '—' },
                ].map(({ label, value }) => (
                    <div key={label} className="bg-dw-bg-soft rounded p-2 text-center">
                        <p className="label">{label}</p>
                        <p className="font-mono font-bold text-dw-ink-mid">{value}</p>
                    </div>
                ))}
            </div>

            {/* DTE & Vencimento */}
            <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-dw-bg-soft rounded p-2">
                    <p className="label">DTE</p>
                    <p className="font-mono font-bold text-dw-ink-mid">{signal.dte} dias úteis</p>
                </div>
                <div className="bg-dw-bg-soft rounded p-2">
                    <p className="label">Vencimento</p>
                    <p className="font-mono font-bold text-dw-ink-mid">
                        {signal.mes_venc ? meses[signal.mes_venc - 1] : '—'}/{signal.ano_venc ? String(signal.ano_venc).slice(-2) : '—'}
                    </p>
                </div>
            </div>

            {/* Gatilhos (expandido) */}
            {expanded && signal.gatilhos?.length > 0 && (
                <div className="bg-dw-blue-soft border border-dw-rule rounded-lg p-3 space-y-2">
                    <p className="label text-dw-blue">Gatilhos Ativados ({signal.gatilhos.length})</p>
                    <ul className="space-y-1">
                        {signal.gatilhos.map((g, i) => (
                            <li key={i} className="text-xs text-dw-ink-mid flex items-start gap-2">
                                <span className="text-dw-blue mt-0.5">•</span>
                                <span>{g}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Toggle */}
            <button
                className="btn-secondary w-full justify-center text-xs"
                onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
                {expanded ? '▼ Ocultar Gatilhos' : '▶ Ver Gatilhos'}
            </button>
        </div>
    )
}
