'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  Bell, RefreshCcw, Download, Plus, Trash2, X,
} from 'lucide-react';
import { fetchSignalHistory } from '@/lib/api';
import { Signal } from '@/types/signals';

// ── Alert Rules ──────────────────────────────────────────────────────────────

interface AlertRule {
  id: string;
  ticker: string;
  tipo_sinal: 'CALL' | 'PUT' | '';
  min_score: number;
}

const RULES_KEY = 'b3_alert_rules_v1';

function loadRules(): AlertRule[] {
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem(RULES_KEY) || '[]'); }
  catch { return []; }
}
function saveRules(rules: AlertRule[]) {
  localStorage.setItem(RULES_KEY, JSON.stringify(rules));
}
function ruleMatches(rule: AlertRule, s: Signal): boolean {
  return (
    (!rule.ticker || s.ticker === rule.ticker.toUpperCase()) &&
    (!rule.tipo_sinal || s.tipo_sinal === rule.tipo_sinal) &&
    s.score >= rule.min_score
  );
}

// ── CSV export ────────────────────────────────────────────────────────────────

function exportCSV(signals: Signal[]) {
  const headers = ['Horário', 'Ticker', 'Tipo', 'Direção', 'Score', 'Preço Ação', 'Strike', 'DTE', 'IV Hist%', 'RR Alvo1', 'Premio Est'];
  const rows = signals.map((s) => [
    new Date(s.timestamp || s.created_at || '').toLocaleString('pt-BR'),
    s.ticker,
    s.tipo_sinal,
    s.direcao,
    s.score,
    s.preco_acao?.toFixed(2) ?? '',
    s.strike_ref?.toFixed(2) ?? '',
    s.dte ?? '',
    s.iv_hist?.toFixed(1) ?? '',
    s.rr_alvo1?.toFixed(2) ?? '',
    s.premio_est?.toFixed(2) ?? '',
  ].join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sinais_b3_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterTicker, setFilterTicker] = useState('');
  const [filterTipo, setFilterTipo] = useState<'CALL' | 'PUT' | ''>('');
  const [filterScore, setFilterScore] = useState(0);
  const [filterDays, setFilterDays] = useState(30);

  // Rules
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [newRule, setNewRule] = useState<Omit<AlertRule, 'id'>>({ ticker: '', tipo_sinal: '', min_score: 6 });

  useEffect(() => { setRules(loadRules()); }, []);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSignalHistory(200);
      setSignals(data);
    } catch {
      setError('Falha ao carregar histórico. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadHistory(); }, []);

  // Client-side filtering
  const cutoff = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - filterDays);
    return d;
  }, [filterDays]);

  const filtered = useMemo(() => signals.filter((s) => {
    if (filterTicker && !s.ticker.includes(filterTicker.toUpperCase())) return false;
    if (filterTipo && s.tipo_sinal !== filterTipo) return false;
    if (s.score < filterScore) return false;
    const ts = s.timestamp || s.created_at;
    if (ts && new Date(ts) < cutoff) return false;
    return true;
  }), [signals, filterTicker, filterTipo, filterScore, cutoff]);

  // Rule match counts
  const matchCounts = useMemo(() =>
    rules.map((rule) => signals.filter((s) => ruleMatches(rule, s)).length),
    [rules, signals],
  );
  const totalMatches = matchCounts.reduce((a, b) => a + b, 0);

  const addRule = () => {
    const rule: AlertRule = { ...newRule, id: Date.now().toString() };
    const updated = [...rules, rule];
    setRules(updated);
    saveRules(updated);
    setNewRule({ ticker: '', tipo_sinal: '', min_score: 60 });
    setShowRuleForm(false);
  };

  const deleteRule = (id: string) => {
    const updated = rules.filter((r) => r.id !== id);
    setRules(updated);
    saveRules(updated);
  };

  const pillStyle = (tipo: string): { bg: string; color: string } => {
    if (tipo === 'CALL') return { bg: 'var(--dw-green-soft)', color: 'var(--dw-green)' };
    if (tipo === 'PUT')  return { bg: 'var(--dw-red-soft)',   color: 'var(--dw-red)'   };
    return                       { bg: 'var(--dw-blue-soft)',  color: 'var(--dw-blue)'  };
  };

  return (
    <main className="main-content">
      {/* Header */}
      <div className="page-header">
        <div className="flex items-center gap-3">
          <Bell className="h-8 w-8" style={{ color: 'var(--dw-blue)' }} />
          <div>
            <h1 className="font-serif">Central de Alertas</h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--dw-ink-muted)' }}>
              Regras configuráveis + histórico de sinais com filtros
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => exportCSV(filtered)}
            disabled={filtered.length === 0}
            className="btn-secondary flex items-center gap-2 disabled:opacity-40"
          >
            <Download className="h-4 w-4" />
            Exportar CSV
          </button>
          <button onClick={loadHistory} disabled={loading} className="btn-secondary flex items-center gap-2">
            <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* ── Regras de Alerta ─────────────────────────────────────────────── */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="label">Minhas Regras de Alerta</div>
            {totalMatches > 0 && (
              <span className="ct-pill blue">{totalMatches} sinais hoje</span>
            )}
          </div>
          <button
            onClick={() => setShowRuleForm(!showRuleForm)}
            className="btn-secondary flex items-center gap-1.5 text-xs"
          >
            {showRuleForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            {showRuleForm ? 'Cancelar' : 'Nova Regra'}
          </button>
        </div>

        {/* Formulário de nova regra */}
        {showRuleForm && (
          <div className="rounded-xl p-4 mb-4 flex flex-wrap gap-3 items-end"
            style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>
                Ticker (vazio = todos)
              </label>
              <input
                type="text"
                value={newRule.ticker}
                onChange={(e) => setNewRule({ ...newRule, ticker: e.target.value.toUpperCase() })}
                placeholder="Ex: PETR4"
                className="rounded-lg px-3 py-2 text-sm font-mono w-28 focus:outline-none"
                style={{ border: '1.5px solid var(--dw-rule)', background: 'white', color: 'var(--dw-ink)' }}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>Tipo</label>
              <select
                value={newRule.tipo_sinal}
                onChange={(e) => setNewRule({ ...newRule, tipo_sinal: e.target.value as AlertRule['tipo_sinal'] })}
                className="rounded-lg px-3 py-2 text-sm focus:outline-none"
                style={{ border: '1.5px solid var(--dw-rule)', background: 'white', color: 'var(--dw-ink)' }}
              >
                <option value="">Qualquer</option>
                <option value="CALL">CALL</option>
                <option value="PUT">PUT</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--dw-ink-mid)' }}>
                Score mínimo: <strong>{newRule.min_score}/10</strong>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={newRule.min_score}
                onChange={(e) => setNewRule({ ...newRule, min_score: Number(e.target.value) })}
                className="w-32"
                style={{ accentColor: 'var(--dw-blue)' }}
              />
            </div>
            <button
              onClick={addRule}
              className="btn-demo flex items-center gap-1.5 text-sm"
              style={{ background: 'var(--dw-blue)' }}
            >
              <Plus className="h-4 w-4" />
              Criar
            </button>
          </div>
        )}

        {/* Lista de regras */}
        {rules.length === 0 ? (
          <p className="text-sm py-2" style={{ color: 'var(--dw-ink-muted)' }}>
            Nenhuma regra criada. Clique em &quot;Nova Regra&quot; para definir condições de alerta.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {rules.map((rule, i) => (
              <div
                key={rule.id}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
                style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}
              >
                <span className="font-mono font-bold" style={{ color: 'var(--dw-ink)' }}>
                  {rule.ticker || 'Todos'}
                </span>
                {rule.tipo_sinal && (() => {
                  const ps = pillStyle(rule.tipo_sinal);
                  return (
                    <span
                      className="text-xs font-semibold px-1.5 py-0.5 rounded"
                      style={{ background: ps.bg, color: ps.color }}
                    >
                      {rule.tipo_sinal}
                    </span>
                  );
                })()}
                <span className="text-xs" style={{ color: 'var(--dw-ink-muted)' }}>
                  Score ≥ {rule.min_score}
                </span>
                <span className="ct-pill blue text-xs">{matchCounts[i]} sinais</span>
                <button onClick={() => deleteRule(rule.id)} style={{ color: 'var(--dw-ink-muted)' }}>
                  <Trash2 className="h-3.5 w-3.5 hover:text-dw-red" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Filtros ──────────────────────────────────────────────────────── */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* Ticker search */}
          <input
            type="text"
            value={filterTicker}
            onChange={(e) => setFilterTicker(e.target.value)}
            placeholder="Filtrar ticker..."
            className="rounded-lg px-3 py-2 text-sm font-mono w-36 focus:outline-none"
            style={{ border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)', color: 'var(--dw-ink)' }}
          />

          {/* Tipo toggle */}
          <div className="flex rounded-lg overflow-hidden" style={{ border: '1px solid var(--dw-rule)' }}>
            {(['', 'CALL', 'PUT'] as const).map((t) => (
              <button
                key={t || 'all'}
                onClick={() => setFilterTipo(t)}
                className="px-3 py-1.5 text-xs font-semibold transition-colors"
                style={{
                  background: filterTipo === t ? 'var(--dw-blue)' : 'var(--dw-bg-soft)',
                  color: filterTipo === t ? 'white' : 'var(--dw-ink-mid)',
                }}
              >
                {t || 'Todos'}
              </button>
            ))}
          </div>

          {/* Score mínimo */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold" style={{ color: 'var(--dw-ink-mid)' }}>Score ≥</span>
            {[0, 5, 7, 9].map((v) => (
              <button
                key={v}
                onClick={() => setFilterScore(v)}
                className="px-2.5 py-1 text-xs rounded-lg font-mono font-semibold transition-colors"
                style={{
                  background: filterScore === v ? 'var(--dw-blue)' : 'var(--dw-bg-soft)',
                  color: filterScore === v ? 'white' : 'var(--dw-ink-mid)',
                  border: '1px solid var(--dw-rule)',
                }}
              >
                {v || 'Todos'}
              </button>
            ))}
          </div>

          {/* Período */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold" style={{ color: 'var(--dw-ink-mid)' }}>Período</span>
            {[1, 7, 30].map((d) => (
              <button
                key={d}
                onClick={() => setFilterDays(d)}
                className="px-2.5 py-1 text-xs rounded-lg font-semibold transition-colors"
                style={{
                  background: filterDays === d ? 'var(--dw-blue)' : 'var(--dw-bg-soft)',
                  color: filterDays === d ? 'white' : 'var(--dw-ink-mid)',
                  border: '1px solid var(--dw-rule)',
                }}
              >
                {d === 1 ? 'Hoje' : d === 7 ? '7d' : '30d'}
              </button>
            ))}
          </div>

          <span className="text-xs ml-auto" style={{ color: 'var(--dw-ink-muted)' }}>
            {filtered.length} de {signals.length} sinais
          </span>
        </div>
      </div>

      {/* ── Tabela ───────────────────────────────────────────────────────── */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead style={{ borderBottom: '1px solid var(--dw-rule)' }}>
              <tr>
                {['Horário', 'Ticker', 'Tipo', 'Direção', 'Score', 'Preço', 'Strike', 'DTE', 'IV%', 'RR'].map((h) => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--dw-ink-muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={10} className="text-center py-8">
                    <RefreshCcw className="h-5 w-5 animate-spin inline-block mr-2" style={{ color: 'var(--dw-blue)' }} />
                    <span style={{ color: 'var(--dw-ink-muted)' }}>Carregando...</span>
                  </td>
                </tr>
              )}
              {error && (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-sm" style={{ color: 'var(--dw-red)' }}>{error}</td>
                </tr>
              )}
              {!loading && !error && filtered.length === 0 && (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-sm" style={{ color: 'var(--dw-ink-muted)' }}>
                    Nenhum sinal encontrado com estes filtros.
                  </td>
                </tr>
              )}
              {!loading && !error && filtered.map((s, idx) => {
                const isRuleMatch = rules.some((r) => ruleMatches(r, s));
                return (
                  <tr
                    key={`${s.ticker}-${s.timestamp}-${idx}`}
                    style={{
                      borderBottom: '1px solid var(--dw-rule)',
                      background: isRuleMatch ? 'var(--dw-blue-soft)' : undefined,
                    }}
                    className="hover:bg-dw-bg-soft transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-xs" style={{ color: 'var(--dw-ink-muted)' }}>
                      {new Date(s.timestamp || s.created_at || '').toLocaleString('pt-BR')}
                    </td>
                    <td className="px-4 py-3 font-bold font-mono" style={{ color: 'var(--dw-ink)' }}>
                      {s.ticker}
                      {isRuleMatch && <span className="ml-1 text-xs" style={{ color: 'var(--dw-blue)' }}>●</span>}
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const ps = pillStyle(s.tipo_sinal);
                        return (
                          <span
                            className="text-xs font-semibold px-2 py-0.5 rounded"
                            style={{ background: ps.bg, color: ps.color }}
                          >
                            {s.tipo_sinal}
                          </span>
                        );
                      })()}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--dw-ink-mid)' }}>{s.direcao}</td>
                    <td className="px-4 py-3 font-mono font-semibold" style={{ color: 'var(--dw-ink)' }}>
                      {s.score}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--dw-ink-mid)' }}>
                      R$ {s.preco_acao?.toFixed(2) ?? '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--dw-ink-mid)' }}>
                      {s.strike_ref?.toFixed(2) ?? '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--dw-ink-mid)' }}>
                      {s.dte ?? '—'}d
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--dw-ink-mid)' }}>
                      {s.iv_hist?.toFixed(1) ?? '—'}%
                    </td>
                    <td className="px-4 py-3 font-mono text-xs font-semibold" style={{ color: 'var(--dw-green)' }}>
                      {s.rr_alvo1?.toFixed(2) ?? '—'}x
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
