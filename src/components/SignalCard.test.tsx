import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SignalCard from './SignalCard';
import { Signal } from '@/types/signals';

const baseSignal: Signal = {
  ticker: 'PETR4',
  nome: 'Petrobras PN',
  tipo_sinal: 'CALL',
  direcao: 'alta',
  preco_acao: 38.5,
  ticker_opcao: 'PETRG400',
  strike_ref: 40,
  dist_otm_pct: 4,
  hv_20d: 32.1,
  dte: 15,
  mes_venc: 7,
  ano_venc: 2026,
  premio_est: 0.85,
  preco_tela: null,
  entrada_min: 0.8,
  entrada_max: 0.9,
  alvo1: 1.2,
  alvo2: 1.6,
  alvo_final: 2.0,
  stop: 0.5,
  rr_alvo1: 1.5,
  rr_alvo2: 2.5,
  rr_final: 3.0,
  score: 7.5,
  stoch_k: 25.3,
  rsi: 42.1,
  vol_ratio: 1.8,
  gatilhos: ['Stoch cruzou para cima'],
};

describe('SignalCard — Matriz v2 (executabilidade, classe, evento)', () => {
  it('não renderiza seção Executabilidade nem badges quando campos v2 ausentes', () => {
    render(<SignalCard signal={baseSignal} />);
    expect(screen.queryByText('Executabilidade')).not.toBeInTheDocument();
    expect(screen.queryByText(/Classe/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Liquidez/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sizing sugerido/)).not.toBeInTheDocument();
  });

  it('exibe OI, bid/ask, spread e VXBR formatados', () => {
    render(
      <SignalCard
        signal={{
          ...baseSignal,
          oi: 12500,
          bid: 0.82,
          ask: 0.88,
          spread_pct: 7.3,
          vxbr: 22.4,
        }}
      />
    );
    expect(screen.getByText('Executabilidade')).toBeInTheDocument();
    expect(screen.getByText('fech. anterior')).toBeInTheDocument();
    expect(screen.getByText((12500).toLocaleString('pt-BR'))).toBeInTheDocument();
    expect(screen.getByText('0.82 / 0.88')).toBeInTheDocument();
    expect(screen.getByText('7.3%')).toBeInTheDocument();
    expect(screen.getByText('22.4')).toBeInTheDocument();
  });

  it('mostra "—" para campos de executabilidade nulos (nunca 0/NaN)', () => {
    render(
      <SignalCard
        signal={{ ...baseSignal, oi: null, bid: null, ask: null, spread_pct: null, vxbr: 18.2 }}
      />
    );
    expect(screen.getByText('Executabilidade')).toBeInTheDocument();
    expect(screen.queryByText('NaN')).not.toBeInTheDocument();
    // OI, Bid/Ask e Spread nulos → 3 traços na seção
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(3);
  });

  it('badge de liquidez "bloquear" com motivo em tooltip', () => {
    render(
      <SignalCard
        signal={{
          ...baseSignal,
          filtro_liquidez_decisao: 'bloquear',
          filtro_liquidez_motivo: 'OI abaixo do mínimo',
        }}
      />
    );
    const badge = screen.getByText('Liquidez: bloqueado (shadow)');
    expect(badge).toHaveAttribute('title', 'OI abaixo do mínimo');
  });

  it('badge de evento e classe v2 com razões de downgrade', () => {
    render(
      <SignalCard
        signal={{
          ...baseSignal,
          evento_label: 'COPOM',
          classe_v2: 'B',
          razoes_downgrade_classe: ['spread alto', 'OI baixo'],
        }}
      />
    );
    expect(screen.getByText(/COPOM/)).toBeInTheDocument();
    const classeBadge = screen.getByText('Classe B');
    expect(classeBadge).toHaveAttribute('title', 'Downgrade: spread alto; OI baixo');
  });

  it('sizing sugerido e divergência de prêmio > 15% destacada', () => {
    render(
      <SignalCard
        signal={{ ...baseSignal, sizing_sugerido_pct: 2.3, divergencia_premio_pct: 18.7 }}
      />
    );
    expect(screen.getByText(/Sizing sugerido/)).toBeInTheDocument();
    expect(screen.getByText('2.3% do capital')).toBeInTheDocument();
    expect(screen.getByText('18.7%')).toBeInTheDocument();
    expect(screen.getByText(/Divergência de prêmio/)).toHaveClass('font-semibold');
  });

  it('divergência <= 15% não destacada', () => {
    render(<SignalCard signal={{ ...baseSignal, divergencia_premio_pct: 8.0 }} />);
    expect(screen.getByText(/Divergência de prêmio/)).not.toHaveClass('font-semibold');
  });
});
