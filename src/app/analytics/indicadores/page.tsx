'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Search, ArrowLeft } from 'lucide-react';
import { useIndicators } from '@/hooks/useIndicators';
import { scoreAsset } from '@/lib/asset-analysis';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';
import { IndicatorsHeader } from '@/components/indicators/IndicatorsHeader';
import { MomentoPanel, TendenciaPanel, ReversaoPanel, VolatilidadePanel } from '@/components/indicators/IndicatorPanels';
import { SetupsGrid } from '@/components/indicators/SetupsGrid';
import { VolReadCard } from '@/components/indicators/VolReadCard';
import { ComingSoonPanel } from '@/components/indicators/ComingSoonPanel';

export default function IndicadoresPage() {
  const [input, setInput] = useState('PETR4');
  const [ticker, setTicker] = useState<string | null>(null);
  const { data, loading, error } = useIndicators(ticker);

  const analisar = useCallback(() => {
    const t = input.trim().toUpperCase();
    if (t) setTicker(t);
  }, [input]);

  const valuation = data
    ? scoreAsset({
        ticker: data.ticker,
        preco_atual: data.preco_atual,
        hv_20: data.hv_20,
        hv_60: data.hv_60,
        ma20: data.ma20,
        ma50: data.ma50,
        ma200: data.ma200,
        sigma_20: data.sigma_20,
        rsi14: data.rsi14,
        bollinger_pct_b: data.bollinger_pct_b,
        z_score_20: data.z_score_20,
        faixa_52s_min: data.faixa_52s_min,
        faixa_52s_max: data.faixa_52s_max,
        macd_diff: data.macd_diff,
        stoch_k: data.stoch_k,
        stoch_d: data.stoch_d,
        adx: data.adx,
        preco_graham: null,
        preco_dcf: null,
        chain: [],
      } as AssetAnalysisPayload).score
    : 0;

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <Link href="/analytics" className="label mb-2 inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="w-3 h-3" /> Voltar para Analytics
          </Link>
          <h1 className="font-serif">Indicadores e Setup</h1>
          <p className="mt-2 text-dw-ink-light text-base max-w-2xl">
            Leitura técnica em tempo real do ativo e de suas opções: indicadores mais usados, setups de price action e leitura de volatilidade.
          </p>
        </div>
      </div>

      <div className="card mb-6">
        <div className="label mb-3">Selecionar ativo</div>
        <div className="flex gap-3 items-center flex-wrap">
          <input
            type="text" value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && analisar()}
            placeholder="Ex: PETR4, VALE3, BBAS3"
            className="rounded-lg px-3 py-2.5 text-sm font-mono w-44 focus:outline-none focus:ring-2"
            style={{ border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)', color: 'var(--dw-ink)', '--tw-ring-color': 'var(--dw-blue)' } as React.CSSProperties}
          />
          <button onClick={analisar} disabled={loading} className="btn-demo flex items-center gap-2 disabled:opacity-50" style={{ background: 'var(--dw-blue)' }}>
            {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Search className="w-4 h-4" />}
            Analisar
          </button>
          {error && <span style={{ fontSize: 13, color: 'var(--dw-red)' }}>{error}</span>}
        </div>
      </div>

      {!ticker && (
        <div className="card flex items-center justify-center" style={{ height: 120, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
          <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>Digite um ativo para ver a leitura de mercado.</p>
        </div>
      )}

      {data && (
        <div className="card mb-6">
          <IndicatorsHeader p={data} valuationScore={valuation} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <MomentoPanel p={data} />
            <TendenciaPanel p={data} />
            <ReversaoPanel p={data} />
            <VolatilidadePanel p={data} />
          </div>
        </div>
      )}

      {data && (
        <div className="card mb-6">
          <h3 className="font-serif text-lg mb-1">Setups de Price Action</h3>
          <p className="text-xs mb-4" style={{ color: 'var(--dw-ink-muted)' }}>Estado dos setups mais usados no candle mais recente (diário).</p>
          <SetupsGrid setups={data.setups} />
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <VolReadCard p={data} />
          <ComingSoonPanel title="Fluxo de opções" itens={['Open Interest por strike', 'Max Pain', 'Put/Call ratio (OI)']} />
          <ComingSoonPanel title="Fluxo B3 · Aluguel" itens={['Taxa de aluguel (BTC)', 'Short interest / days-to-cover']} />
          <ComingSoonPanel title="Estrutura de volatilidade" itens={['IV Rank 252d', 'Estrutura a termo de IV', 'Skew 25Δ']} />
        </div>
      )}
    </div>
  );
}
