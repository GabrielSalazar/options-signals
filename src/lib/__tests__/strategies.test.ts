import { describe, it, expect } from 'vitest';
import {
  legIntrinsic, legSign, calculateStrategy, calculatePayoffCurve,
  getLongCallLegs, getBullCallSpreadLegs, type Leg,
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
