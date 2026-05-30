'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { fetchScan, getBackendUrl } from '@/lib/api';
import { BACKEND_URL } from '@/lib/config';
import { Signal } from '@/types/signals';
import SignalCard from '@/components/SignalCard';
import { AlertCircle, Search, Activity, ArrowRight, ChevronDown, ChevronUp, SlidersHorizontal, Wifi, WifiOff, Zap } from 'lucide-react';
import { Slider } from '@/components/ui/slider';

type BackendStatus = 'checking' | 'waking' | 'online' | 'offline';

// Universo completo de ativos B3 com opções líquidas (~90 tickers)
const ALL_B3_TICKERS = [
    // Petróleo & Gás
    'PETR4','PETR3','PRIO3','RRRP3','RECV3','CSAN3',
    // Mineração & Siderurgia
    'VALE3','CSNA3','GGBR4','GGBR3','USIM5','CMIN3','GOAU4',
    // Financeiro & Bancos
    'ITUB4','ITUB3','BBDC4','BBDC3','BBAS3','SANB11','BPAC11','B3SA3','IRBR3','PSSA3','BBSE3',
    // Seguros
    'SULA11','CXSE3',
    // Varejo
    'MGLU3','LREN3','SOMA3','AMER3','ALPA4','LWSA3',
    // Energia Elétrica
    'EGIE3','TAEE11','ENGI11','CMIG4','CPFE3','SBSP3','ELET3','ELET6','TRPL4','AURE3','ENEV3','CPLE6',
    // Industrial & Bens de Capital
    'WEGE3','EMBR3','RAIL3','MOVI3','RENT3','RAPT4','POMO4',
    // Consumo & Alimentos
    'ABEV3','BRFS3','JBSS3','MRFG3','SMTO3','BEEF3','SLCE3',
    // Telecom
    'VIVT3','TIMS3',
    // Saúde
    'RDOR3','HAPV3','DASA3','FLRY3','QUAL3',
    // Imobiliário & Construção
    'MRVE3','CYRE3','EVEN3','EZTC3','TEND3',
    // Educação
    'COGN3','YDUQ3',
    // Papel & Celulose
    'SUZB3','KLBN11','DXCO3',
    // Transporte & Logística
    'AZUL4','GOLL4','ECOR3',
    // Tech & Serviços
    'TOTVS3',
];

const WAKE_TIMEOUT_S = 90;
const HEALTH_RETRY_INTERVAL_S = 6;

const DEMO_SIGNALS: Signal[] = [
    {
        ticker: 'PETR4', nome: 'Petrobras PN', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 37.50, ticker_opcao: 'PETRF380', strike_ref: 39.38, dist_otm_pct: 5, iv_hist: 32.5, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.45, preco_tela: 0.43, entrada_min: 0.40, entrada_max: 0.50,
        alvo1: 0.56, alvo2: 1.13, alvo_final: 2.25, stop: 0.26, rr_alvo1: 0.8, rr_alvo2: 1.51,
        rr_final: 3.96, score: 8, stoch_k: 22.5, rsi: 32.1, vol_ratio: 1.8,
        gatilhos: ['📈 Estocástico: cruzamento altista em sobrevenda', '📈 RSI sobrevenda: 32.1', '📈 Preço em suporte 20D: R$36.50', '📈 EMA9 cruzou acima EMA21'],
    },
    {
        ticker: 'VALE3', nome: 'Vale', tipo_sinal: 'PUT', direcao: 'COMPRA DE PUT',
        preco_acao: 68.20, ticker_opcao: 'VALEP645', strike_ref: 64.59, dist_otm_pct: 5, iv_hist: 28.2, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.38, preco_tela: 0.36, entrada_min: 0.34, entrada_max: 0.42,
        alvo1: 0.47, alvo2: 0.95, alvo_final: 1.90, stop: 0.22, rr_alvo1: 0.68, rr_alvo2: 1.92,
        rr_final: 3.93, score: 7, stoch_k: 78.5, rsi: 68.3, vol_ratio: 1.6,
        gatilhos: ['📉 Estocástico: cruzamento baixista em sobrecompra', '📉 RSI sobrecompra: 68.3', '📉 Preço em resistência 20D'],
    },
    {
        ticker: 'MGLU3', nome: 'Magazine Luiza', tipo_sinal: 'CALL', direcao: 'COMPRA DE CALL',
        preco_acao: 9.85, ticker_opcao: 'MGLUF109', strike_ref: 10.95, dist_otm_pct: 11, iv_hist: 42.1, dte: 21,
        mes_venc: 6, ano_venc: 2026, premio_est: 0.32, preco_tela: 0.31, entrada_min: 0.29, entrada_max: 0.35,
        alvo1: 0.40, alvo2: 0.80, alvo_final: 1.60, stop: 0.19, rr_alvo1: 0.91, rr_alvo2: 2.27,
        rr_final: 4.82, score: 9, stoch_k: 18.2, rsi: 28.9, vol_ratio: 2.1,
        gatilhos: ['📈 Estocástico: cruzamento altista em sobrevenda', '📈 RSI sobrevenda: 28.9', '📈 Volume 2.1x acima da média', '📈 Divergência altista RSI'],
    },
];

export default function ScannerPage() {
    const [ticker, setTicker] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<Signal[]>([]);
    const [error, setError] = useState('');
    const [searchedTicker, setSearchedTicker] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [isBatchScan, setIsBatchScan] = useState(false);
    const [sseProgress, setSseProgress] = useState({ completed: 0, total: 0, lastTicker: '' });

    const [minVolume, setMinVolume] = useState(0);
    const [minDTE, setMinDTE] = useState(5);
    const [maxDTE, setMaxDTE] = useState(60);
    const [minConfidence, setMinConfidence] = useState(50);
    const [minDelta, setMinDelta] = useState(0.10);
    const [maxDelta, setMaxDelta] = useState(0.90);

    const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
    const [wakeElapsed, setWakeElapsed] = useState(0);
    const [justCameOnline, setJustCameOnline] = useState(false);

    const elapsedRef = useRef(0);
    const elapsedIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const mountedRef = useRef(true);
    const esRef = useRef<EventSource | null>(null);

    const clearTimers = () => {
        if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
        if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
    };

    const checkHealth = useCallback(async (): Promise<boolean> => {
        try {
            const controller = new AbortController();
            const t = setTimeout(() => controller.abort(), 4000);
            const res = await fetch(`${BACKEND_URL}/health`, { 
                signal: controller.signal,
                cache: 'no-store' 
            });
            clearTimeout(t);
            return res.ok;
        } catch {
            return false;
        }
    }, []);

    const startWaking = useCallback(() => {
        if (!mountedRef.current) return;
        setBackendStatus('waking');
        elapsedRef.current = 0;

        elapsedIntervalRef.current = setInterval(() => {
            if (!mountedRef.current) return;
            elapsedRef.current += 1;
            setWakeElapsed(elapsedRef.current);
            if (elapsedRef.current >= WAKE_TIMEOUT_S) {
                clearTimers();
                setBackendStatus('offline');
            }
        }, 1000);

        const retry = async () => {
            if (!mountedRef.current || elapsedRef.current >= WAKE_TIMEOUT_S) return;
            const alive = await checkHealth();
            if (!mountedRef.current) return;
            if (alive) {
                clearTimers();
                setBackendStatus('online');
                setJustCameOnline(true);
                setTimeout(() => setJustCameOnline(false), 3000);
            } else {
                retryTimeoutRef.current = setTimeout(retry, HEALTH_RETRY_INTERVAL_S * 1000);
            }
        };

        retryTimeoutRef.current = setTimeout(retry, HEALTH_RETRY_INTERVAL_S * 1000);
    }, [checkHealth]);

    useEffect(() => {
        mountedRef.current = true;
        checkHealth().then((alive) => {
            if (!mountedRef.current) return;
            if (alive) setBackendStatus('online');
            else startWaking();
        });
        return () => {
            mountedRef.current = false;
            clearTimers();
            if (esRef.current) { esRef.current.close(); esRef.current = null; }
        };
    }, [checkHealth, startWaking]);

    const retryWake = () => {
        clearTimers();
        setWakeElapsed(0);
        elapsedRef.current = 0;
        setBackendStatus('checking');
        checkHealth().then((alive) => {
            if (!mountedRef.current) return;
            if (alive) setBackendStatus('online');
            else startWaking();
        });
    };

    const handleScan = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (backendStatus !== 'online') return;

        // Close any existing SSE
        if (esRef.current) { esRef.current.close(); esRef.current = null; }

        setLoading(true);
        setError('');
        setResults([]);
        setSearchedTicker('');
        const isBatch = !ticker.trim();
        setIsBatchScan(isBatch);

        if (isBatch) {
            // ── Batch scan via SSE stream ────────────────────────────────
            setSseProgress({ completed: 0, total: ALL_B3_TICKERS.length, lastTicker: '' });
            const backendUrl = getBackendUrl();
            const tickersParam = ALL_B3_TICKERS.join(',');
            const es = new EventSource(`${backendUrl}/signals/scan/stream?tickers=${tickersParam}`);
            esRef.current = es;
            const accumulated: Signal[] = [];

            es.onmessage = (event) => {
                if (!mountedRef.current) { es.close(); return; }
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'progress') {
                        setSseProgress({ completed: data.completed, total: data.total, lastTicker: data.ticker });
                        if (data.has_signal && data.signal) {
                            accumulated.push(data.signal);
                            setResults([...accumulated]);
                        }
                    } else if (data.type === 'done') {
                        es.close();
                        esRef.current = null;
                        setLoading(false);
                        setSearchedTicker(`${ALL_B3_TICKERS.length} ativos B3`);
                        if (accumulated.length === 0) {
                            setError(`Nenhum sinal encontrado nos ${ALL_B3_TICKERS.length} tickers com os critérios atuais.`);
                        }
                    }
                } catch {
                    // ignore parse errors
                }
            };

            es.onerror = () => {
                es.close();
                esRef.current = null;
                if (!mountedRef.current) return;
                setLoading(false);
                if (accumulated.length === 0) setError('Erro na conexão com o backend. Tente novamente.');
            };
        } else {
            // ── Single ticker scan ────────────────────────────────────────
            try {
                const data = await fetchScan(ticker.trim(), {
                    min_dte: minDTE, max_dte: maxDTE, min_delta: minDelta, max_delta: maxDelta,
                });
                const signal = data.sinal;
                if (signal) {
                    setResults([signal]);
                    setSearchedTicker(ticker.trim().toUpperCase());
                } else {
                    setResults([]);
                    setSearchedTicker(ticker.trim().toUpperCase());
                    setError(`Nenhum sinal encontrado para ${ticker.trim().toUpperCase()} com as estratégias atuais.`);
                }
            } catch (err: any) {
                setError(err.response?.data?.detail || err.message || 'Falha ao escanear.');
            } finally {
                setLoading(false);
            }
        }
    };

    const progressPct = Math.min((wakeElapsed / WAKE_TIMEOUT_S) * 100, 100);
    const ssePct = sseProgress.total > 0 ? Math.round((sseProgress.completed / sseProgress.total) * 100) : 0;
    const isDisabled = loading || backendStatus === 'checking' || backendStatus === 'waking' || backendStatus === 'offline';

    return (
        <main className="main-content">
            <div className="page-header">
                <div>
                    <h1 className="font-serif">Opportunity Scanner</h1>
                    <p className="mt-2 text-dw-ink-light text-lg">
                        Scan em tempo real para High IV, RSI Reversions e Gamma Squeezes em opções da B3.
                    </p>
                </div>
                <div className="flex items-center gap-2 self-start mt-2">
                    {backendStatus === 'online' && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: 'var(--dw-green-soft)', color: 'var(--dw-green)' }}>
                            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                            Backend online
                        </span>
                    )}
                    {(backendStatus === 'checking' || backendStatus === 'waking') && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: '#FEF3C7', color: '#92400E' }}>
                            <Activity className="w-3 h-3 animate-spin" />
                            Acordando...
                        </span>
                    )}
                    {backendStatus === 'offline' && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: 'var(--dw-red-soft)', color: 'var(--dw-red)' }}>
                            <WifiOff className="w-3 h-3" />
                            Offline
                        </span>
                    )}
                </div>
            </div>

            {/* ── Wake-up banners ──────────────────────────────── */}
            {backendStatus === 'checking' && (
                <div className="card mb-6" style={{ borderColor: '#FCD34D', borderWidth: '1.5px' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: '#FEF3C7' }}>
                            <Wifi className="w-5 h-5" style={{ color: '#92400E' }} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold" style={{ color: '#92400E' }}>Verificando backend...</p>
                            <p className="text-xs text-dw-ink-muted">Conectando ao servidor FastAPI</p>
                        </div>
                        <Activity className="w-4 h-4 animate-spin ml-auto text-dw-ink-muted" />
                    </div>
                </div>
            )}

            {backendStatus === 'waking' && (
                <div className="card mb-6" style={{ borderColor: '#FCD34D', borderWidth: '1.5px' }}>
                    <div className="flex items-start gap-4">
                        <div className="w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: '#FEF3C7' }}>
                            <Zap className="w-5 h-5" style={{ color: '#D97706' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                                <p className="text-sm font-semibold" style={{ color: '#92400E' }}>Backend acordando...</p>
                                <span className="font-mono text-sm font-bold" style={{ color: '#D97706' }}>{wakeElapsed}s</span>
                            </div>
                            <p className="text-xs text-dw-ink-muted mb-3">
                                O Render free tier hiberna após 15 min. O servidor leva ~45s para iniciar. Tentando a cada {HEALTH_RETRY_INTERVAL_S}s.
                            </p>
                            <div className="w-full h-1.5 rounded-full" style={{ background: 'var(--dw-bg-soft)' }}>
                                <div className="h-1.5 rounded-full transition-all duration-1000" style={{ width: `${progressPct}%`, background: '#F59E0B' }} />
                            </div>
                            <p className="text-[10px] text-dw-ink-muted mt-1.5 text-right">{Math.max(0, WAKE_TIMEOUT_S - wakeElapsed)}s restantes até timeout</p>
                        </div>
                    </div>
                </div>
            )}

            {backendStatus === 'offline' && (
                <>
                    <div className="card mb-4" style={{ borderColor: 'var(--dw-red)', borderWidth: '1.5px' }}>
                        <div className="flex items-center gap-4">
                            <div className="w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'var(--dw-red-soft)' }}>
                                <WifiOff className="w-5 h-5 text-dw-red" />
                            </div>
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-dw-red">Backend offline</p>
                                <p className="text-xs text-dw-ink-muted">Não foi possível conectar após {WAKE_TIMEOUT_S}s.</p>
                            </div>
                            <button onClick={retryWake} className="btn-secondary text-sm flex-shrink-0">Tentar novamente</button>
                        </div>
                    </div>
                    <div className="card mb-6" style={{ borderColor: 'var(--dw-yellow)', background: '#FFFBEB' }}>
                        <div className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4" style={{ color: '#D97706' }} />
                            <p className="text-sm font-semibold" style={{ color: '#92400E' }}>Modo Demo · Sinais de exemplo</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                        {DEMO_SIGNALS.map((signal) => (
                            <SignalCard key={signal.ticker} signal={signal} />
                        ))}
                    </div>
                </>
            )}

            {justCameOnline && (
                <div className="card mb-6" style={{ borderColor: 'var(--dw-green)', borderWidth: '1.5px', background: 'var(--dw-green-soft)' }}>
                    <div className="flex items-center gap-3">
                        <Wifi className="w-5 h-5 text-dw-green" />
                        <p className="text-sm font-semibold" style={{ color: 'var(--dw-green)' }}>Backend online! Pode escanear agora.</p>
                    </div>
                </div>
            )}

            {/* ── Scan Form ──────────────────────────────────── */}
            <div className="card mb-8">
                <div className="flex items-center gap-2 mb-4">
                    <Search className="w-5 h-5 text-dw-blue" />
                    <h3 className="font-serif">Novo Scan</h3>
                </div>
                <form onSubmit={handleScan} className="space-y-6">
                    <div className="flex flex-col sm:flex-row gap-4 items-end">
                        <div className="w-full sm:w-1/3">
                            <label className="block text-sm font-semibold text-dw-ink-mid mb-1">
                                Ticker{' '}
                                <span className="font-normal text-dw-ink-muted">
                                    {ticker.trim() ? '— scan individual' : `— vazio = todos os ${ALL_B3_TICKERS.length} ativos B3`}
                                </span>
                            </label>
                            <input
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                placeholder={`Vazio = scan completo (${ALL_B3_TICKERS.length} ativos)`}
                                className="w-full bg-dw-bg-soft border border-dw-rule rounded-md px-3 py-2 font-mono text-lg uppercase tracking-wider text-dw-ink focus:outline-none focus:border-dw-blue transition-colors"
                            />
                            {!ticker.trim() && backendStatus === 'online' && (
                                <p className="text-[10px] text-dw-ink-muted mt-1">
                                    Resultados aparecem em tempo real · estimativa 30–90s
                                </p>
                            )}
                        </div>
                        <button type="button" onClick={() => setShowFilters(!showFilters)} className="btn-secondary flex items-center gap-2">
                            <SlidersHorizontal className="w-4 h-4" />
                            Filtros {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                        <button
                            type="submit"
                            disabled={isDisabled}
                            className="btn-demo flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            style={{ background: isDisabled ? undefined : 'var(--dw-blue)' }}
                        >
                            {loading && isBatchScan ? (
                                <><Activity className="w-4 h-4 animate-spin" /> {ssePct}% ({sseProgress.completed}/{sseProgress.total})</>
                            ) : loading ? (
                                <><Activity className="w-4 h-4 animate-spin" /> Scanning...</>
                            ) : backendStatus === 'checking' ? (
                                <><Activity className="w-4 h-4 animate-spin" /> Verificando...</>
                            ) : backendStatus === 'waking' ? (
                                <><Activity className="w-4 h-4 animate-spin" /> Aguarde ({wakeElapsed}s)</>
                            ) : ticker.trim() ? (
                                <>Scan {ticker} <ArrowRight className="w-4 h-4" /></>
                            ) : (
                                <>Scan B3 Completo <ArrowRight className="w-4 h-4" /></>
                            )}
                        </button>
                    </div>

                    {showFilters && (
                        <div className="pt-4 border-t border-dw-rule-soft grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <label className="label">Volume Mínimo</label>
                                    <span className="text-xs font-mono text-dw-blue">{minVolume.toLocaleString()}</span>
                                </div>
                                <Slider value={[minVolume]} onValueChange={(v) => setMinVolume(v[0])} max={5000} step={100} className="py-2" />
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <label className="label">DTE (dias)</label>
                                    <span className="text-xs font-mono text-dw-blue">{minDTE}–{maxDTE}</span>
                                </div>
                                <div className="flex gap-3">
                                    <div className="flex-1">
                                        <label className="text-[10px] text-dw-ink-muted">Mín</label>
                                        <input type="number" value={minDTE} onChange={(e) => setMinDTE(parseInt(e.target.value))} className="w-full h-8 bg-dw-bg-soft border border-dw-rule rounded px-2 text-xs text-dw-ink" />
                                    </div>
                                    <div className="flex-1">
                                        <label className="text-[10px] text-dw-ink-muted">Máx</label>
                                        <input type="number" value={maxDTE} onChange={(e) => setMaxDTE(parseInt(e.target.value))} className="w-full h-8 bg-dw-bg-soft border border-dw-rule rounded px-2 text-xs text-dw-ink" />
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <label className="label">Confiança Mínima</label>
                                    <span className="text-xs font-mono text-dw-blue">{minConfidence}%</span>
                                </div>
                                <Slider value={[minConfidence]} onValueChange={(v) => setMinConfidence(v[0])} max={100} step={5} className="py-2" />
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <label className="label">Delta Range</label>
                                    <span className="text-xs font-mono text-dw-blue">{minDelta.toFixed(2)}–{maxDelta.toFixed(2)}</span>
                                </div>
                                <div className="flex gap-3">
                                    <div className="flex-1">
                                        <label className="text-[10px] text-dw-ink-muted">Mín</label>
                                        <input type="number" step="0.05" value={minDelta} onChange={(e) => setMinDelta(parseFloat(e.target.value))} className="w-full h-8 bg-dw-bg-soft border border-dw-rule rounded px-2 text-xs text-dw-ink" />
                                    </div>
                                    <div className="flex-1">
                                        <label className="text-[10px] text-dw-ink-muted">Máx</label>
                                        <input type="number" step="0.05" value={maxDelta} onChange={(e) => setMaxDelta(parseFloat(e.target.value))} className="w-full h-8 bg-dw-bg-soft border border-dw-rule rounded px-2 text-xs text-dw-ink" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </form>

                {/* SSE progress bar */}
                {loading && isBatchScan && sseProgress.total > 0 && (
                    <div className="mt-4 pt-4 border-t border-dw-rule-soft">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-dw-ink-muted">
                                Analisando{sseProgress.lastTicker ? ` · ${sseProgress.lastTicker}` : '...'}
                            </span>
                            <span className="text-xs font-mono font-bold text-dw-blue">
                                {sseProgress.completed}/{sseProgress.total}
                            </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-dw-bg-soft">
                            <div
                                className="h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${ssePct}%`, background: 'var(--dw-blue)' }}
                            />
                        </div>
                        {results.length > 0 && (
                            <p className="text-xs text-dw-green mt-1">{results.length} sinal(is) encontrado(s) até agora</p>
                        )}
                    </div>
                )}
            </div>

            {error && (
                <div className="p-4 bg-red-50 border border-red-100 rounded-lg flex items-center gap-3 text-dw-red mb-6">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <p className="text-sm">{error}</p>
                </div>
            )}

            {results.length > 0 && (
                <div className="space-y-6">
                    <div className="flex items-center gap-2 text-dw-green bg-emerald-50 w-fit px-4 py-1.5 rounded-full border border-emerald-100 text-sm font-semibold">
                        <Activity className="w-4 h-4" />
                        {results.length} {results.length === 1 ? 'oportunidade' : 'oportunidades'}
                        {searchedTicker ? ` em ${searchedTicker}` : ''}
                        {loading && isBatchScan && ' · scan em andamento...'}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.map((signal, idx) => (
                            <SignalCard key={`${signal.ticker}-${idx}`} signal={signal} />
                        ))}
                    </div>
                </div>
            )}
        </main>
    );
}
