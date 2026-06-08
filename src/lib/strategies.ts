/**
 * Options Strategies Library
 * Leg definitions, payoff calculator, and strategy metadata for the StrategiesBuilder UI.
 *
 * Strategies supported (17 total):
 *   Puras:       Long Call, Short Call, Long Put, Short Put
 *   Com Ação:    Covered Call, Protective Put
 *   Spreads:     Bull Call Spread, Bear Put Spread, Bull Put Spread, Bear Call Spread
 *   Volatilidade: Long Straddle, Long Strangle, Short Straddle, Short Strangle, Butterfly
 *   Complexas:   Iron Condor
 */
import { calcAll, callPrice, putPrice } from './black-scholes';

export type OptionType = 'call' | 'put';
export type Side = 'long' | 'short';

export interface Leg {
  type: OptionType;
  strike: number;
  side: Side;
  quantity: number;
}

/** Intrinsic value of a single leg at price S — usado em payoff/breakeven/monte-carlo */
export function legIntrinsic(leg: Leg, S: number): number {
  return leg.type === 'call'
    ? Math.max(S - leg.strike, 0)
    : Math.max(leg.strike - S, 0);
}

/** +1 para long, -1 para short — multiplicador de sinal aplicado em PnL/payoff */
export function legSign(leg: Leg): 1 | -1 {
  return leg.side === 'long' ? 1 : -1;
}

// ── Strategy Types ────────────────────────────────────────────────────────────

export type StrategyName =
  | 'custom'
  // ── Posições Puras ─────────────────────────────────
  | 'longCall'
  | 'shortCall'
  | 'longPut'
  | 'shortPut'
  // ── Com Ação ───────────────────────────────────────
  | 'coveredCall'
  | 'protectivePut'
  // ── Spreads ────────────────────────────────────────
  | 'bullCall'
  | 'bearPut'
  | 'bullPutSpread'
  | 'bearCallSpread'
  // ── Volatilidade ───────────────────────────────────
  | 'straddle'
  | 'strangle'
  | 'shortStraddle'
  | 'shortStrangle'
  | 'butterflyCall'
  // ── Complexas ──────────────────────────────────────
  | 'ironCondor';

export type StrategyCategory = 'puras' | 'acao' | 'spreads' | 'volatilidade' | 'complexas';
export type StrategyProfile = 'alta' | 'baixa' | 'neutro' | 'renda' | 'hedge';

export interface StrategyMeta {
  label: string;              // English name (as known in market)
  labelPT: string;            // Portuguese name
  description: string;        // One-line description in Portuguese
  category: StrategyCategory;
  profile: StrategyProfile;
  numLegs: number;
  hasStockComponent: boolean; // true for Covered Call and Protective Put
  unlimitedLoss: boolean;     // true for Short Call, Short Straddle, Short Strangle
  icon: string;               // emoji displayed in the card grid
}

// ── Strategy Metadata ─────────────────────────────────────────────────────────

export const STRATEGY_META: Record<StrategyName, StrategyMeta> = {
  custom: {
    label: 'Custom', labelPT: 'Personalizada',
    description: 'Monte sua própria estrutura de opções.',
    category: 'complexas', profile: 'neutro', numLegs: 0,
    hasStockComponent: false, unlimitedLoss: false, icon: '⚙️',
  },
  longCall: {
    label: 'Long Call', labelPT: 'Compra de Call',
    description: 'Alta especulativa — risco limitado ao prêmio, ganho ilimitado.',
    category: 'puras', profile: 'alta', numLegs: 1,
    hasStockComponent: false, unlimitedLoss: false, icon: '📈',
  },
  shortCall: {
    label: 'Short Call', labelPT: 'Venda de Call',
    description: 'Gera renda em queda ou lateralidade — risco ilimitado em alta forte.',
    category: 'puras', profile: 'neutro', numLegs: 1,
    hasStockComponent: false, unlimitedLoss: true, icon: '💰',
  },
  longPut: {
    label: 'Long Put', labelPT: 'Compra de Put',
    description: 'Baixa especulativa — risco limitado ao prêmio pago.',
    category: 'puras', profile: 'baixa', numLegs: 1,
    hasStockComponent: false, unlimitedLoss: false, icon: '📉',
  },
  shortPut: {
    label: 'Short Put', labelPT: 'Venda de Put',
    description: 'Gera renda aguardando ponto de entrada mais barato na ação.',
    category: 'puras', profile: 'alta', numLegs: 1,
    hasStockComponent: false, unlimitedLoss: false, icon: '💵',
  },
  coveredCall: {
    label: 'Covered Call', labelPT: 'Venda Coberta',
    description: 'Rentabiliza carteira de ações vendendo calls — a mais usada no Brasil.',
    category: 'acao', profile: 'renda', numLegs: 2,
    hasStockComponent: true, unlimitedLoss: false, icon: '🏦',
  },
  protectivePut: {
    label: 'Protective Put', labelPT: 'Put Protetora',
    description: 'Seguro contra quedas em posição comprada em ações.',
    category: 'acao', profile: 'hedge', numLegs: 2,
    hasStockComponent: true, unlimitedLoss: false, icon: '🛡️',
  },
  bullCall: {
    label: 'Bull Call Spread', labelPT: 'Trava de Alta com Call',
    description: 'Aposta de alta com custo e risco reduzidos (débito).',
    category: 'spreads', profile: 'alta', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '↗️',
  },
  bearPut: {
    label: 'Bear Put Spread', labelPT: 'Trava de Baixa com Put',
    description: 'Aposta de baixa com custo e risco reduzidos (débito).',
    category: 'spreads', profile: 'baixa', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '↘️',
  },
  bullPutSpread: {
    label: 'Bull Put Spread', labelPT: 'Trava de Alta com Put',
    description: 'Crédito recebido apostando que o ativo fica acima do strike.',
    category: 'spreads', profile: 'renda', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '↗️',
  },
  bearCallSpread: {
    label: 'Bear Call Spread', labelPT: 'Trava de Baixa com Call',
    description: 'Crédito recebido apostando que o ativo fica abaixo do strike.',
    category: 'spreads', profile: 'renda', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '↘️',
  },
  straddle: {
    label: 'Long Straddle', labelPT: 'Straddle Comprado',
    description: 'Lucra com movimentos fortes em qualquer direção.',
    category: 'volatilidade', profile: 'neutro', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '⟺',
  },
  strangle: {
    label: 'Long Strangle', labelPT: 'Strangle Comprado',
    description: 'Como o Straddle, mas mais barato — exige movimento maior.',
    category: 'volatilidade', profile: 'neutro', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: false, icon: '↔️',
  },
  shortStraddle: {
    label: 'Short Straddle', labelPT: 'Straddle Vendido',
    description: 'Lucra com mercado parado — risco ilimitado em ambos lados.',
    category: 'volatilidade', profile: 'renda', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: true, icon: '⊖',
  },
  shortStrangle: {
    label: 'Short Strangle', labelPT: 'Strangle Vendido',
    description: 'Range mais amplo que o Short Straddle — risco ilimitado.',
    category: 'volatilidade', profile: 'renda', numLegs: 2,
    hasStockComponent: false, unlimitedLoss: true, icon: '⊗',
  },
  butterflyCall: {
    label: 'Butterfly Spread', labelPT: 'Borboleta',
    description: 'Máximo lucro se fechar exatamente no strike central.',
    category: 'volatilidade', profile: 'neutro', numLegs: 3,
    hasStockComponent: false, unlimitedLoss: false, icon: '🦋',
  },
  ironCondor: {
    label: 'Iron Condor', labelPT: 'Iron Condor',
    description: 'Renda com mercado dentro de um range amplo — 4 pernas.',
    category: 'complexas', profile: 'renda', numLegs: 4,
    hasStockComponent: false, unlimitedLoss: false, icon: '🦅',
  },
};

// ── Strategy Result ───────────────────────────────────────────────────────────

export interface StrategyResult {
  totalCost: number; // Positive = net debit (cost), negative = net credit (received)
  maxProfit: number | 'Infinito';
  maxLoss: number | 'Ilimitado';
  breakevens: number[];
  greeks: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
  };
  legsResult: {
    price: number;
    total: number; // price * quantity * side sign
  }[];
}

// ── Leg Constructors: Existing ────────────────────────────────────────────────

export const getStraddleLegs = (K: number): Leg[] => [
  { type: 'call', strike: K, side: 'long', quantity: 1 },
  { type: 'put',  strike: K, side: 'long', quantity: 1 },
];

export const getStrangleLegs = (K_put: number, K_call: number): Leg[] => [
  { type: 'put',  strike: K_put,  side: 'long', quantity: 1 },
  { type: 'call', strike: K_call, side: 'long', quantity: 1 },
];

export const getBullCallSpreadLegs = (K_long: number, K_short: number): Leg[] => [
  { type: 'call', strike: K_long,  side: 'long',  quantity: 1 },
  { type: 'call', strike: K_short, side: 'short', quantity: 1 },
];

export const getBearPutSpreadLegs = (K_short: number, K_long: number): Leg[] => [
  { type: 'put', strike: K_short, side: 'short', quantity: 1 },
  { type: 'put', strike: K_long,  side: 'long',  quantity: 1 },
];

export const getIronCondorLegs = (
  K_put_long: number,
  K_put_short: number,
  K_call_short: number,
  K_call_long: number,
): Leg[] => [
  { type: 'put',  strike: K_put_long,   side: 'long',  quantity: 1 },
  { type: 'put',  strike: K_put_short,  side: 'short', quantity: 1 },
  { type: 'call', strike: K_call_short, side: 'short', quantity: 1 },
  { type: 'call', strike: K_call_long,  side: 'long',  quantity: 1 },
];

// ── Leg Constructors: Posições Puras ─────────────────────────────────────────

export const getLongCallLegs = (K: number): Leg[] => [
  { type: 'call', strike: K, side: 'long', quantity: 1 },
];

export const getShortCallLegs = (K: number): Leg[] => [
  { type: 'call', strike: K, side: 'short', quantity: 1 },
];

export const getLongPutLegs = (K: number): Leg[] => [
  { type: 'put', strike: K, side: 'long', quantity: 1 },
];

export const getShortPutLegs = (K: number): Leg[] => [
  { type: 'put', strike: K, side: 'short', quantity: 1 },
];

// ── Leg Constructors: Com Ação ────────────────────────────────────────────────
// Apenas a perna de opção — stockOffset=true adiciona o P&L da ação no motor

export const getCoveredCallLegs = (K: number): Leg[] => [
  { type: 'call', strike: K, side: 'short', quantity: 1 },
];

export const getProtectivePutLegs = (K: number): Leg[] => [
  { type: 'put', strike: K, side: 'long', quantity: 1 },
];

// ── Leg Constructors: Spreads de Crédito ─────────────────────────────────────

/** Bull Put Spread: recebe crédito apostando que o ativo fica acima de K_high */
export const getBullPutSpreadLegs = (K_low: number, K_high: number): Leg[] => [
  { type: 'put', strike: K_high, side: 'short', quantity: 1 },
  { type: 'put', strike: K_low,  side: 'long',  quantity: 1 },
];

/** Bear Call Spread: recebe crédito apostando que o ativo fica abaixo de K_low */
export const getBearCallSpreadLegs = (K_low: number, K_high: number): Leg[] => [
  { type: 'call', strike: K_low,  side: 'short', quantity: 1 },
  { type: 'call', strike: K_high, side: 'long',  quantity: 1 },
];

// ── Leg Constructors: Volatilidade Vendida ────────────────────────────────────

export const getShortStraddleLegs = (K: number): Leg[] => [
  { type: 'call', strike: K, side: 'short', quantity: 1 },
  { type: 'put',  strike: K, side: 'short', quantity: 1 },
];

export const getShortStrangleLegs = (K_put: number, K_call: number): Leg[] => [
  { type: 'put',  strike: K_put,  side: 'short', quantity: 1 },
  { type: 'call', strike: K_call, side: 'short', quantity: 1 },
];

/**
 * Butterfly Call: Long(K1) + 2×Short(K2) + Long(K3)
 * K2 deve ser o ponto médio entre K1 e K3 para lucro máximo.
 */
export const getButterflyCallLegs = (K1: number, K2: number, K3: number): Leg[] => [
  { type: 'call', strike: K1, side: 'long',  quantity: 1 },
  { type: 'call', strike: K2, side: 'short', quantity: 2 },
  { type: 'call', strike: K3, side: 'long',  quantity: 1 },
];

// ── Core Calculator ───────────────────────────────────────────────────────────

/**
 * @param stockUnits — unidades de ação com sinal (+1 long, -1 short, 0 nenhum).
 *   Adiciona stockUnits·(S − S_center) ao payoff e stockUnits ao delta, modelando
 *   a posição em ação (Covered Call, Protective Put, Collar, Conversão, Reversão).
 */
export function calculateStrategy(
  legs: Leg[],
  S: number,
  T: number,   // em anos (days / 365)
  sigma: number,
  r: number,
  q: number,
  stockUnits: number = 0,
): StrategyResult {
  let totalCost = 0;
  let delta = 0;
  let gamma = 0;
  let theta = 0;
  let vega  = 0;

  const legsResult: { price: number; total: number }[] = [];

  for (const leg of legs) {
    const res    = calcAll(S, leg.strike, T, sigma, r, q, leg.type);
    const sign   = leg.side === 'long' ? 1 : -1;
    const factor = sign * leg.quantity;

    totalCost += res.price * factor;
    delta     += res.delta * factor;
    gamma     += res.gamma * factor;
    theta     += res.theta * factor;
    vega      += res.vega  * factor;

    legsResult.push({ price: res.price, total: res.price * factor });
  }

  // Delta da posição em ação = stockUnits (não inclui gregas de 2ª ordem da ação)
  delta += stockUnits;

  const { maxProfit, maxLoss, breakevens } = analyzeExpiration(legs, totalCost, S, stockUnits);

  return {
    totalCost,
    maxProfit,
    maxLoss,
    breakevens,
    greeks: { delta, gamma, theta, vega },
    legsResult,
  };
}

// ── Payoff Curve Generator ────────────────────────────────────────────────────

export interface PayoffPoint {
  S: number;
  payoffExpiration: number;
  payoffToday: number;
}

export function calculatePayoffCurve(
  legs: Leg[],
  S_center: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  rangePercent: number = 0.4,
  points: number = 150,
  stockUnits: number = 0,
): PayoffPoint[] {
  const curve: PayoffPoint[] = [];
  const start = Math.max(0.01, S_center * (1 - rangePercent));
  const end   = S_center * (1 + rangePercent);
  const step  = (end - start) / points;

  // Net cost at entry (options only — stock cost is sunk)
  let entryCost = 0;
  for (const leg of legs) {
    const p = leg.type === 'call'
      ? callPrice(S_center, leg.strike, T, sigma, r, q)
      : putPrice(S_center, leg.strike, T, sigma, r, q);
    entryCost += p * leg.quantity * (leg.side === 'long' ? 1 : -1);
  }

  for (let i = 0; i <= points; i++) {
    const s = Math.max(0.01, start + i * step);

    let payoffExp   = 0;
    let payoffToday = 0;

    for (const leg of legs) {
      const sign = leg.side === 'long' ? 1 : -1;
      const qty  = leg.quantity;

      // Expiration intrinsic
      const intrinsic = leg.type === 'call'
        ? Math.max(s - leg.strike, 0)
        : Math.max(leg.strike - s, 0);
      payoffExp += intrinsic * sign * qty;

      // Mark-to-market value today
      const valToday = leg.type === 'call'
        ? callPrice(s, leg.strike, T, sigma, r, q)
        : putPrice(s, leg.strike, T, sigma, r, q);
      payoffToday += valToday * sign * qty;
    }

    // Stock component: stockUnits·(S − S₀) models P&L of the underlying position
    const stockPnL = stockUnits * (s - S_center);

    curve.push({
      S: parseFloat(s.toFixed(2)),
      payoffExpiration: parseFloat((payoffExp   + stockPnL - entryCost).toFixed(4)),
      payoffToday:      parseFloat((payoffToday + stockPnL - entryCost).toFixed(4)),
    });
  }

  return curve;
}

// ── Expiration Analysis (Max Profit, Max Loss, Breakevens) ────────────────────

function analyzeExpiration(
  legs: Leg[],
  entryCost: number,
  S_center: number,
  stockUnits: number = 0,
) {
  const strikes = Array.from(new Set(legs.map((l) => l.strike))).sort((a, b) => a - b);
  const minStrike = strikes.length > 0 ? strikes[0] : S_center;
  const maxStrike = strikes.length > 0 ? strikes[strikes.length - 1] : S_center;

  const pointsToEval = [
    Math.max(0.01, minStrike * 0.1),
    ...strikes,
    maxStrike * 2,
  ];

  let maxP = -Infinity;
  let maxL =  Infinity;
  const payoffs: { s: number; pnl: number }[] = [];

  for (const s of pointsToEval) {
    let expVal = 0;
    for (const leg of legs) {
      expVal += legIntrinsic(leg, s) * legSign(leg) * leg.quantity;
    }
    const pnl = expVal + stockUnits * (s - S_center) - entryCost;
    maxP = Math.max(maxP, pnl);
    maxL = Math.min(maxL, pnl);
    payoffs.push({ s, pnl });
  }

  let finalMaxProfit: number | 'Infinito' = maxP;
  let finalMaxLoss: number | 'Ilimitado'  = maxL;

  // Detect infinite profit/loss via slope at extremes
  const p0   = payoffs[0];
  const p1   = payoffs[1];
  const pend = payoffs[payoffs.length - 1];
  const pprev = payoffs[payoffs.length - 2];

  if (p1    && p0.pnl   > p1.pnl   && p0.pnl   > 0) finalMaxProfit = 'Infinito';
  if (pprev && pend.pnl > pprev.pnl && pend.pnl > 0) finalMaxProfit = 'Infinito';
  if (pprev && pend.pnl < pprev.pnl && pend.pnl < 0) finalMaxLoss   = 'Ilimitado';
  if (p1    && p0.pnl   < p1.pnl   && p0.pnl   < 0) finalMaxLoss   = 'Ilimitado';

  // Fine-grid scan for breakevens
  const breakevens: number[] = [];
  const fineStep = (maxStrike * 2) / 2000;
  let prevS   = -1;
  let prevPnl = 0;

  for (let s = 0.01; s <= maxStrike * 2; s += fineStep) {
    let expVal = 0;
    for (const leg of legs) {
      expVal += legIntrinsic(leg, s) * legSign(leg) * leg.quantity;
    }
    const pnl = expVal + stockUnits * (s - S_center) - entryCost;

    if (prevS !== -1 && ((prevPnl < 0 && pnl > 0) || (prevPnl > 0 && pnl < 0))) {
      const interpS = prevS - prevPnl * ((s - prevS) / (pnl - prevPnl));
      if (!breakevens.some((b) => Math.abs(b - interpS) < 0.1)) {
        breakevens.push(interpS);
      }
    }
    prevS   = s;
    prevPnl = pnl;
  }

  return { maxProfit: finalMaxProfit, maxLoss: finalMaxLoss, breakevens };
}
