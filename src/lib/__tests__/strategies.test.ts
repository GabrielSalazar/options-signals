import { describe, it, expect } from 'vitest';
import {
  legIntrinsic, legSign, calculateStrategy, calculatePayoffCurve, type Leg,
  STRATEGY_DEFS, instantiateLegs, defaultStrikes, type StrategyId,
  // Construtores mantidos — usados como referência de regressão da migração
  getLongCallLegs, getShortCallLegs, getLongPutLegs, getShortPutLegs,
  getCoveredCallLegs, getProtectivePutLegs,
  getStraddleLegs, getShortStraddleLegs, getStrangleLegs, getShortStrangleLegs,
  getBullCallSpreadLegs, getBearPutSpreadLegs, getBullPutSpreadLegs, getBearCallSpreadLegs,
  getButterflyCallLegs, getIronCondorLegs,
} from '@/lib/strategies';

/** Chave canônica de uma perna, p/ comparar listas como multiconjuntos. */
const normLegs = (legs: Leg[]) =>
  legs.map((l) => `${l.type}:${l.side}:${l.strike}:${l.quantity}`).sort();

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

  it('sintético vendido tem perda ilimitada na alta', () => {
    expect(mk('syntheticShort').maxLoss).toBe('Ilimitado');
  });

  it('call ratio backspread tem alta ilimitada', () => {
    expect(mk('callRatioBackspread').maxProfit).toBe('Infinito');
  });

  it('strip tem alta ilimitada (perna de call comprada)', () => {
    expect(mk('strip').maxProfit).toBe('Infinito');
  });

  it('iron butterfly tem lucro e perda finitos', () => {
    const r = mk('ironButterfly');
    expect(typeof r.maxProfit).toBe('number');
    expect(typeof r.maxLoss).toBe('number');
  });

  it('long condor tem lucro e perda finitos', () => {
    const r = mk('longCondor');
    expect(typeof r.maxProfit).toBe('number');
    expect(typeof r.maxLoss).toBe('number');
  });
});

// ── Regressão: a migração data-driven preserva as 16 estratégias originais ─────

describe('migração — registro instancia as mesmas pernas dos construtores antigos', () => {
  const cases: Array<[StrategyId, number[], Leg[]]> = [
    ['longCall',       [100],              getLongCallLegs(100)],
    ['shortCall',      [100],              getShortCallLegs(100)],
    ['longPut',        [100],              getLongPutLegs(100)],
    ['shortPut',       [100],              getShortPutLegs(100)],
    ['coveredCall',    [100],              getCoveredCallLegs(100)],
    ['protectivePut',  [100],              getProtectivePutLegs(100)],
    ['straddle',       [100],              getStraddleLegs(100)],
    ['shortStraddle',  [100],              getShortStraddleLegs(100)],
    ['strangle',       [95, 105],          getStrangleLegs(95, 105)],
    ['shortStrangle',  [95, 105],          getShortStrangleLegs(95, 105)],
    ['bullCall',       [95, 105],          getBullCallSpreadLegs(95, 105)],
    ['bearPut',        [95, 105],          getBearPutSpreadLegs(95, 105)],
    ['bullPutSpread',  [95, 105],          getBullPutSpreadLegs(95, 105)],
    ['bearCallSpread', [95, 105],          getBearCallSpreadLegs(95, 105)],
    ['butterflyCall',  [90, 100, 110],     getButterflyCallLegs(90, 100, 110)],
    ['ironCondor',     [90, 95, 105, 110], getIronCondorLegs(90, 95, 105, 110)],
  ];

  it.each(cases)('%s gera as mesmas pernas', (id, strikes, expected) => {
    expect(normLegs(instantiateLegs(STRATEGY_DEFS[id], strikes))).toEqual(normLegs(expected));
  });

  it('defaultStrikes mapeia os offsets para strikes em torno de S', () => {
    expect(defaultStrikes(STRATEGY_DEFS.ironCondor, 100)).toEqual([90, 95, 105, 110]);
    expect(defaultStrikes(STRATEGY_DEFS.straddle, 42)).toEqual([42]);
  });
});

// ── Payoff travado e replicação sintética (vencimento) ────────────────────────

describe('payoff no vencimento — travadas e sintéticas', () => {
  const expCurve = (id: StrategyId) => {
    const d = STRATEGY_DEFS[id];
    const legs = instantiateLegs(d, defaultStrikes(d, 100));
    return calculatePayoffCurve(legs, 100, 30 / 365, 0.3, 0.1, 0, 0.4, 80, d.stockUnits)
      .map((p) => p.payoffExpiration);
  };

  it.each(['boxSpread', 'conversion', 'reversal'] as StrategyId[])(
    '%s tem payoff constante no vencimento (travado)',
    (id) => {
      const vals = expCurve(id);
      const spread = Math.max(...vals) - Math.min(...vals);
      expect(spread).toBeLessThan(0.01);
    },
  );

  it('sintético comprado replica a ação (inclinação ≈ 1)', () => {
    const vals = expCurve('syntheticLong');
    const d = STRATEGY_DEFS.syntheticLong;
    const curve = calculatePayoffCurve(
      instantiateLegs(d, defaultStrikes(d, 100)), 100, 30 / 365, 0.3, 0.1, 0, 0.4, 80, d.stockUnits,
    );
    const lo = curve[10], hi = curve[curve.length - 10];
    const slope = (hi.payoffExpiration - lo.payoffExpiration) / (hi.S - lo.S);
    expect(slope).toBeCloseTo(1, 2);
    // e não é constante (ao contrário das travadas)
    expect(Math.max(...vals) - Math.min(...vals)).toBeGreaterThan(1);
  });
});
