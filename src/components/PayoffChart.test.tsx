import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PayoffChart from './PayoffChart';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: { post: vi.fn() },
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
}));

const legs = [{ type: 'call' as const, strike: 38, entry_price: 2.0, side: 'buy' as const, qty: 1 }];

describe('PayoffChart', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockReset();
  });

  it('sem legs, não renderiza nada', () => {
    const { container } = render(<PayoffChart spotPrice={38} legs={[]} />);
    expect(container).toBeEmptyDOMElement();
    expect(api.post).not.toHaveBeenCalled();
  });

  it('com legs, mostra estado de carregamento enquanto a requisição está pendente', () => {
    vi.mocked(api.post).mockReturnValue(new Promise(() => {})); // nunca resolve
    render(<PayoffChart spotPrice={38} legs={legs} />);
    expect(screen.getByText(/Calculando Curva/i)).toBeInTheDocument();
  });

  it('quando a API retorna erro, exibe a mensagem de erro', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { error: 'parâmetros inválidos' } });
    render(<PayoffChart spotPrice={38} legs={legs} />);
    await waitFor(() => expect(screen.getByText('parâmetros inválidos')).toBeInTheDocument());
  });

  it('quando a requisição falha (exceção), exibe mensagem de erro genérica', async () => {
    vi.mocked(api.post).mockRejectedValue(new Error('network error'));
    render(<PayoffChart spotPrice={38} legs={legs} />);
    await waitFor(() =>
      expect(screen.getByText(/Erro ao carregar gráfico de payoff/i)).toBeInTheDocument()
    );
  });

  it('quando a API retorna a curva, renderiza o gráfico de payoff', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        curve: [
          { spot_price: 36, pnl: -2 },
          { spot_price: 38, pnl: 0 },
          { spot_price: 40, pnl: 2 },
        ],
      },
    });
    render(<PayoffChart spotPrice={38} legs={legs} />);
    await waitFor(() => expect(screen.getByTestId('area-chart')).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledWith('/signals/payoff', { spot_price: 38, legs });
  });
});
