'use client'

import { useState } from 'react'
import { Signal } from '@/types/signals'

const fmtNum = (v: number | null | undefined, digits = 2): string =>
    v != null && Number.isFinite(v) ? v.toFixed(digits) : '—'

const LIQUIDEZ_BADGE: Record<'normal' | 'atencao' | 'bloquear', { label: string; bg: string; color: string }> = {
    normal: { label: 'Liquidez normal', bg: 'var(--dw-green-soft)', color: 'var(--dw-green)' },
    atencao: { label: 'Liquidez: atenção', bg: '#FFFBEB', color: 'var(--dw-yellow)' },
    bloquear: { label: 'Liquidez: bloqueado (shadow)', bg: 'var(--dw-red-soft)', color: 'var(--dw-red)' },
}

const CLASSE_BADGE: Record<'A' | 'B' | 'C', { bg: string; color: string }> = {
    A: { bg: 'var(--dw-green-soft)', color: 'var(--dw-green)' },
    B: { bg: 'var(--dw-blue-soft)', color: 'var(--dw-blue)' },
    C: { bg: 'var(--dw-bg-soft)', color: 'var(--dw-ink-muted)' },
}

export default function SignalCard({ signal }: { signal: Signal }) {
    const [expanded, setExpanded] = useState(false)
    const isCall = signal.tipo_sinal === 'CALL'
    const liquidez = signal.filtro_liquidez_decisao ? LIQUIDEZ_BADGE[signal.filtro_liquidez_decisao] : null
    const classe = signal.classe_v2 ? CLASSE_BADGE[signal.classe_v2] : null
    const vxbrColor = signal.vxbr == null
        ? 'var(--dw-ink-mid)'
        : signal.vxbr > 30 ? 'var(--dw-red)' : signal.vxbr > 25 ? 'var(--dw-yellow)' : 'var(--dw-ink-mid)'
    const divergAlta = signal.divergencia_premio_pct != null && signal.divergencia_premio_pct > 15
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    // Fallback: se score_ponderado não existir, escala o score técnico antigo (que era de ~0 a 10)
    const confidenceScore = signal.score_ponderado ?? (signal.score * 10 || 0);

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
                    <div className="font-mono font-bold text-dw-ink text-lg">{confidenceScore}<span className="text-dw-ink-muted text-sm">/100</span></div>
                </div>
            </div>

            {/* Badges: evento, classe v2, filtro de liquidez (informativos) */}
            {(signal.evento_label || classe || liquidez || signal.absorcao) && (
                <div className="flex flex-wrap items-center gap-2">
                    {signal.evento_label && (
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{ background: '#FFFBEB', color: '#92400E', border: '1px solid var(--dw-yellow)' }}
                            title={`Evento no dia: ${signal.evento_label}`}
                        >
                            ⚠ {signal.evento_label}
                        </span>
                    )}
                    {classe && signal.classe_v2 && (
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{ background: classe.bg, color: classe.color }}
                            title={signal.razoes_downgrade_classe?.length
                                ? `Notas de classe: ${signal.razoes_downgrade_classe.join('; ')}`
                                : 'Classe de emissão v2 (shadow)'}
                        >
                            Classe {signal.classe_v2}
                        </span>
                    )}
                    {liquidez && (
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{ background: liquidez.bg, color: liquidez.color }}
                            title={signal.filtro_liquidez_motivo ?? 'Filtro informativo (shadow) — não bloqueia o sinal'}
                        >
                            {liquidez.label}
                        </span>
                    )}
                    {signal.absorcao && (
                        <span
                            className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                            style={{ background: '#FFFBEB', color: '#92400E', border: '1px solid var(--dw-yellow)' }}
                            title="Rompimento do HC testado e rejeitado com fluxo neutro (telemetria shadow)"
                        >
                            Absorção HC
                        </span>
                    )}
                </div>
            )}

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
                        <p className="text-dw-ink-muted mt-0.5">-43%</p>
                    </div>
                </div>
            </div>

            {/* Níveis no ativo subjacente (PUCK — gestão pela tese, não pela opção) */}
            {signal.ativo_stop != null && (
                <div className="bg-dw-bg-soft rounded-lg p-3 space-y-1">
                    <p className="label">Níveis no ativo (ATR)</p>
                    <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                        <div>
                            <span className="text-dw-ink-muted">Stop</span>
                            <p className="font-semibold" style={{ color: 'var(--dw-red)' }}>R$ {fmtNum(signal.ativo_stop)}</p>
                        </div>
                        <div>
                            <span className="text-dw-ink-muted">TP1 (50%)</span>
                            <p className="font-semibold text-dw-ink">R$ {fmtNum(signal.ativo_tp1)}</p>
                        </div>
                        <div>
                            <span className="text-dw-ink-muted">TP2 (100%)</span>
                            <p className="font-semibold text-dw-ink">R$ {fmtNum(signal.ativo_tp2)}</p>
                        </div>
                    </div>
                    <p className="text-[10px] text-dw-ink-muted">
                        Gestão pelo ativo: no TP1 realizar 50% e mover o stop para a entrada
                        (R$ {fmtNum(signal.ativo_entrada)}); zerar se o ativo fechar além do stop.
                    </p>
                </div>
            )}

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

            {/* Executabilidade (dados D-1 da B3) */}
            {(signal.oi != null || signal.bid != null || signal.ask != null || signal.spread_pct != null || signal.vxbr != null) && (
                <div className="bg-dw-bg-soft rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                        <p className="label">Executabilidade</p>
                        <span className="text-[10px] text-dw-ink-muted" title="Dados do fechamento do pregão anterior (D-1)">fech. anterior</span>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                        <div>
                            <p className="label">OI</p>
                            <p className="font-mono font-bold text-dw-ink-mid">
                                {signal.oi != null ? signal.oi.toLocaleString('pt-BR') : '—'}
                            </p>
                        </div>
                        <div>
                            <p className="label">Bid/Ask</p>
                            <p className="font-mono font-bold text-dw-ink-mid">
                                {signal.bid != null || signal.ask != null
                                    ? `${fmtNum(signal.bid)} / ${fmtNum(signal.ask)}`
                                    : '—'}
                            </p>
                        </div>
                        <div>
                            <p className="label">Spread</p>
                            <p className="font-mono font-bold text-dw-ink-mid">
                                {signal.spread_pct != null ? `${fmtNum(signal.spread_pct, 1)}%` : '—'}
                            </p>
                        </div>
                        <div>
                            <p className="label">VXBR</p>
                            <p className="font-mono font-bold" style={{ color: vxbrColor }}>
                                {fmtNum(signal.vxbr, 1)}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Sizing sugerido & divergência de prêmio (informativos) */}
            {(signal.sizing_sugerido_pct != null || signal.divergencia_premio_pct != null) && (
                <div className="text-xs space-y-1">
                    {signal.sizing_sugerido_pct != null && (
                        <p className="text-dw-ink-mid">
                            Sizing sugerido: <span className="font-mono font-bold">{signal.sizing_sugerido_pct.toFixed(1)}% do capital</span>
                            <span className="text-dw-ink-muted"> (informativo)</span>
                        </p>
                    )}
                    {signal.divergencia_premio_pct != null && (
                        <p
                            className={divergAlta ? 'font-semibold' : 'text-dw-ink-mid'}
                            style={divergAlta ? { color: 'var(--dw-yellow)' } : undefined}
                            title="Divergência entre prêmio real (D-1) e prêmio modelado (Black-Scholes)"
                        >
                            Divergência de prêmio: <span className="font-mono font-bold">{signal.divergencia_premio_pct.toFixed(1)}%</span>
                            {divergAlta && ' ⚠'}
                        </p>
                    )}
                </div>
            )}

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

            {/* Greeks (expandido) */}
            {expanded && signal.greeks && (
                <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-lg p-3 space-y-2">
                    <p className="label">Detalhes Técnicos (Black-Scholes)</p>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                            <p className="label">Delta</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{signal.greeks.delta?.toFixed(3)}</p>
                        </div>
                        <div>
                            <p className="label">Theta/dia</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{signal.greeks.theta?.toFixed(4)}</p>
                        </div>
                        <div>
                            <p className="label">Vega</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{signal.greeks.vega?.toFixed(4)}</p>
                        </div>
                        <div>
                            <p className="label">Gamma</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{signal.greeks.gamma?.toFixed(4)}</p>
                        </div>
                        <div>
                            <p className="label">POP</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{(signal.greeks.prob_profit * 100)?.toFixed(0)}%</p>
                        </div>
                        <div>
                            <p className="label">HV 20d</p>
                            <p className="font-mono font-bold text-dw-ink-mid">{signal.hv_20d?.toFixed(1)}%</p>
                        </div>
                    </div>
                    {signal.score_ponderado != null && (
                        <div className="pt-2 border-t border-dw-rule-soft flex items-center justify-between text-xs">
                            <span className="label">Score ponderado (shadow)</span>
                            <span className={`font-mono font-bold ${signal.ponderado_passou ? 'text-dw-green' : 'text-dw-ink-muted'}`}>
                                {signal.score_ponderado}/100 {signal.ponderado_passou ? '✓' : '—'}
                            </span>
                        </div>
                    )}
                    {signal.book_until && (
                        <p className="text-xs text-dw-ink-muted">Book válido até {signal.book_until}</p>
                    )}
                </div>
            )}

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
                {expanded ? '▼ Ocultar Detalhes' : '▶ Ver Detalhes & Greeks'}
            </button>
        </div>
    )
}
