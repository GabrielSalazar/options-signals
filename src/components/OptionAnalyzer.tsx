'use client';

import { useMemo, useState } from 'react';
import { impliedVol, calcAll } from '@/lib/black-scholes';
import type { AssetAnalysisPayload, OptionVerdict } from '@/lib/types/analytics';

const R = 0.1075; // Taxa Selic aproximada (sem live fetch)

interface Props {
  payload: AssetAnalysisPayload | null;
  onVerdict?: (v: OptionVerdict | null) => void;
}

function daysToYears(date: string): number {
  const dte = Math.max(1, Math.round((new Date(date).getTime() - Date.now()) / 86_400_000));
  return dte / 365;
}

function ivRank(iv: number, chain: AssetAnalysisPayload['chain'], S: number, T: number): number | null {
  const ivs = chain
    .filter((c) => c.negocios > 0 && c.preco > 0)
    .map((c) => impliedVol(c.preco, S, c.strike, T, R, c.tipo))
    .filter((v) => !isNaN(v));
  if (ivs.length === 0) return null;
  const below = ivs.filter((v) => v <= iv).length;
  return Math.round((below / ivs.length) * 100);
}

export function OptionAnalyzer({ payload, onVerdict }: Props) {
  const [tipo, setTipo] = useState<'call' | 'put'>('call');
  const [strikeStr, setStrikeStr] = useState('');
  const [expiryStr, setExpiryStr] = useState('');
  const [priceStr, setPriceStr] = useState('');

  const result = useMemo(() => {
    if (!payload) return null;
    const strike = parseFloat(strikeStr);
    const price  = parseFloat(priceStr);
    if (!strikeStr || !expiryStr || !priceStr) return null;
    if (isNaN(strike) || isNaN(price) || price <= 0) return null;

    const S = payload.preco_atual;
    const T = daysToYears(expiryStr);
    if (T <= 0) return null;

    const iv = impliedVol(price, S, strike, T, R, tipo);
    if (isNaN(iv)) return null;

    const fairSigma = payload.hv_20;
    const fair = tipo === 'call'
      ? calcAll(S, strike, T, fairSigma, R, 0, 'call')
      : calcAll(S, strike, T, fairSigma, R, 0, 'put');

    const bs = calcAll(S, strike, T, iv, R, 0, tipo);
    const breakEven = tipo === 'call' ? strike + price : strike - price;
    const moneynessRaw = tipo === 'call' ? ((S - strike) / strike) * 100 : ((strike - S) / strike) * 100;
    const dte = Math.round(T * 365);
    const rank = ivRank(iv, payload.chain, S, T);

    const ratio = iv / payload.hv_20;
    const verdict: OptionVerdict = ratio > 1.2 ? 'cara' : ratio < 0.8 ? 'barata' : 'neutra';

    return { iv, fair, bs, breakEven, moneynessRaw, dte, rank, verdict, fairSigma };
  }, [payload, tipo, strikeStr, expiryStr, priceStr]);

  // Notify parent
  if (onVerdict) onVerdict(result?.verdict ?? null);

  const verdictStyle: Record<OptionVerdict, { label: string; class: string }> = {
    barata: { label: '🟢 Opção Barata', class: 'bg-emerald-900/40 text-emerald-300 border-emerald-700' },
    neutra: { label: '🟡 Neutra',       class: 'bg-yellow-900/40 text-yellow-300 border-yellow-700' },
    cara:   { label: '🔴 Opção Cara',   class: 'bg-red-900/40 text-red-300 border-red-700' },
  };

  const inputCls = 'w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500';

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/60 p-5 space-y-4">
      <h3 className="text-base font-semibold text-white">Calculadora de Opção</h3>

      {!payload && (
        <p className="text-sm text-zinc-500">Analise um ativo primeiro para habilitar esta calculadora.</p>
      )}

      {payload && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Tipo</label>
              <div className="flex gap-2">
                {(['call', 'put'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTipo(t)}
                    className={`flex-1 py-2 rounded-md text-sm font-medium border transition-colors ${
                      tipo === t
                        ? 'bg-blue-700 border-blue-500 text-white'
                        : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                    }`}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Strike (R$)</label>
              <input type="number" value={strikeStr} onChange={(e) => setStrikeStr(e.target.value)} placeholder="38.00" className={inputCls} step="0.50" />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Vencimento</label>
              <input type="date" value={expiryStr} onChange={(e) => setExpiryStr(e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Prêmio de mercado (R$)</label>
              <input type="number" value={priceStr} onChange={(e) => setPriceStr(e.target.value)} placeholder="1.45" className={inputCls} step="0.01" />
            </div>
          </div>

          {result && (
            <div className="space-y-3 pt-2 border-t border-zinc-700">
              <div className={`px-3 py-2 rounded-lg border text-sm font-semibold ${verdictStyle[result.verdict].class}`}>
                {verdictStyle[result.verdict].label}
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Row label="IV calculada" value={`${(result.iv * 100).toFixed(1)}%`} />
                <Row label="HV 20d (referência)" value={`${(result.fairSigma * 100).toFixed(1)}%`} />
                <Row label="IV / HV" value={`${(result.iv / result.fairSigma).toFixed(2)}×`} highlight />
                <Row label="Preço justo BS" value={`R$ ${result.fair.price.toFixed(2)}`} />
                <Row label="Break-even vencimento" value={`R$ ${result.breakEven.toFixed(2)}`} />
                <Row label="DTE" value={`${result.dte} dias`} />
                <Row label="Moneyness" value={`${result.moneynessRaw >= 0 ? 'ITM' : 'OTM'} ${Math.abs(result.moneynessRaw).toFixed(1)}%`} />
                {result.rank !== null && <Row label="IV Rank na chain" value={`${result.rank}º percentil`} />}
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-zinc-700/50">
                <Greek label="Delta" value={result.bs.delta.toFixed(3)} />
                <Greek label="Theta/dia" value={`R$ ${result.bs.theta.toFixed(3)}`} />
                <Greek label="Vega/1%" value={`R$ ${result.bs.vega.toFixed(3)}`} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <>
      <span className="text-zinc-400">{label}</span>
      <span className={`text-right font-medium ${highlight ? 'text-blue-300' : 'text-white'}`}>{value}</span>
    </>
  );
}

function Greek({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-zinc-900/60 p-2 text-center">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}
