'use client';

import { useEffect, useMemo, useState } from 'react';
import { impliedVol, calcAll } from '@/lib/black-scholes';
import type { AssetAnalysisPayload, OptionVerdict } from '@/lib/types/analytics';

const R = 0.1075;

function thirdFriday(year: number, month: number): Date {
  const d = new Date(year, month, 1);
  const dow = d.getDay();
  const toFriday = (5 - dow + 7) % 7;
  d.setDate(1 + toFriday + 14);
  return d;
}

function nextB3Expiries(count = 6): { label: string; value: string }[] {
  const today = new Date();
  const results: { label: string; value: string }[] = [];
  let year = today.getFullYear();
  let month = today.getMonth();
  while (results.length < count) {
    const d = thirdFriday(year, month);
    if (d > today) {
      const iso = d.toISOString().split('T')[0];
      const label = d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '');
      results.push({ label, value: iso });
    }
    month++;
    if (month > 11) { month = 0; year++; }
  }
  return results;
}

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

const verdictStyle: Record<OptionVerdict, { label: string; bg: string; color: string; border: string; dot: string }> = {
  barata: { label: 'Opção Barata', bg: '#D1FAE5', color: '#065F46', border: '#6EE7B7', dot: '#10B981' },
  neutra: { label: 'Neutra',       bg: '#FEF3C7', color: '#92400E', border: '#FCD34D', dot: '#F59E0B' },
  cara:   { label: 'Opção Cara',   bg: '#FEE2E2', color: '#991B1B', border: '#FCA5A5', dot: '#EF4444' },
};

const inputStyle: React.CSSProperties = {
  width: '100%', borderRadius: 8,
  border: '1.5px solid var(--dw-rule)',
  background: 'var(--dw-white)',
  padding: '8px 12px',
  fontSize: 13,
  color: 'var(--dw-ink)',
  outline: 'none',
  boxSizing: 'border-box',
};

export function OptionAnalyzer({ payload, onVerdict }: Props) {
  const [tipo, setTipo] = useState<'call' | 'put'>('call');
  const [strikeStr, setStrikeStr] = useState('');
  const [expiryStr, setExpiryStr] = useState('');
  const [priceStr, setPriceStr] = useState('');

  const calcError = useMemo((): string | null => {
    if (!payload || !strikeStr || !expiryStr || !priceStr) return null;
    const strike = parseFloat(strikeStr);
    const price  = parseFloat(priceStr);
    if (isNaN(strike) || isNaN(price) || price <= 0) return null;
    const S = payload.preco_atual;
    const T = daysToYears(expiryStr);
    if (T <= 0) return 'Vencimento deve ser uma data futura.';
    const intrinsic = tipo === 'call'
      ? Math.max(0, S - strike)
      : Math.max(0, strike - S);
    if (price < intrinsic - 0.01) {
      return `Prêmio R$${price.toFixed(2)} abaixo do valor intrínseco (R$${intrinsic.toFixed(2)}). ` +
        `Impossível calcular IV — verifique strike ou prêmio.`;
    }
    const iv = impliedVol(price, S, strike, T, R, tipo);
    if (isNaN(iv)) return 'Não foi possível calcular IV. Ajuste os parâmetros.';
    return null;
  }, [payload, tipo, strikeStr, expiryStr, priceStr]);

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

  useEffect(() => {
    onVerdict?.(result?.verdict ?? null);
  }, [result?.verdict, onVerdict]);

  const sectionStyle: React.CSSProperties = {
    background: 'var(--dw-bg-soft)',
    border: '1px solid var(--dw-rule-soft)',
    borderRadius: 10,
    padding: 16,
  };

  return (
    <div style={{
      background: 'var(--dw-white)',
      border: '1px solid var(--dw-rule)',
      borderRadius: 12,
      padding: 20,
      boxShadow: '0 1px 4px rgba(15,17,23,0.07), 0 1px 2px rgba(15,17,23,0.04)',
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
    }}>
      <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--dw-ink)', margin: 0 }}>
        Calculadora de Opção
      </h3>

      {!payload && (
        <p style={{ fontSize: 13, color: 'var(--dw-ink-muted)', margin: 0 }}>
          Analise um ativo primeiro para habilitar esta calculadora.
        </p>
      )}

      {payload && (
        <>
          {/* Inputs */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* Tipo */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
                Tipo
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {(['call', 'put'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTipo(t)}
                    style={{
                      padding: '9px 0',
                      border: tipo === t ? `2px solid var(--dw-ink)` : '2px solid var(--dw-rule)',
                      background: tipo === t ? 'var(--dw-ink)' : 'var(--dw-white)',
                      color: tipo === t ? '#fff' : 'var(--dw-ink-mid)',
                      borderRadius: 8, fontSize: 13, fontWeight: 600,
                      cursor: 'pointer', transition: 'all 0.15s',
                    }}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Strike */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
                Strike (R$)
              </label>
              <input
                type="number" value={strikeStr}
                onChange={(e) => setStrikeStr(e.target.value)}
                placeholder="38.00" step="0.50"
                style={inputStyle}
              />
            </div>

            {/* Vencimento */}
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
                Vencimento B3 (3ª sexta)
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                {nextB3Expiries(6).map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => setExpiryStr(value)}
                    style={{
                      padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 600,
                      cursor: 'pointer', transition: 'all 0.15s',
                      border: expiryStr === value ? '2px solid var(--dw-blue)' : '1.5px solid var(--dw-rule)',
                      background: expiryStr === value ? 'var(--dw-blue-soft)' : 'var(--dw-white)',
                      color: expiryStr === value ? 'var(--dw-blue)' : 'var(--dw-ink-mid)',
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <input
                type="date" value={expiryStr}
                onChange={(e) => setExpiryStr(e.target.value)}
                style={{ ...inputStyle, fontSize: 12 }}
              />
            </div>

            {/* Prêmio */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
                Prêmio de mercado (R$)
              </label>
              <input
                type="number" value={priceStr}
                onChange={(e) => setPriceStr(e.target.value)}
                placeholder="1.45" step="0.01"
                style={inputStyle}
              />
            </div>
          </div>

          {/* Error feedback */}
          {calcError && (
            <div style={{
              padding: '10px 14px', borderRadius: 8, fontSize: 12,
              background: '#FEE2E2', color: '#991B1B',
              border: '1px solid #FCA5A5',
            }}>
              {calcError}
            </div>
          )}

          {/* Results */}
          {result && (() => {
            const vs = verdictStyle[result.verdict];
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Verdict badge */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 14px', borderRadius: 8,
                  background: vs.bg, color: vs.color, border: `1px solid ${vs.border}`,
                  fontSize: 13, fontWeight: 700,
                }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: vs.dot, display: 'inline-block' }} />
                  {vs.label}
                </div>

                {/* Metrics grid */}
                <div style={{ ...sectionStyle, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px' }}>
                  <Row label="IV calculada" value={`${(result.iv * 100).toFixed(1)}%`} />
                  <Row label="HV 20d (referência)" value={`${(result.fairSigma * 100).toFixed(1)}%`} />
                  <Row label="IV / HV" value={`${(result.iv / result.fairSigma).toFixed(2)}×`} highlight />
                  <Row label="Preço justo BS" value={
                    result.fair.price < 0.005
                      ? `R$ ${result.fair.price.toFixed(5)}`
                      : result.fair.price < 0.10
                      ? `R$ ${result.fair.price.toFixed(3)}`
                      : `R$ ${result.fair.price.toFixed(2)}`
                  } />
                  <Row label="Break-even" value={`R$ ${result.breakEven.toFixed(2)}`} />
                  <Row label="DTE" value={`${result.dte} dias`} />
                  <Row label="Moneyness" value={`${result.moneynessRaw >= 0 ? 'ITM' : 'OTM'} ${Math.abs(result.moneynessRaw).toFixed(1)}%`} />
                  {result.rank !== null && <Row label="IV Rank na chain" value={`${result.rank}º percentil`} />}
                </div>

                {/* Greeks mini */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  <GreekCard label="Delta" value={result.bs.delta.toFixed(3)} tooltip="Variação esperada no prêmio para cada R$ 1,00 de movimento no ativo. Delta 0.2 → prêmio sobe ~R$ 0,20 se o ativo subir R$ 1,00." />
                  <GreekCard label="Theta/dia" value={`R$ ${result.bs.theta.toFixed(3)}`} tooltip="Perda de valor da opção por dia de passagem do tempo (decaimento temporal). Theta −R$ 0,07 → opção perde R$ 0,07 por dia sem movimento do ativo." />
                  <GreekCard label="Vega/1%" value={`R$ ${result.bs.vega.toFixed(3)}`} tooltip="Variação no prêmio para cada 1% de mudança na volatilidade implícita. Vega R$ 0,06 → prêmio sobe R$ 0,06 se a IV aumentar 1 ponto percentual." />
                </div>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}

function FieldLabel({ text, tooltip }: { text: string; tooltip: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <span
      style={{ position: 'relative', cursor: 'help', display: 'inline-block' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {text}
      {hovered && (
        <span style={{
          position: 'absolute', bottom: 'calc(100% + 8px)', left: 0,
          background: '#1a1f3a', color: '#e8eaf6',
          fontSize: 11, lineHeight: 1.5,
          padding: '7px 11px', borderRadius: 8,
          width: 260, display: 'block', textAlign: 'left',
          boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
          pointerEvents: 'none', zIndex: 100,
          whiteSpace: 'normal', fontWeight: 400,
        }}>
          {tooltip}
          <span style={{
            position: 'absolute', top: '100%', left: 16,
            border: '6px solid transparent', borderTopColor: '#1a1f3a', display: 'block',
          }} />
        </span>
      )}
    </span>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <>
      <span style={{ fontSize: 12, color: 'var(--dw-ink-muted)' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, textAlign: 'right', color: highlight ? 'var(--dw-blue)' : 'var(--dw-ink)' }}>
        {value}
      </span>
    </>
  );
}

function GreekCard({ label, value, tooltip }: { label: string; value: string; tooltip?: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      style={{ position: 'relative', cursor: tooltip ? 'help' : undefined }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{
        background: 'rgba(59,91,219,0.08)',
        border: '1.5px solid rgba(59,91,219,0.22)',
        borderRadius: 8, padding: '10px 12px', textAlign: 'center',
      }}>
        <div style={{ fontSize: 11, color: 'var(--dw-blue)', marginBottom: 2, fontWeight: 600 }}>{label}</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--dw-blue)' }}>{value}</div>
      </div>
      {tooltip && hovered && (
        <div style={{
          position: 'absolute', bottom: 'calc(100% + 8px)', left: '50%',
          transform: 'translateX(-50%)',
          background: '#1a1f3a', color: '#e8eaf6',
          fontSize: 12, lineHeight: 1.5,
          padding: '8px 12px', borderRadius: 8,
          width: 240, textAlign: 'left',
          boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
          pointerEvents: 'none',
          zIndex: 100,
          whiteSpace: 'normal',
        }}>
          {tooltip}
          <div style={{
            position: 'absolute', top: '100%', left: '50%',
            transform: 'translateX(-50%)',
            border: '6px solid transparent',
            borderTopColor: '#1a1f3a',
          }} />
        </div>
      )}
    </div>
  );
}
