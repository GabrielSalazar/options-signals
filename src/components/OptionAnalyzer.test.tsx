import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { OptionAnalyzer } from './OptionAnalyzer';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';

const mockPayload: AssetAnalysisPayload = {
  ticker: 'PETR4',
  preco_atual: 38.0,
  hv_20: 0.3,
  hv_60: 0.28,
  ma20: 37.5,
  ma50: 36.0,
  ma200: 35.0,
  sigma_20: 0.3,
  rsi14: 55,
  bollinger_pct_b: 0.6,
  z_score_20: 0.5,
  faixa_52s_min: 30.0,
  faixa_52s_max: 45.0,
  macd_diff: 0.1,
  stoch_k: 60,
  stoch_d: 55,
  adx: 25,
  preco_graham: null,
  preco_dcf: null,
  chain: [],
};

// Data futura distante para garantir T > 0 independentemente de quando o teste roda.
const FUTURE_EXPIRY = '2099-12-01';

function fillForm(strike: string, price: string, expiry = FUTURE_EXPIRY) {
  fireEvent.change(screen.getByPlaceholderText('38.00'), { target: { value: strike } });
  fireEvent.change(screen.getByPlaceholderText('1.45'), { target: { value: price } });
  const dateInput = document.querySelector('input[type="date"]');
  if (!dateInput) throw new Error('input de data não encontrado');
  fireEvent.change(dateInput, { target: { value: expiry } });
}

describe('OptionAnalyzer', () => {
  it('sem payload, mostra mensagem pedindo para analisar um ativo primeiro', () => {
    render(<OptionAnalyzer payload={null} />);
    expect(screen.getByText(/Analise um ativo primeiro/i)).toBeInTheDocument();
  });

  it('com payload, mostra os campos de entrada da calculadora', () => {
    render(<OptionAnalyzer payload={mockPayload} />);
    expect(screen.getByPlaceholderText('38.00')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('1.45')).toBeInTheDocument();
    expect(screen.queryByText(/Analise um ativo primeiro/i)).not.toBeInTheDocument();
  });

  it('prêmio abaixo do valor intrínseco de uma CALL gera mensagem de erro', () => {
    render(<OptionAnalyzer payload={mockPayload} />);
    // S=38, K=35 (CALL é o tipo padrão) -> intrínseco = max(0, 38-35) = 3.00.
    // Prêmio de 0.50 está abaixo disso: cálculo de IV é impossível.
    fillForm('35', '0.50');
    expect(screen.getByText(/abaixo do valor intrínseco/i)).toBeInTheDocument();
  });

  it('prêmio coerente com o intrínseco não gera mensagem de erro', () => {
    render(<OptionAnalyzer payload={mockPayload} />);
    // S=38, K=38 (ATM) -> intrínseco = 0; prêmio de 2.00 é plausível para uma ATM.
    fillForm('38', '2.00');
    expect(screen.queryByText(/abaixo do valor intrínseco/i)).not.toBeInTheDocument();
  });

  it('alternar para PUT recalcula o intrínseco e pode disparar o erro', () => {
    render(<OptionAnalyzer payload={mockPayload} />);
    fireEvent.click(screen.getByText('PUT'));
    // S=38, K=45 (PUT) -> intrínseco = max(0, 45-38) = 7.00; prêmio de 0.50 está abaixo.
    fillForm('45', '0.50');
    expect(screen.getByText(/abaixo do valor intrínseco/i)).toBeInTheDocument();
  });
});
