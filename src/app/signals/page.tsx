"use client"

import { useState, useMemo } from 'react'
import SignalCard from '@/components/SignalCard'
import { useSignals } from '@/hooks/useSignals'
import { Signal } from '@/types/signals'
import { Activity, Filter, X, AlertCircle, Wifi } from 'lucide-react'

// ── Setores e papéis da B3 ─────────────────────────────────────────────
const SECTORS: Record<string, { ticker: string; nome: string }[]> = {
    'Todos': [],
    'Petróleo & Gás': [
        { ticker: 'PETR4', nome: 'Petrobras PN' },
        { ticker: 'PETR3', nome: 'Petrobras ON' },
        { ticker: 'PRIO3', nome: 'PetroRio' },
        { ticker: 'RRRP3', nome: '3R Petroleum' },
        { ticker: 'RECV3', nome: 'Recôncavo' },
    ],
    'Mineração': [
        { ticker: 'VALE3', nome: 'Vale' },
        { ticker: 'CSNA3', nome: 'CSN' },
        { ticker: 'GGBR4', nome: 'Gerdau PN' },
        { ticker: 'USIM5', nome: 'Usiminas PNA' },
        { ticker: 'CMIN3', nome: 'CSN Mineração' },
    ],
    'Financeiro': [
        { ticker: 'ITUB4', nome: 'Itaú Unibanco PN' },
        { ticker: 'BBDC4', nome: 'Bradesco PN' },
        { ticker: 'BBAS3', nome: 'Banco do Brasil' },
        { ticker: 'SANB11', nome: 'Santander' },
        { ticker: 'BPAC11', nome: 'BTG Pactual' },
        { ticker: 'B3SA3', nome: 'B3' },
    ],
    'Varejo': [
        { ticker: 'MGLU3', nome: 'Magazine Luiza' },
        { ticker: 'VIIA3', nome: 'Via' },
        { ticker: 'LREN3', nome: 'Lojas Renner' },
        { ticker: 'SOMA3', nome: 'Grupo SOMA' },
        { ticker: 'AMER3', nome: 'Americanas' },
    ],
    'Energia': [
        { ticker: 'EGIE3', nome: 'Engie Brasil' },
        { ticker: 'TAEE11', nome: 'Taesa' },
        { ticker: 'ENGI11', nome: 'Energisa' },
        { ticker: 'CMIG4', nome: 'Cemig PN' },
        { ticker: 'CPFE3', nome: 'CPFL Energia' },
        { ticker: 'SBSP3', nome: 'Sabesp' },
    ],
    'Industrial': [
        { ticker: 'WEGE3', nome: 'Weg' },
        { ticker: 'EMBR3', nome: 'Embraer' },
        { ticker: 'RAIL3', nome: 'Rumo' },
        { ticker: 'MOVI3', nome: 'Movida' },
        { ticker: 'RENT3', nome: 'Localiza' },
    ],
    'Consumo': [
        { ticker: 'ABEV3', nome: 'Ambev' },
        { ticker: 'BRFS3', nome: 'BRF' },
        { ticker: 'JBSS3', nome: 'JBS' },
        { ticker: 'MRFG3', nome: 'Marfrig' },
        { ticker: 'SMTO3', nome: 'São Martinho' },
    ],
    'Telecom': [
        { ticker: 'VIVT3', nome: 'Vivo' },
        { ticker: 'TIMS3', nome: 'TIM' },
        { ticker: 'OIBR3', nome: 'Oi' },
    ],
}

const ALL_STOCKS = Object.entries(SECTORS)
    .filter(([s]) => s !== 'Todos')
    .flatMap(([setor, stocks]) => stocks.map(s => ({ ...s, setor })))

const TICKER_SETOR: Record<string, string> = Object.fromEntries(
    ALL_STOCKS.map(s => [s.ticker, s.setor])
)

// ── Sinais de exemplo (fallback quando backend não tem dados) ──────────
const DEMO_SIGNALS: Signal[] = [
    {
        ticker: 'PETR4', nome: 'Petrobras PN', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 37.50, ticker_opcao: 'PETRF380', strike_ref: 39.38, dist_otm_pct: 5, iv_hist: 32.5, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.45, preco_tela: 0.43, entrada_min: 0.40, entrada_max: 0.50,
        alvo1: 0.56, alvo2: 1.13, alvo_final: 2.25, stop: 0.26, rr_alvo1: 0.8, rr_alvo2: 1.51,
        rr_final: 3.96, score: 8, stoch_k: 22.5, rsi: 32.1, vol_ratio: 1.8,
        gatilhos: ['📈 Estocástico: cruzamento altista em sobrevenda', '📈 RSI sobrevenda: 32.1', '📈 Preço em suporte 20D', '📈 EMA9 cruzou acima EMA21'],
    },
    {
        ticker: 'VALE3', nome: 'Vale', tipo_sinal: 'PUT', direcao: 'COMPRA DE PUT',
        preco_acao: 68.20, ticker_opcao: 'VALEP645', strike_ref: 64.59, dist_otm_pct: 5, iv_hist: 28.2, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.38, preco_tela: null, entrada_min: 0.34, entrada_max: 0.42,
        alvo1: 0.47, alvo2: 0.95, alvo_final: 1.90, stop: 0.22, rr_alvo1: 0.68, rr_alvo2: 1.92,
        rr_final: 3.93, score: 7, stoch_k: 78.5, rsi: 68.3, vol_ratio: 1.6,
        gatilhos: ['📉 Estocástico: cruzamento baixista em sobrecompra', '📉 RSI sobrecompra: 68.3', '📉 Preço em resistência 20D'],
    },
    {
        ticker: 'MGLU3', nome: 'Magazine Luiza', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 9.85, ticker_opcao: 'MGLUF109', strike_ref: 10.95, dist_otm_pct: 11, iv_hist: 42.1, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.32, preco_tela: null, entrada_min: 0.29, entrada_max: 0.35,
        alvo1: 0.40, alvo2: 0.80, alvo_final: 1.60, stop: 0.19, rr_alvo1: 0.91, rr_alvo2: 2.27,
        rr_final: 4.82, score: 9, stoch_k: 18.2, rsi: 28.9, vol_ratio: 2.1,
        gatilhos: ['📈 Estocástico: cruzamento altista em sobrevenda', '📈 RSI sobrevenda: 28.9', '📈 Volume 2.1x acima da média', '📈 Divergência altista RSI'],
    },
    {
        ticker: 'ITUB4', nome: 'Itaú Unibanco PN', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 33.45, ticker_opcao: 'ITUBF350', strike_ref: 35.10, dist_otm_pct: 5, iv_hist: 22.8, dte: 28,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.38, preco_tela: null, entrada_min: 0.34, entrada_max: 0.42,
        alvo1: 0.48, alvo2: 0.95, alvo_final: 1.90, stop: 0.22, rr_alvo1: 0.71, rr_alvo2: 1.68,
        rr_final: 4.18, score: 7, stoch_k: 25.4, rsi: 34.2, vol_ratio: 1.5,
        gatilhos: ['📈 Estocástico sobrevenda', '📈 RSI sobrevenda: 34.2', '📈 Suporte em R$32.80'],
    },
    {
        ticker: 'WEGE3', nome: 'Weg', tipo_sinal: 'PUT', direcao: 'COMPRA DE PUT',
        preco_acao: 52.70, ticker_opcao: 'WEGEP499', strike_ref: 49.90, dist_otm_pct: 5, iv_hist: 19.4, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.55, preco_tela: null, entrada_min: 0.50, entrada_max: 0.60,
        alvo1: 0.69, alvo2: 1.38, alvo_final: 2.75, stop: 0.32, rr_alvo1: 0.76, rr_alvo2: 1.53,
        rr_final: 3.84, score: 6, stoch_k: 72.1, rsi: 66.8, vol_ratio: 1.4,
        gatilhos: ['📉 RSI sobrecompra: 66.8', '📉 Resistência histórica R$53.50', '📉 Volume declinante'],
    },
    {
        ticker: 'ABEV3', nome: 'Ambev', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 11.94, ticker_opcao: 'ABEVF125', strike_ref: 12.53, dist_otm_pct: 5, iv_hist: 24.6, dte: 14,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.18, preco_tela: null, entrada_min: 0.16, entrada_max: 0.20,
        alvo1: 0.22, alvo2: 0.45, alvo_final: 0.90, stop: 0.10, rr_alvo1: 0.75, rr_alvo2: 1.81,
        rr_final: 4.50, score: 8, stoch_k: 19.3, rsi: 30.5, vol_ratio: 1.9,
        gatilhos: ['📈 Estocástico sobrevenda', '📈 RSI sobrevenda: 30.5', '📈 Suporte forte R$11.60', '📈 Candle de reversão'],
    },
    {
        ticker: 'BBAS3', nome: 'Banco do Brasil', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 28.72, ticker_opcao: 'BBASF301', strike_ref: 30.15, dist_otm_pct: 5, iv_hist: 26.3, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.29, preco_tela: null, entrada_min: 0.26, entrada_max: 0.32,
        alvo1: 0.36, alvo2: 0.72, alvo_final: 1.45, stop: 0.17, rr_alvo1: 0.67, rr_alvo2: 1.53,
        rr_final: 3.94, score: 7, stoch_k: 28.1, rsi: 35.7, vol_ratio: 1.7,
        gatilhos: ['📈 RSI sobrevenda', '📈 Cruzamento de médias EMA21/EMA50', '📈 Suporte em R$27.90'],
    },
    {
        ticker: 'EGIE3', nome: 'Engie Brasil', tipo_sinal: 'PUT', direcao: 'COMPRA DE PUT',
        preco_acao: 47.20, ticker_opcao: 'EGIEP448', strike_ref: 44.80, dist_otm_pct: 5, iv_hist: 16.2, dte: 28,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.42, preco_tela: null, entrada_min: 0.38, entrada_max: 0.46,
        alvo1: 0.52, alvo2: 1.05, alvo_final: 2.10, stop: 0.25, rr_alvo1: 0.71, rr_alvo2: 1.68,
        rr_final: 4.20, score: 6, stoch_k: 75.8, rsi: 70.2, vol_ratio: 1.3,
        gatilhos: ['📉 RSI sobrecompra: 70.2', '📉 Topo duplo no gráfico diário', '📉 Divergência baixista MACD'],
    },
]

export default function SignalsPage() {
    const [selectedSector, setSelectedSector] = useState('Todos')
    const [selectedTicker, setSelectedTicker] = useState('')
    const [tipoSinal, setTipoSinal] = useState('Todos')
    const [minScore, setMinScore] = useState(5)

    const { signals: backendSignals, isLoading, isError } = useSignals(true)

    const isDemo = !isLoading && (!backendSignals || backendSignals.length === 0)
    const activeSignals = isDemo ? DEMO_SIGNALS : (backendSignals ?? [])

    const sectorStocks = useMemo(() => {
        if (selectedSector === 'Todos') return ALL_STOCKS
        return SECTORS[selectedSector] ?? []
    }, [selectedSector])

    const filtered = useMemo(() => {
        return activeSignals.filter((s) => {
            if (selectedTicker && s.ticker !== selectedTicker) return false
            if (tipoSinal !== 'Todos' && s.tipo_sinal !== tipoSinal) return false
            if (s.score < minScore) return false
            if (selectedSector !== 'Todos' && TICKER_SETOR[s.ticker] !== selectedSector) return false
            return true
        })
    }, [activeSignals, selectedSector, selectedTicker, tipoSinal, minScore])

    const calls = filtered.filter((s) => s.tipo_sinal === 'CALL').length
    const puts  = filtered.filter((s) => s.tipo_sinal === 'PUT').length
    const avgScore = filtered.length
        ? (filtered.reduce((a, s) => a + s.score, 0) / filtered.length).toFixed(1)
        : '—'

    const handleSectorClick = (sector: string) => {
        setSelectedSector(sector)
        setSelectedTicker('')
    }

    const handleTickerClick = (ticker: string) => {
        setSelectedTicker(prev => prev === ticker ? '' : ticker)
    }

    const clearFilters = () => {
        setSelectedSector('Todos')
        setSelectedTicker('')
        setTipoSinal('Todos')
        setMinScore(5)
    }

    const hasActiveFilters = selectedSector !== 'Todos' || selectedTicker || tipoSinal !== 'Todos' || minScore !== 5

    return (
        <main className="main-content">
            <div className="page-header">
                <div>
                    <h1 className="font-serif">Sinais Gerados</h1>
                    <p className="mt-2 text-dw-ink-light text-lg">
                        Todos os sinais de CALL e PUT detectados pelo motor de 19 gatilhos.
                    </p>
                </div>
                <div className="flex items-center gap-3 self-start mt-2">
                    {isLoading && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: '#FEF3C7', color: '#92400E' }}>
                            <Activity className="w-3 h-3 animate-spin" />
                            Carregando...
                        </span>
                    )}
                    {!isLoading && !isDemo && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: 'var(--dw-green-soft)', color: 'var(--dw-green)' }}>
                            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                            Dados ao vivo
                        </span>
                    )}
                    {!isLoading && isDemo && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: 'var(--dw-yellow)', color: '#92400E' }}>
                            Modo Demo
                        </span>
                    )}
                    {hasActiveFilters && (
                        <button onClick={clearFilters} className="btn-secondary flex items-center gap-2 text-sm">
                            <X className="w-4 h-4" /> Limpar filtros
                        </button>
                    )}
                </div>
            </div>

            {/* Banner demo */}
            {isDemo && !isLoading && (
                <div className="card mb-6" style={{ borderColor: 'var(--dw-yellow)', background: '#FFFBEB' }}>
                    <div className="flex items-center gap-3">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#D97706' }} />
                        <p className="text-sm" style={{ color: '#92400E' }}>
                            <strong>Modo Demo</strong> · O backend não encontrou sinais no último scan. Exibindo exemplos ilustrativos.
                            Use o <strong>Scanner</strong> para gerar sinais reais por ticker.
                        </p>
                    </div>
                </div>
            )}

            {/* Banner erro de conexão */}
            {isError && (
                <div className="card mb-6" style={{ borderColor: 'var(--dw-red)', background: 'var(--dw-red-soft)' }}>
                    <div className="flex items-center gap-3">
                        <Wifi className="w-4 h-4 flex-shrink-0 text-dw-red" />
                        <p className="text-sm text-dw-red">
                            Não foi possível conectar ao backend. Exibindo dados de demonstração.
                        </p>
                    </div>
                </div>
            )}

            {/* ── Filtros ─────────────────────────────────────── */}
            <div className="card mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Filter className="w-4 h-4 text-dw-ink-muted" />
                    <span className="label">Filtrar por Setor e Papel</span>
                </div>

                <div className="sector-tabs mb-4">
                    {Object.keys(SECTORS).map(sector => (
                        <button
                            key={sector}
                            onClick={() => handleSectorClick(sector)}
                            className={`sector-tab${selectedSector === sector ? ' active' : ''}`}
                        >
                            {sector}
                        </button>
                    ))}
                </div>

                <div className="stock-grid mb-5">
                    {sectorStocks.map(({ ticker, nome }) => {
                        const hasSignal = activeSignals.some((s) => s.ticker === ticker)
                        return (
                            <button
                                key={ticker}
                                onClick={() => handleTickerClick(ticker)}
                                className={`stock-card${selectedTicker === ticker ? ' active' : ''}`}
                            >
                                <span className="stock-card-ticker">{ticker}</span>
                                <span className="stock-card-name">{nome}</span>
                                {hasSignal && (
                                    <span
                                        className="mt-1.5 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full"
                                        style={{ background: 'var(--dw-green-soft)', color: 'var(--dw-green)' }}
                                    >
                                        sinal
                                    </span>
                                )}
                            </button>
                        )
                    })}
                </div>

                <div className="flex flex-wrap gap-4 pt-4 border-t border-dw-rule-soft items-end">
                    <div>
                        <label className="label block mb-1">Tipo de Sinal</label>
                        <select
                            value={tipoSinal}
                            onChange={e => setTipoSinal(e.target.value)}
                            className="bg-dw-bg-soft border border-dw-rule rounded-md px-3 py-2 text-sm text-dw-ink focus:outline-none focus:border-dw-blue transition-colors"
                        >
                            <option value="Todos">Todos</option>
                            <option value="CALL">CALL</option>
                            <option value="PUT">PUT</option>
                        </select>
                    </div>
                    <div>
                        <label className="label block mb-1">Score Mínimo</label>
                        <input
                            type="number"
                            value={minScore}
                            min={1} max={10}
                            onChange={e => setMinScore(Number(e.target.value))}
                            className="w-24 bg-dw-bg-soft border border-dw-rule rounded-md px-3 py-2 text-sm text-dw-ink focus:outline-none focus:border-dw-blue transition-colors"
                        />
                    </div>
                    {selectedTicker && (
                        <div className="flex items-end">
                            <span
                                className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-semibold"
                                style={{ background: 'var(--dw-blue-soft)', color: 'var(--dw-blue)' }}
                            >
                                {selectedTicker}
                                <button onClick={() => setSelectedTicker('')} className="ml-1 opacity-60 hover:opacity-100">
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Stats ───────────────────────────────────────── */}
            <div className="dashboard-grid mb-8">
                {[
                    { label: 'CALLs', value: String(calls), sub: 'sinais filtrados', color: 'text-dw-green' },
                    { label: 'PUTs',  value: String(puts),  sub: 'sinais filtrados', color: 'text-dw-red'   },
                    { label: 'Score Médio', value: `${avgScore}/10`, sub: 'dos sinais filtrados', color: 'text-dw-blue' },
                    { label: 'Taxa de Acerto', value: '82%', sub: 'Histórico (22 ops)', color: 'text-dw-yellow' },
                ].map(({ label, value, sub, color }) => (
                    <div key={label} className="card">
                        <span className="label">{label}</span>
                        <span className={`card-value text-2xl font-bold ${color}`}>{value}</span>
                        <span className="text-xs text-dw-ink-muted">{sub}</span>
                    </div>
                ))}
            </div>

            {/* ── Sinais ──────────────────────────────────────── */}
            <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-2xl font-bold text-dw-ink">
                    {selectedTicker
                        ? `Sinais · ${selectedTicker}`
                        : selectedSector !== 'Todos'
                        ? `Sinais · ${selectedSector}`
                        : 'Todos os Sinais'}
                </h2>
                {filtered.length > 0 && (
                    <span className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
                        style={{ background: 'var(--dw-green-soft)', color: 'var(--dw-green)' }}>
                        <Activity className="w-3 h-3" />
                        {filtered.length} {filtered.length === 1 ? 'sinal' : 'sinais'}
                    </span>
                )}
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="card animate-pulse" style={{ minHeight: 280 }}>
                            <div className="h-4 bg-dw-bg-soft rounded w-1/3 mb-3" />
                            <div className="h-3 bg-dw-bg-soft rounded w-1/2 mb-6" />
                            <div className="h-3 bg-dw-bg-soft rounded w-full mb-2" />
                            <div className="h-3 bg-dw-bg-soft rounded w-3/4" />
                        </div>
                    ))}
                </div>
            ) : filtered.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
                    {filtered.map((signal, idx) => (
                        <SignalCard key={signal.id ?? `${signal.ticker}-${idx}`} signal={signal} />
                    ))}
                </div>
            ) : (
                <div className="card text-center py-12">
                    <p className="text-dw-ink-muted mb-1">Nenhum sinal encontrado</p>
                    <p className="text-sm text-dw-ink-muted">
                        {selectedTicker
                            ? `Sem sinais para ${selectedTicker} com os filtros atuais.`
                            : 'Ajuste os filtros ou aguarde o próximo scan.'}
                    </p>
                    {hasActiveFilters && (
                        <button onClick={clearFilters} className="btn-secondary mt-4 mx-auto text-sm">
                            Limpar filtros
                        </button>
                    )}
                </div>
            )}

        </main>
    )
}
