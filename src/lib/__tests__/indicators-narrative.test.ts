import { describe, it, expect } from 'vitest';
import { tendenciaLabel, momentoLabel, tecnicaLabel, volReadLabel } from '@/lib/indicators-narrative';
import type { IndicatorsPayload } from '@/lib/types/indicators';

const base: IndicatorsPayload = {
  ticker: 'PETR4', preco_atual: 41.65, hora: '15:42',
  rsi14: 17.9, stoch_k: 17, stoch_d: 11, vol_ratio: 2.3,
  ma20: 43.4, ma50: 46.2, ma200: 40.9, adx: 60.6, macd_diff: -0.18,
  bollinger_pct_b: 0.23, z_score_20: -2.1, atr14: 1.12, vwap: 41.3, vwap_dist_pct: 0.8,
  hv_20: 0.31, hv_60: 0.30, sigma_20: 0.30, expected_move: 2.8, expected_move_pct: 6.7,
  faixa_1sigma: [38.85, 44.45], dte_proximo_venc: 26, iv_atm: 0.42, iv_hv_ratio: 1.35,
  vol_read: 'premio_gordo', faixa_52s_min: 36, faixa_52s_max: 47, setups: [],
};

describe('indicators-narrative', () => {
  it('momento sobrevendido quando RSI < 30', () => {
    expect(momentoLabel(base)).toBe('sobrevendido');
  });
  it('tendência baixa forte quando ADX alto e preço abaixo das médias curtas', () => {
    expect(tendenciaLabel(base)).toBe('baixa forte');
  });
  it('técnica "faca caindo" em baixa forte + sobrevendido', () => {
    expect(tecnicaLabel(base)).toBe('faca caindo');
  });
  it('vol read favorece venda de prêmio quando prêmio gordo', () => {
    expect(volReadLabel('premio_gordo')).toContain('vender');
  });
});
