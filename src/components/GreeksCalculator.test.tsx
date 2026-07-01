import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GreeksCalculator from './GreeksCalculator';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Line: () => null,
}));

vi.mock('@/components/ui/slider', () => ({
  Slider: ({
    value,
    min,
    max,
    step,
    onValueChange,
  }: {
    value: number[];
    min: number;
    max: number;
    step: number;
    onValueChange: (v: number[]) => void;
  }) => (
    <input
      type="range"
      value={value[0]}
      min={min}
      max={max}
      step={step}
      onChange={(e) => onValueChange([Number(e.target.value)])}
    />
  ),
}));

describe('GreeksCalculator', () => {
  it('renderiza os seis cards de gregas com seus nomes', () => {
    render(<GreeksCalculator />);
    for (const greek of ['Delta', 'Gamma', 'Theta', 'Vega', 'Vanna', 'Volga']) {
      expect(screen.getAllByText(new RegExp(`^${greek} =`)).length).toBeGreaterThan(0);
    }
  });

  it('inicia no modo CALL, classifica S=K=100 como ATM e mostra "Preço da Call"', () => {
    render(<GreeksCalculator />);
    // Parâmetros padrão do componente são S=100, K=100 — moneyness é derivado
    // independentemente da implementação de normalCDF, então não é afetado
    // pelo bug conhecido de paridade Black-Scholes da lib.
    expect(screen.getByText('Preço da Call')).toBeInTheDocument();
    expect(screen.getByText('ATM')).toBeInTheDocument();
  });

  it('ao clicar em PUT troca o resumo para "Preço da Put"', () => {
    render(<GreeksCalculator />);
    fireEvent.click(screen.getByText('PUT'));
    expect(screen.getByText('Preço da Put')).toBeInTheDocument();
    expect(screen.queryByText('Preço da Call')).not.toBeInTheDocument();
  });

  it('delta de uma CALL ATM (S=K=100) fica estritamente entre 0 e 1', () => {
    render(<GreeksCalculator />);
    const deltaSpan = screen.getAllByText(/^Delta =/)[0];
    const match = deltaSpan.textContent?.match(/Delta\s*=\s*([\d.]+)/);
    const delta = match ? parseFloat(match[1]) : NaN;
    expect(delta).toBeGreaterThan(0);
    expect(delta).toBeLessThan(1);
  });
});
