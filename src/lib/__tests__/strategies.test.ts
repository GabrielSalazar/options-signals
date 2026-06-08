import { describe, it, expect } from 'vitest';
import {
  legIntrinsic, legSign, calculateStrategy, calculatePayoffCurve,
  getLongCallLegs, getBullCallSpreadLegs, type Leg,
  STRATEGY_DEFS, instantiateLegs, defaultStrikes, type StrategyId,
} from '@/lib/strategies';

const longCall: Leg = { type: 'call', strike: 100, side: 'long', quantity: 1 };
const longPut: Leg = { type: 'put', strike: 100, side: 'long', quantity: 1 };

describe('legIntrinsic', () => {
  it('call: max(S - K, 0)', () => {
    expect(legIntrinsic(longCall, 110)).toBe(10);
    expect(legIntrinsic(longCall, 90)).toBe(0);
  });
  it('put: max(K - S, 0)', () => {
    expect(legIntrinsic(longPut, 90)).toBe(10);
    expect(legIntrinsic(longPut, 110)).toBe(0);
  });
});

describe('legSign', () => {
  it('+1 for long, -1 for short', () => {
    expect(legSign({ ...longCall, side: 'long' })).toBe(1);
    expect(legSign({ ...longCall, side: 'short' })).toBe(-1);
  });
});

describe('calculateStrategy — long call', () => {
  const res = calculateStrategy(getLongCallLegs(100), 100, 30 / 365, 0.3, 0.1, 0);

  it('is a net debit (positive cost)', () => {
    expect(res.totalCost).toBeGreaterThan(0);
  });

  it('greeks of a long call have expected signs', () => {
    expect(res.greeks.delta).toBeGreaterThan(0);
    expect(res.greeks.delta).toBeLessThan(1);
    expect(res.greeks.gamma).toBeGreaterThan(0);
    expect(res.greeks.vega).toBeGreaterThan(0);
    expect(res.greeks.theta).toBeLessThan(0);
  });

  it('has unlimited upside and a capped loss', () => {
    expect(res.maxProfit).toBe('Infinito');
    expect(typeof res.maxLoss).toBe('number');
  });
});

describe('calculateStrategy — bull call spread', () => {
  const res = calculateStrategy(getBullCallSpreadLegs(100, 110), 100, 30 / 365, 0.3, 0.1, 0);

  it('is a net debit', () => {
    expect(res.totalCost).toBeGreaterThan(0);
  });

  it('has bounded profit and loss', () => {
    expect(typeof res.maxProfit).toBe('number');
    expect(typeof res.maxLoss).toBe('number');
  });
});

describe('calculatePayoffCurve', () => {
  const curve = calculatePayoffCurve(getLongCallLegs(100), 100, 30 / 365, 0.3, 0.1, 0, 0.4, 50);

  it('returns points+1 entries', () => {
    expect(curve.length).toBe(51);
  });

  it('expiration payoff is non-decreasing for a long call', () => {
    for (let i = 1; i < curve.length; i++) {
      expect(curve[i].payoffExpiration).toBeGreaterThanOrEqual(curve[i - 1].payoffExpiration - 1e-9);
    }
  });
});

describe('calculateStrategy — stockUnits (com sinal)', () => {
  const call = getLongCallLegs(100);
  const base   = calculateStrategy(call, 100, 30 / 365, 0.3, 0.1, 0, 0);
  const longS  = calculateStrategy(call, 100, 30 / 365, 0.3, 0.1, 0, 1);
  const shortS = calculateStrategy(call, 100, 30 / 365, 0.3, 0.1, 0, -1);

  it('ação comprada soma +1 ao delta; vendida subtrai 1', () => {
    expect(longS.greeks.delta).toBeCloseTo(base.greeks.delta + 1, 6);
    expect(shortS.greeks.delta).toBeCloseTo(base.greeks.delta - 1, 6);
  });

  it('ação comprada melhora o P&L na alta vs. sem ação', () => {
    const curve0 = calculatePayoffCurve(call, 100, 30 / 365, 0.3, 0.1, 0, 0.4, 50, 0);
    const curve1 = calculatePayoffCurve(call, 100, 30 / 365, 0.3, 0.1, 0, 0.4, 50, 1);
    const at = (c: { S: number; payoffExpiration: number }[]) =>
      c.reduce((p, x) => (Math.abs(x.S - 130) < Math.abs(p.S - 130) ? x : p));
    expect(at(curve1).payoffExpiration).toBeGreaterThan(at(curve0).payoffExpiration);
  });
});

describe('STRATEGY_DEFS — invariantes do registro', () => {
  const ids = Object.keys(STRATEGY_DEFS) as StrategyId[];

  it('strikeLabels e strikeOffsets têm o mesmo tamanho', () => {
    for (const id of ids) {
      const d = STRATEGY_DEFS[id];
      expect(d.strikeOffsets.length).toBe(d.strikeLabels.length);
    }
  });

  it('todo strikeRef está dentro da contagem de strikes declarada', () => {
    for (const id of ids) {
      const d = STRATEGY_DEFS[id];
      for (const leg of d.legs) {
        expect(leg.strikeRef).toBeGreaterThanOrEqual(0);
        expect(leg.strikeRef).toBeLessThan(d.strikeLabels.length);
      }
    }
  });

  it('strikeOffsets são não-decrescentes (strikes ascendentes)', () => {
    for (const id of ids) {
      const o = STRATEGY_DEFS[id].strikeOffsets;
      for (let i = 1; i < o.length; i++) expect(o[i]).toBeGreaterThanOrEqual(o[i - 1]);
    }
  });

  it('contém as 35 entradas (custom + 16 atuais + 18 novas)', () => {
    expect(ids.length).toBe(35);
  });
});

describe('instantiateLegs', () => {
  it('iron butterfly → 4 pernas em 3 strikes distintos', () => {
    const legs = instantiateLegs(STRATEGY_DEFS.ironButterfly, [90, 100, 110]);
    expect(legs.length).toBe(4);
    expect(new Set(legs.map((l) => l.strike))).toEqual(new Set([90, 100, 110]));
  });

  it('call ratio backspread → 2 calls compradas no strike superior', () => {
    const legs = instantiateLegs(STRATEGY_DEFS.callRatioBackspread, [100, 110]);
    const longLeg = legs.find((l) => l.side === 'long');
    expect(longLeg?.quantity).toBe(2);
    expect(longLeg?.strike).toBe(110);
  });

  it('reversal tem stockUnits = -1', () => {
    expect(STRATEGY_DEFS.reversal.stockUnits).toBe(-1);
  });
});

describe('novas estratégias — sanidade do payoff', () => {
  const mk = (id: StrategyId, S = 100) => {
    const d = STRATEGY_DEFS[id];
    const legs = instantiateLegs(d, defaultStrikes(d, S));
    return calculateStrategy(legs, S, 30 / 365, 0.3, 0.1, 0, d.stockUnits);
  };

  it('strap tem alta ilimitada', () => {
    expect(mk('strap').maxProfit).toBe('Infinito');
  });

  it('call front ratio spread tem perda ilimitada', () => {
    expect(mk('callFrontRatioSpread').maxLoss).toBe('Ilimitado');
  });

  it('box spread tem lucro e perda finitos (payoff travado)', () => {
    const r = mk('boxSpread');
    expect(typeof r.maxProfit).toBe('number');
    expect(typeof r.maxLoss).toBe('number');
  });
});
