# Construtor de Estratégias data-driven (+18 estratégias) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar 18 estratégias de opções de vencimento único ao Construtor de Estratégias, tornando-as totalmente simuláveis (payoff, extremos, breakevens, Gregas, Monte Carlo, Hedging), via um registro genérico orientado a dados, mantendo o motor Black-Scholes existente.

**Architecture:** Refatorar `src/lib/strategies.ts` para um registro único `STRATEGY_DEFS` (templates de pernas com `strikeRef` + metadados). O `StrategiesBuilder` passa a renderizar N sliders de strike dinamicamente e a montar pernas via `instantiateLegs(def, strikes)`. O `stockOffset: boolean` vira `stockUnits: number` (com sinal) e é propagado para Monte Carlo/Hedging. Os arquivos de referência `payoff_engine.ts` e `estrategias_payoff.json` da raiz são removidos ao final.

**Tech Stack:** TypeScript, Next.js (App Router, client components), React, Recharts, Vitest (happy-dom). Black-Scholes já existente em `src/lib/black-scholes.ts`.

**Spec:** [docs/superpowers/specs/2026-06-07-construtor-estrategias-data-driven-design.md](../specs/2026-06-07-construtor-estrategias-data-driven-design.md)

**Comandos do projeto:**
- Testes: `npm test` (= `vitest run`)
- Lint: `npm run lint`
- Build: `npm run build`
- Dev: `npm run dev`

**Regra de commit deste repo:** o `commit-msg` hook BLOQUEIA o trailer `Co-Authored-By` de Claude/Anthropic. NÃO inclua essa linha em nenhum commit.

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `src/lib/strategies.ts` | Tipos, registro `STRATEGY_DEFS`, `instantiateLegs`, `defaultStrikes`, motor (`calculateStrategy`, `calculatePayoffCurve`, `analyzeExpiration`) | Modificar |
| `src/lib/monte-carlo.ts` | Simulação Monte Carlo de P&L; receber `stockUnits` | Modificar |
| `src/components/StrategiesBuilder.tsx` | UI do construtor: seletor, painel de strikes genérico, instanciação de pernas | Modificar |
| `src/components/RiskSimulator.tsx` | Wrapper Monte Carlo; repassar `stockUnits` | Modificar |
| `src/components/HedgingSimulator.tsx` | Delta hedging / gamma scalping; considerar `stockUnits` | Modificar |
| `src/app/estrategias/page.tsx` | Página + "Guia Rápido"; adicionar blocos das 5 novas categorias | Modificar |
| `src/lib/__tests__/strategies.test.ts` | Testes do registro/motor | Modificar |
| `src/lib/__tests__/monte-carlo.test.ts` | Testes do Monte Carlo | Modificar |
| `payoff_engine.ts`, `estrategias_payoff.json` (raiz, untracked) | Referência — remover ao final | Deletar |

---

## Task 1: Generalizar `stockOffset` → `stockUnits` (com sinal) no motor

Troca o parâmetro booleano `stockOffset` por um numérico `stockUnits` (default `0`) em `calculateStrategy`, `calculatePayoffCurve` e `analyzeExpiration`. Atualiza o único chamador real (o `StrategiesBuilder`) com um shim mínimo para manter tudo compilando. O comportamento das 16 estratégias atuais não muda (Covered Call/Protective Put passam `stockUnits = 1`).

**Files:**
- Modify: `src/lib/strategies.ts` (assinaturas e lógica de `calculateStrategy`, `calculatePayoffCurve`, `analyzeExpiration`)
- Modify: `src/components/StrategiesBuilder.tsx:117-155` (shim de `stockUnits`)
- Test: `src/lib/__tests__/strategies.test.ts`

- [ ] **Step 1: Escrever o teste que falha (delta reflete `stockUnits` com sinal)**

Adicionar ao final de `src/lib/__tests__/strategies.test.ts`:

```ts
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
    // payoff a S=130 (acima do strike): a ação comprada agrega (130 - 100)
    const curve0 = calculatePayoffCurve(call, 100, 30 / 365, 0.3, 0.1, 0, 0.4, 50, 0);
    const curve1 = calculatePayoffCurve(call, 100, 30 / 365, 0.3, 0.1, 0, 0.4, 50, 1);
    const at = (c: { S: number; payoffExpiration: number }[]) =>
      c.reduce((p, x) => (Math.abs(x.S - 130) < Math.abs(p.S - 130) ? x : p));
    expect(at(curve1).payoffExpiration).toBeGreaterThan(at(curve0).payoffExpiration);
  });
});
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `npm test -- strategies`
Esperado: FALHA — hoje o 7º argumento de `calculateStrategy` é `stockOffset: boolean`; passar `1`/`-1` não altera o delta com sinal (e `-1` é truthy, então `delta += 1` em ambos). O 1º teste falha (`-1` daria `+1`).

- [ ] **Step 3: Implementar — trocar `stockOffset` por `stockUnits` nas 3 funções**

Em `src/lib/strategies.ts`:

`calculateStrategy` — assinatura e uso (em torno das linhas 308-342):

```ts
export function calculateStrategy(
  legs: Leg[],
  S: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  stockUnits: number = 0,   // +1 long, -1 short, 0 nenhum
): StrategyResult {
```

Trocar `if (stockOffset) delta += 1;` por:

```ts
  // Delta da posição em ação = stockUnits (não inclui gregas de 2ª ordem da ação)
  delta += stockUnits;
```

Trocar a chamada de análise por:

```ts
  const { maxProfit, maxLoss, breakevens } = analyzeExpiration(legs, totalCost, S, stockUnits);
```

`calculatePayoffCurve` — assinatura (linha ~371) e termo de ação (linha ~411):

```ts
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
```

```ts
    // Componente em ação: stockUnits·(S − S₀) modela o P&L do ativo
    const stockPnL = stockUnits * (s - S_center);
```

`analyzeExpiration` — assinatura (linha ~425) e os dois termos de ação (linhas ~450 e ~481):

```ts
function analyzeExpiration(
  legs: Leg[],
  entryCost: number,
  S_center: number,
  stockUnits: number = 0,
) {
```

```ts
    const pnl = expVal + stockUnits * (s - S_center) - entryCost;
```

(aplicar a mesma troca `stockOffset ? (s - S_center) : 0` → `stockUnits * (s - S_center)` nas duas ocorrências dentro de `analyzeExpiration`).

- [ ] **Step 4: Shim no `StrategiesBuilder` para manter compilação**

Em `src/components/StrategiesBuilder.tsx`, trocar a linha 118 e as duas chamadas (149-155):

```tsx
  const meta        = STRATEGY_META[strategy];
  const stockUnits  = meta.hasStockComponent ? 1 : 0;
```

```tsx
  const result = useMemo(
    () => calculateStrategy(legs, S, T / 365, sigma / 100, r / 100, q / 100, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );

  const chartData = useMemo(
    () => calculatePayoffCurve(legs, S, T / 365, sigma / 100, r / 100, q / 100, 0.4, 150, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );
```

- [ ] **Step 5: Rodar testes e lint; confirmar verde**

Run: `npm test` e `npm run lint`
Esperado: todos os testes PASSAM (incluindo os novos); lint sem novos erros.

- [ ] **Step 6: Commit**

```bash
git add src/lib/strategies.ts src/components/StrategiesBuilder.tsx src/lib/__tests__/strategies.test.ts
git commit -m "refactor(strategies): stockOffset booleano vira stockUnits com sinal"
```

---

## Task 2: Adicionar o registro `STRATEGY_DEFS` + helpers (aditivo)

Introduz os tipos do registro, o objeto `STRATEGY_DEFS` (16 atuais migradas + 18 novas + `custom`) e os helpers `instantiateLegs`/`defaultStrikes`. É **puramente aditivo** — `STRATEGY_META`/`StrategyName` permanecem por ora (removidos na Task 3). Estende `StrategyCategory` com 5 chaves novas.

**Files:**
- Modify: `src/lib/strategies.ts` (novos tipos, `STRATEGY_DEFS`, helpers; estender `StrategyCategory`)
- Test: `src/lib/__tests__/strategies.test.ts`

- [ ] **Step 1: Estender `StrategyCategory` e adicionar os tipos do registro**

Em `src/lib/strategies.ts`, substituir a linha do `StrategyCategory` (linha 62) por:

```ts
export type StrategyCategory =
  | 'puras' | 'acao' | 'spreads' | 'volatilidade' | 'complexas'
  | 'razao' | 'borboletasAvancadas' | 'creditoHibridas' | 'direcionalVol' | 'sinteticas';
```

E adicionar, logo após a definição de `StrategyProfile` (após linha 63):

```ts
// ── Registro data-driven (fonte única do builder) ─────────────────────────────

export type StrategyId =
  | 'custom'
  | 'longCall' | 'shortCall' | 'longPut' | 'shortPut'
  | 'coveredCall' | 'protectivePut'
  | 'bullCall' | 'bearPut' | 'bullPutSpread' | 'bearCallSpread'
  | 'straddle' | 'strangle' | 'shortStraddle' | 'shortStrangle' | 'butterflyCall'
  | 'ironCondor'
  | 'callRatioBackspread' | 'putRatioBackspread' | 'callFrontRatioSpread' | 'putFrontRatioSpread'
  | 'ironButterfly' | 'longCondor' | 'brokenWingButterfly'
  | 'jadeLizard' | 'collar' | 'seagull' | 'riskReversal'
  | 'strap' | 'strip'
  | 'boxSpread' | 'conversion' | 'reversal' | 'syntheticLong' | 'syntheticShort';

export interface LegTemplate {
  type: OptionType;
  side: Side;
  qty: number;
  strikeRef: number;          // índice no array de strikes ASCENDENTE
}

export interface StrategyDef {
  id: StrategyId;
  label: string;
  labelPT: string;
  description: string;
  category: StrategyCategory;
  profile: StrategyProfile;
  icon: string;
  unlimitedLoss: boolean;
  stockUnits: number;         // +1 / -1 / 0
  legs: LegTemplate[];        // só pernas de opção
  strikeLabels: string[];     // 1 rótulo por strikeRef distinto (ascendente)
  strikeOffsets: number[];    // default de cada strike como offset de S (ascendente)
  locked?: boolean;           // payoff travado (box/conversão/reversão)
}
```

- [ ] **Step 2: Adicionar os helpers `instantiateLegs` e `defaultStrikes`**

Em `src/lib/strategies.ts`, adicionar logo após o bloco de tipos do registro:

```ts
/** Monta as pernas concretas (Leg[]) de uma estratégia a partir dos strikes. */
export function instantiateLegs(def: StrategyDef, strikes: number[]): Leg[] {
  return def.legs.map((l) => ({
    type: l.type,
    side: l.side,
    quantity: l.qty,
    strike: strikes[l.strikeRef],
  }));
}

/** Strikes default (arredondados) a partir dos offsets de S. */
export function defaultStrikes(def: StrategyDef, S: number): number[] {
  return def.strikeOffsets.map((o) => Math.round(S + o));
}
```

- [ ] **Step 3: Adicionar o objeto `STRATEGY_DEFS` completo**

Em `src/lib/strategies.ts`, adicionar (pode ser logo após `STRATEGY_META`):

```ts
// ── Registro completo (35 entradas: custom + 16 atuais + 18 novas) ────────────

export const STRATEGY_DEFS: Record<StrategyId, StrategyDef> = {
  custom: {
    id: 'custom', label: 'Custom', labelPT: 'Personalizada',
    description: 'Monte sua própria estrutura de opções.',
    category: 'complexas', profile: 'neutro', icon: '⚙️',
    unlimitedLoss: false, stockUnits: 0, legs: [], strikeLabels: [], strikeOffsets: [],
  },

  // ── Puras ──
  longCall: {
    id: 'longCall', label: 'Long Call', labelPT: 'Compra de Call',
    description: 'Alta especulativa — risco limitado ao prêmio, ganho ilimitado.',
    category: 'puras', profile: 'alta', icon: '📈', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  shortCall: {
    id: 'shortCall', label: 'Short Call', labelPT: 'Venda de Call',
    description: 'Gera renda em queda ou lateralidade — risco ilimitado em alta forte.',
    category: 'puras', profile: 'neutro', icon: '💰', unlimitedLoss: true, stockUnits: 0,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  longPut: {
    id: 'longPut', label: 'Long Put', labelPT: 'Compra de Put',
    description: 'Baixa especulativa — risco limitado ao prêmio pago.',
    category: 'puras', profile: 'baixa', icon: '📉', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  shortPut: {
    id: 'shortPut', label: 'Short Put', labelPT: 'Venda de Put',
    description: 'Gera renda aguardando ponto de entrada mais barato na ação.',
    category: 'puras', profile: 'alta', icon: '💵', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },

  // ── Com ação ──
  coveredCall: {
    id: 'coveredCall', label: 'Covered Call', labelPT: 'Venda Coberta',
    description: 'Rentabiliza carteira de ações vendendo calls — a mais usada no Brasil.',
    category: 'acao', profile: 'renda', icon: '🏦', unlimitedLoss: false, stockUnits: 1,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike da Call Vendida (K)'], strikeOffsets: [0],
  },
  protectivePut: {
    id: 'protectivePut', label: 'Protective Put', labelPT: 'Put Protetora',
    description: 'Seguro contra quedas em posição comprada em ações.',
    category: 'acao', profile: 'hedge', icon: '🛡️', unlimitedLoss: false, stockUnits: 1,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike da Put Protetora (K)'], strikeOffsets: [0],
  },

  // ── Spreads ──
  bullCall: {
    id: 'bullCall', label: 'Bull Call Spread', labelPT: 'Trava de Alta com Call',
    description: 'Aposta de alta com custo e risco reduzidos (débito).',
    category: 'spreads', profile: 'alta', icon: '↗️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 1, strikeRef: 0 }, { type: 'call', side: 'short', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Call Longa (K₁)', 'Strike Call Curta (K₂)'], strikeOffsets: [-5, 5],
  },
  bearPut: {
    id: 'bearPut', label: 'Bear Put Spread', labelPT: 'Trava de Baixa com Put',
    description: 'Aposta de baixa com custo e risco reduzidos (débito).',
    category: 'spreads', profile: 'baixa', icon: '↘️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'short', qty: 1, strikeRef: 0 }, { type: 'put', side: 'long', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Put Curta (K₁)', 'Strike Put Longa (K₂)'], strikeOffsets: [-5, 5],
  },
  bullPutSpread: {
    id: 'bullPutSpread', label: 'Bull Put Spread', labelPT: 'Trava de Alta com Put',
    description: 'Crédito recebido apostando que o ativo fica acima do strike.',
    category: 'spreads', profile: 'renda', icon: '↗️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }, { type: 'put', side: 'short', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Put Longa (K₁)', 'Strike Put Curta (K₂)'], strikeOffsets: [-5, 5],
  },
  bearCallSpread: {
    id: 'bearCallSpread', label: 'Bear Call Spread', labelPT: 'Trava de Baixa com Call',
    description: 'Crédito recebido apostando que o ativo fica abaixo do strike.',
    category: 'spreads', profile: 'renda', icon: '↘️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }, { type: 'call', side: 'long', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Call Curta (K₁)', 'Strike Call Longa (K₂)'], strikeOffsets: [-5, 5],
  },

  // ── Volatilidade ──
  straddle: {
    id: 'straddle', label: 'Long Straddle', labelPT: 'Straddle Comprado',
    description: 'Lucra com movimentos fortes em qualquer direção.',
    category: 'volatilidade', profile: 'neutro', icon: '⟺', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 1, strikeRef: 0 }, { type: 'put', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  strangle: {
    id: 'strangle', label: 'Long Strangle', labelPT: 'Strangle Comprado',
    description: 'Como o Straddle, mas mais barato — exige movimento maior.',
    category: 'volatilidade', profile: 'neutro', icon: '↔️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }, { type: 'call', side: 'long', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Put (K₁)', 'Strike Call (K₂)'], strikeOffsets: [-5, 5],
  },
  shortStraddle: {
    id: 'shortStraddle', label: 'Short Straddle', labelPT: 'Straddle Vendido',
    description: 'Lucra com mercado parado — risco ilimitado em ambos lados.',
    category: 'volatilidade', profile: 'renda', icon: '⊖', unlimitedLoss: true, stockUnits: 0,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }, { type: 'put', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  shortStrangle: {
    id: 'shortStrangle', label: 'Short Strangle', labelPT: 'Strangle Vendido',
    description: 'Range mais amplo que o Short Straddle — risco ilimitado.',
    category: 'volatilidade', profile: 'renda', icon: '⊗', unlimitedLoss: true, stockUnits: 0,
    legs: [{ type: 'put', side: 'short', qty: 1, strikeRef: 0 }, { type: 'call', side: 'short', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Strike Put (K₁)', 'Strike Call (K₂)'], strikeOffsets: [-5, 5],
  },
  butterflyCall: {
    id: 'butterflyCall', label: 'Butterfly Spread', labelPT: 'Borboleta',
    description: 'Máximo lucro se fechar exatamente no strike central.',
    category: 'volatilidade', profile: 'neutro', icon: '🦋', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'call', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'short', qty: 2, strikeRef: 1 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 2 },
    ],
    strikeLabels: ['Asa Esquerda (K₁)', 'Strike Central (K₂)', 'Asa Direita (K₃)'], strikeOffsets: [-10, 0, 10],
  },

  // ── Complexas ──
  ironCondor: {
    id: 'ironCondor', label: 'Iron Condor', labelPT: 'Iron Condor',
    description: 'Renda com mercado dentro de um range amplo — 4 pernas.',
    category: 'complexas', profile: 'renda', icon: '🦅', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'put', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'put', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 2 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 3 },
    ],
    strikeLabels: ['Put Longa (K₁)', 'Put Curta (K₂)', 'Call Curta (K₃)', 'Call Longa (K₄)'],
    strikeOffsets: [-10, -5, 5, 10],
  },

  // ── Razão / Backspread ──
  callRatioBackspread: {
    id: 'callRatioBackspread', label: 'Call Ratio Backspread', labelPT: 'Backspread de Call',
    description: 'Alta forte com vol comprada: vende 1 call e compra 2 acima. Lucro ilimitado na alta.',
    category: 'razao', profile: 'alta', icon: '⚖️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }, { type: 'call', side: 'long', qty: 2, strikeRef: 1 }],
    strikeLabels: ['Call Vendida (K₁)', 'Calls Compradas (K₂)'], strikeOffsets: [0, 10],
  },
  putRatioBackspread: {
    id: 'putRatioBackspread', label: 'Put Ratio Backspread', labelPT: 'Backspread de Put',
    description: 'Baixa forte com vol comprada: compra 2 puts e vende 1 acima. Grande lucro na queda.',
    category: 'razao', profile: 'baixa', icon: '⚖️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'long', qty: 2, strikeRef: 0 }, { type: 'put', side: 'short', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Puts Compradas (K₁)', 'Put Vendida (K₂)'], strikeOffsets: [-10, 0],
  },
  callFrontRatioSpread: {
    id: 'callFrontRatioSpread', label: 'Call Front Ratio Spread', labelPT: 'Front Ratio de Call',
    description: 'Neutro/leve alta vendendo vol: compra 1 call e vende 2 acima. Risco ilimitado se subir forte.',
    category: 'razao', profile: 'renda', icon: '⚖️', unlimitedLoss: true, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 1, strikeRef: 0 }, { type: 'call', side: 'short', qty: 2, strikeRef: 1 }],
    strikeLabels: ['Call Comprada (K₁)', 'Calls Vendidas (K₂)'], strikeOffsets: [0, 10],
  },
  putFrontRatioSpread: {
    id: 'putFrontRatioSpread', label: 'Put Front Ratio Spread', labelPT: 'Front Ratio de Put',
    description: 'Neutro/leve baixa vendendo vol: compra 1 put e vende 2 abaixo. Risco grande se cair forte.',
    category: 'razao', profile: 'renda', icon: '⚖️', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'short', qty: 2, strikeRef: 0 }, { type: 'put', side: 'long', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Puts Vendidas (K₁)', 'Put Comprada (K₂)'], strikeOffsets: [-10, 0],
  },

  // ── Borboletas & Condores Avançados ──
  ironButterfly: {
    id: 'ironButterfly', label: 'Iron Butterfly', labelPT: 'Borboleta de Ferro',
    description: 'Venda de vol com pico no strike central: vende straddle ATM e compra as asas.',
    category: 'borboletasAvancadas', profile: 'renda', icon: '🦋', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'put', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'put', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 2 },
    ],
    strikeLabels: ['Put Longa (K₁)', 'Strikes ATM (K₂)', 'Call Longa (K₃)'], strikeOffsets: [-10, 0, 10],
  },
  longCondor: {
    id: 'longCondor', label: 'Long Call Condor', labelPT: 'Condor de Call',
    description: 'Neutro de range: compra as pontas e vende o miolo (mesmo tipo). Lucro num intervalo amplo.',
    category: 'borboletasAvancadas', profile: 'neutro', icon: '🪁', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'call', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 2 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 3 },
    ],
    strikeLabels: ['Call Longa inf. (K₁)', 'Call Curta (K₂)', 'Call Curta (K₃)', 'Call Longa sup. (K₄)'],
    strikeOffsets: [-15, -5, 5, 15],
  },
  brokenWingButterfly: {
    id: 'brokenWingButterfly', label: 'Broken Wing Butterfly', labelPT: 'Borboleta Asa Quebrada',
    description: 'Borboleta com asas de larguras diferentes — pode zerar o risco de um lado se montada por crédito.',
    category: 'borboletasAvancadas', profile: 'neutro', icon: '🪶', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'call', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'short', qty: 2, strikeRef: 1 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 2 },
    ],
    strikeLabels: ['Asa Esq. (K₁)', 'Corpo (K₂)', 'Asa Dir. larga (K₃)'], strikeOffsets: [-10, 0, 20],
  },

  // ── Crédito Híbridas ──
  jadeLizard: {
    id: 'jadeLizard', label: 'Jade Lizard', labelPT: 'Jade Lizard',
    description: 'Vende put OTM + call spread de alta. Sem risco de alta se o crédito ≥ largura do call spread.',
    category: 'creditoHibridas', profile: 'renda', icon: '🦎', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'put', side: 'short', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 2 },
    ],
    strikeLabels: ['Put Vendida (K₁)', 'Call Vendida (K₂)', 'Call Comprada (K₃)'], strikeOffsets: [-10, 10, 20],
  },
  collar: {
    id: 'collar', label: 'Collar', labelPT: 'Colar',
    description: 'Ação + put protetora + call coberta. Trava a posição numa banda (piso e teto).',
    category: 'creditoHibridas', profile: 'hedge', icon: '⛓️', unlimitedLoss: false, stockUnits: 1,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }, { type: 'call', side: 'short', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Put Protetora (K₁)', 'Call Coberta (K₂)'], strikeOffsets: [-10, 10],
  },
  seagull: {
    id: 'seagull', label: 'Seagull', labelPT: 'Gaivota',
    description: 'Alta financiada: call spread comprado + put vendida. Reduz o custo da aposta de alta.',
    category: 'creditoHibridas', profile: 'alta', icon: '🕊️', unlimitedLoss: false, stockUnits: 0,
    legs: [
      { type: 'put', side: 'short', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'long', qty: 1, strikeRef: 1 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 2 },
    ],
    strikeLabels: ['Put Vendida (K₁)', 'Call Comprada (K₂)', 'Call Vendida (K₃)'], strikeOffsets: [-10, 5, 15],
  },
  riskReversal: {
    id: 'riskReversal', label: 'Risk Reversal', labelPT: 'Combo (Risk Reversal)',
    description: 'Combo direcional sintético: vende put e compra call. Replica alta com baixo/zero custo via skew.',
    category: 'creditoHibridas', profile: 'alta', icon: '🔄', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'short', qty: 1, strikeRef: 0 }, { type: 'call', side: 'long', qty: 1, strikeRef: 1 }],
    strikeLabels: ['Put Vendida (K₁)', 'Call Comprada (K₂)'], strikeOffsets: [-10, 10],
  },

  // ── Direcionais (Vol) ──
  strap: {
    id: 'strap', label: 'Strap', labelPT: 'Strap',
    description: 'Long vol com viés de alta: 2 calls + 1 put no mesmo strike. Ganha mais se subir.',
    category: 'direcionalVol', profile: 'alta', icon: '📈', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 2, strikeRef: 0 }, { type: 'put', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  strip: {
    id: 'strip', label: 'Strip', labelPT: 'Strip',
    description: 'Long vol com viés de baixa: 2 puts + 1 call no mesmo strike. Ganha mais se cair.',
    category: 'direcionalVol', profile: 'baixa', icon: '📉', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'put', side: 'long', qty: 2, strikeRef: 0 }, { type: 'call', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },

  // ── Sintéticas / Arbitragem ──
  boxSpread: {
    id: 'boxSpread', label: 'Box Spread', labelPT: 'Caixa',
    description: 'Renda fixa sintética: bull call spread + bear put spread nos mesmos strikes. Payoff travado.',
    category: 'sinteticas', profile: 'neutro', icon: '📦', unlimitedLoss: false, stockUnits: 0, locked: true,
    legs: [
      { type: 'call', side: 'long', qty: 1, strikeRef: 0 },
      { type: 'call', side: 'short', qty: 1, strikeRef: 1 },
      { type: 'put', side: 'long', qty: 1, strikeRef: 1 },
      { type: 'put', side: 'short', qty: 1, strikeRef: 0 },
    ],
    strikeLabels: ['Strike Inferior (K₁)', 'Strike Superior (K₂)'], strikeOffsets: [-5, 5],
  },
  conversion: {
    id: 'conversion', label: 'Conversion', labelPT: 'Conversão',
    description: 'Arbitragem de paridade: ação + put − call no mesmo strike. Payoff travado.',
    category: 'sinteticas', profile: 'neutro', icon: '🔁', unlimitedLoss: false, stockUnits: 1, locked: true,
    legs: [{ type: 'put', side: 'long', qty: 1, strikeRef: 0 }, { type: 'call', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  reversal: {
    id: 'reversal', label: 'Reversal', labelPT: 'Reversão',
    description: 'Inverso da conversão: vende ação + vende put + compra call. Payoff travado.',
    category: 'sinteticas', profile: 'neutro', icon: '🔃', unlimitedLoss: false, stockUnits: -1, locked: true,
    legs: [{ type: 'put', side: 'short', qty: 1, strikeRef: 0 }, { type: 'call', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  syntheticLong: {
    id: 'syntheticLong', label: 'Synthetic Long', labelPT: 'Sintético Comprado',
    description: 'Replica a ação com opções: compra call + vende put no mesmo strike.',
    category: 'sinteticas', profile: 'alta', icon: '🟢', unlimitedLoss: false, stockUnits: 0,
    legs: [{ type: 'call', side: 'long', qty: 1, strikeRef: 0 }, { type: 'put', side: 'short', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
  syntheticShort: {
    id: 'syntheticShort', label: 'Synthetic Short', labelPT: 'Sintético Vendido',
    description: 'Replica venda da ação: vende call + compra put no mesmo strike. Risco ilimitado na alta.',
    category: 'sinteticas', profile: 'baixa', icon: '🔴', unlimitedLoss: true, stockUnits: 0,
    legs: [{ type: 'call', side: 'short', qty: 1, strikeRef: 0 }, { type: 'put', side: 'long', qty: 1, strikeRef: 0 }],
    strikeLabels: ['Strike (K)'], strikeOffsets: [0],
  },
};
```

- [ ] **Step 4: Escrever os testes do registro**

Adicionar ao final de `src/lib/__tests__/strategies.test.ts`, e ajustar o import do topo (linha 2-5) para incluir os novos símbolos:

```ts
import {
  legIntrinsic, legSign, calculateStrategy, calculatePayoffCurve,
  getLongCallLegs, getBullCallSpreadLegs, type Leg,
  STRATEGY_DEFS, instantiateLegs, defaultStrikes, type StrategyId,
} from '@/lib/strategies';
```

```ts
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
```

- [ ] **Step 5: Rodar testes e confirmar verde**

Run: `npm test -- strategies`
Esperado: PASSAM. (Se "35 entradas" falhar, conferir se nenhuma entrada ficou faltando/duplicada no `STRATEGY_DEFS`.)

- [ ] **Step 6: Commit**

```bash
git add src/lib/strategies.ts src/lib/__tests__/strategies.test.ts
git commit -m "feat(strategies): registro STRATEGY_DEFS data-driven + 18 novas estrategias"
```

---

## Task 3: Migrar `StrategiesBuilder` para o registro (data-driven) e remover código morto

Substitui o `switch` de pernas e os painéis de strike hardcoded por um fluxo data-driven baseado em `STRATEGY_DEFS`. Adiciona as 5 categorias novas no grid. Ao final, remove `STRATEGY_META`/`StrategyMeta`/`StrategyName` de `strategies.ts` (agora sem uso).

**Files:**
- Modify: `src/components/StrategiesBuilder.tsx` (imports, estado, seletor, painel de strikes, instanciação)
- Modify: `src/lib/strategies.ts` (remover `StrategyName`, `StrategyMeta`, `STRATEGY_META`)

- [ ] **Step 1: Trocar imports e o config de categorias no topo do builder**

Em `src/components/StrategiesBuilder.tsx`, substituir o bloco de import de `@/lib/strategies` (linhas 16-45) por:

```tsx
import {
  StrategyId,
  StrategyCategory,
  STRATEGY_DEFS,
  instantiateLegs,
  defaultStrikes,
  calculateStrategy,
  calculatePayoffCurve,
} from '@/lib/strategies';
```

Substituir o array `CATEGORIES` (linhas 56-82) por:

```tsx
const CATEGORIES: { key: StrategyCategory; label: string; strategies: StrategyId[] }[] = [
  { key: 'puras', label: '📌 Posições Puras', strategies: ['longCall', 'shortCall', 'longPut', 'shortPut'] },
  { key: 'acao', label: '🏦 Com Ação (Stock)', strategies: ['coveredCall', 'protectivePut'] },
  { key: 'spreads', label: '📊 Spreads', strategies: ['bullCall', 'bearPut', 'bullPutSpread', 'bearCallSpread'] },
  { key: 'volatilidade', label: '🌊 Volatilidade', strategies: ['straddle', 'strangle', 'shortStraddle', 'shortStrangle', 'butterflyCall'] },
  { key: 'complexas', label: '🦅 Complexas', strategies: ['ironCondor'] },
  { key: 'razao', label: '⚖️ Razão / Backspread', strategies: ['callRatioBackspread', 'putRatioBackspread', 'callFrontRatioSpread', 'putFrontRatioSpread'] },
  { key: 'borboletasAvancadas', label: '🦋 Borboletas & Condores Avançados', strategies: ['ironButterfly', 'longCondor', 'brokenWingButterfly'] },
  { key: 'creditoHibridas', label: '🦎 Crédito Híbridas', strategies: ['jadeLizard', 'collar', 'seagull', 'riskReversal'] },
  { key: 'direcionalVol', label: '🎯 Direcionais (Vol)', strategies: ['strap', 'strip'] },
  { key: 'sinteticas', label: '🔁 Sintéticas / Arbitragem', strategies: ['boxSpread', 'conversion', 'reversal', 'syntheticLong', 'syntheticShort'] },
];
```

- [ ] **Step 2: Trocar o estado de strikes e a lógica de pernas**

Em `src/components/StrategiesBuilder.tsx`, substituir TODO o bloco de estado e derivações (linhas 95-178: de `const [strategy, ...` até o objeto `dualStrikeLabels` inclusive) por:

```tsx
  const [strategy, setStrategy] = useState<StrategyId>('straddle');

  // Market parameters
  const [S, setS]         = useState(100);
  const [sigma, setSigma] = useState(25);
  const [T, setT]         = useState(30);
  const r = SELIC_PCT;
  const q = DIVIDEND_YIELD_PCT;

  // Strikes da estrutura — array dimensionado pela estratégia selecionada
  const [strikes, setStrikes] = useState<number[]>(() => defaultStrikes(STRATEGY_DEFS.straddle, 100));

  function selectStrategy(id: StrategyId) {
    setStrategy(id);
    setStrikes(defaultStrikes(STRATEGY_DEFS[id], S));
  }
  function setStrike(i: number, v: number) {
    setStrikes((prev) => prev.map((s, j) => (j === i ? v : s)));
  }

  const def        = STRATEGY_DEFS[strategy];
  const stockUnits = def.stockUnits;
  const numLegs    = def.legs.length + (stockUnits !== 0 ? 1 : 0);
  const hasStock   = stockUnits !== 0;

  const legs = useMemo(() => {
    const d = STRATEGY_DEFS[strategy];
    // guarda o render transitório logo após trocar de estratégia
    const s = strikes.length === d.strikeOffsets.length ? strikes : defaultStrikes(d, S);
    return instantiateLegs(d, s);
  }, [strategy, strikes, S]);

  const result = useMemo(
    () => calculateStrategy(legs, S, T / 365, sigma / 100, r / 100, q / 100, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );

  const chartData = useMemo(
    () => calculatePayoffCurve(legs, S, T / 365, sigma / 100, r / 100, q / 100, 0.4, 150, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );

  const profileStyle = PROFILE_STYLE[def.profile] ?? PROFILE_STYLE.neutro;
```

- [ ] **Step 3: Atualizar o grid de seletores para usar `def`/`selectStrategy`**

Em `src/components/StrategiesBuilder.tsx`, dentro do `.map` dos cards (linhas ~197-236), trocar `STRATEGY_META[strat]` por `STRATEGY_DEFS[strat]` e `onClick={() => setStrategy(strat)}` por `onClick={() => selectStrategy(strat)}`:

```tsx
              {cat.strategies.map((strat) => {
                const m          = STRATEGY_DEFS[strat];
                const isSelected = strategy === strat;
                const ps         = PROFILE_STYLE[m.profile];
                return (
                  <button
                    key={strat}
                    onClick={() => selectStrategy(strat)}
```

(o restante do corpo do botão — `m.icon`, `m.label`, `m.labelPT`, `m.profile`, `m.unlimitedLoss` — permanece igual.)

- [ ] **Step 4: Atualizar o banner de info (usar `def`, `numLegs`, `hasStock`, `locked`)**

Em `src/components/StrategiesBuilder.tsx`, no banner (linhas ~243-273), trocar `meta.` por `def.` e usar as derivadas; adicionar o chip de "payoff travado". Substituir o bloco de badges (a partir de `<div className="flex flex-wrap gap-1.5 items-center">`) por:

```tsx
        <div className="flex flex-wrap gap-1.5 items-center">
          <span
            className="text-[10px] font-bold uppercase px-2 py-1 rounded-full border"
            style={{ color: profileStyle.color, background: 'white', borderColor: profileStyle.border }}
          >
            {def.profile}
          </span>
          <span className="text-[10px] text-dw-ink-muted border border-dw-rule-soft rounded-full px-2 py-1 bg-white">
            {numLegs} perna{numLegs !== 1 ? 's' : ''}
          </span>
          {def.unlimitedLoss && (
            <span className="text-[10px] font-bold text-red-700 bg-red-50 border border-red-300 rounded-full px-2 py-1">
              ⚠️ Risco Ilimitado
            </span>
          )}
          {hasStock && (
            <span className="text-[10px] text-purple-700 bg-purple-50 border border-purple-200 rounded-full px-2 py-1">
              🏦 Inclui posição em ação
            </span>
          )}
          {def.locked && (
            <span className="text-[10px] text-slate-700 bg-slate-100 border border-slate-300 rounded-full px-2 py-1">
              🔒 Payoff travado
            </span>
          )}
        </div>
```

E no cabeçalho do banner (linhas ~245-251) trocar `meta.icon`/`meta.label`/`meta.labelPT`/`meta.description` por `def.icon`/`def.label`/`def.labelPT`/`def.description`.

- [ ] **Step 5: Substituir o painel de strikes hardcoded pelo loop genérico**

Em `src/components/StrategiesBuilder.tsx`, substituir TODO o conteúdo do painel de strikes (linhas ~288-334 — os blocos `isSingleStrike`, `isDualStrike`, `isButterfly`, `isIronCondor`) por:

```tsx
            {def.strikeLabels.length === 0 ? (
              <p className="text-xs text-dw-ink-muted">Sem strikes (estrutura personalizada).</p>
            ) : (
              def.strikeLabels.map((label, i) => (
                <div key={`${strategy}-${i}`}>
                  {i > 0 && <div className="my-3" />}
                  <SliderControl
                    label={label}
                    value={strikes[i] ?? defaultStrikes(def, S)[i]}
                    min={50} max={200} step={1}
                    onChange={(v) => setStrike(i, v)}
                    suffix=" R$"
                  />
                </div>
              ))
            )}
```

- [ ] **Step 6: Rodar lint/build para garantir que o builder compila**

Run: `npm run lint` e `npm run build`
Esperado: sem erros. (Erros típicos a corrigir: referência remanescente a `meta`, `stockOffset`, `K1..K5`, `isSingleStrike`, ou imports não usados como `getStraddleLegs`.)

- [ ] **Step 7: Remover o código morto de `strategies.ts`**

Em `src/lib/strategies.ts`, remover as definições agora sem uso: o type `StrategyName` (linhas ~38-60), a interface `StrategyMeta` (linhas ~65-75) e o objeto `STRATEGY_META` (linhas ~79-182). Manter `Leg`, `legIntrinsic`, `legSign`, todas as funções `getXxxLegs` (usadas pelos testes) e o motor.

Run: `npm run lint` (confirmar que nada mais referencia os símbolos removidos) e `npm test`.
Esperado: PASSAM.

- [ ] **Step 8: Verificação manual no navegador**

Run: `npm run dev` e abrir `/estrategias`.
Conferir:
- As 10 categorias aparecem; clicar em algumas das 18 novas (ex.: Iron Butterfly → 3 sliders; Long Condor → 4 sliders; Strap → 1 slider; Collar → 2 sliders + chip "🏦 Inclui posição em ação"; Box Spread → chip "🔒 Payoff travado").
- A curva de payoff, os cards de Max Profit/Loss/Breakevens e as Gregas atualizam ao mexer nos sliders.
- Estratégias atuais (Long Call, Iron Condor, Butterfly, Covered Call) continuam idênticas.

- [ ] **Step 9: Commit**

```bash
git add src/components/StrategiesBuilder.tsx src/lib/strategies.ts
git commit -m "feat(estrategias): builder data-driven com seletor e painel de strikes genericos"
```

---

## Task 4: Propagar `stockUnits` para Monte Carlo e Hedging

Hoje `RiskSimulator`/`monte-carlo.ts` e `HedgingSimulator` ignoram a perna de ação. Propaga `stockUnits` para que Collar/Conversão/Reversão (e, de quebra, Covered Call/Protective Put) simulem corretamente nesses módulos.

**Files:**
- Modify: `src/lib/monte-carlo.ts` (param + termo de P&L da ação)
- Modify: `src/components/RiskSimulator.tsx` (prop + repasse)
- Modify: `src/components/HedgingSimulator.tsx` (prop + repasse + P&L da ação no caminho)
- Modify: `src/components/StrategiesBuilder.tsx` (passar `stockUnits` aos dois simuladores)
- Test: `src/lib/__tests__/monte-carlo.test.ts`

- [ ] **Step 1: Escrever o teste que falha (Monte Carlo com `stockUnits`)**

Adicionar ao final de `src/lib/__tests__/monte-carlo.test.ts`:

```ts
describe('runMonteCarlo — stockUnits', () => {
  const base = { S0: 100, mu: 0.3, sigma: 0.3, T: 1, steps: 50, numPaths: 8000, legs: [], r: 0.1, q: 0 };

  it('ação comprada → P&L médio positivo; vendida → negativo (mu>0)', () => {
    const long  = runMonteCarlo({ ...base, stockUnits: 1 });
    const short = runMonteCarlo({ ...base, stockUnits: -1 });
    expect(long.meanPnl).toBeGreaterThan(0);
    expect(short.meanPnl).toBeLessThan(0);
  });
});
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `npm test -- monte-carlo`
Esperado: FALHA — `MonteCarloParams` não aceita `stockUnits` (erro de tipo) e, mesmo ignorando, `meanPnl` seria ~0 com `legs: []`.

- [ ] **Step 3: Implementar em `monte-carlo.ts`**

Em `src/lib/monte-carlo.ts`, adicionar o campo na interface (após `q: number;`, linha ~35):

```ts
  stockUnits?: number; // +1 long, -1 short, 0 nenhum (default 0)
```

Na desestruturação da função (linha ~38-40), incluir `stockUnits = 0`:

```ts
export function runMonteCarlo({
  S0, mu, sigma, T, steps, numPaths, legs, r, q, stockUnits = 0
}: MonteCarloParams): MonteCarloResult {
```

No loop de P&L por caminho (em torno da linha 83-92), somar o termo da ação:

```ts
  for (let p = 0; p < numPaths; p++) {
    const ST = finalPrices[p];
    let payoff = 0;
    for (const leg of legs) {
      payoff += legIntrinsic(leg, ST) * leg.quantity * legSign(leg);
    }
    const pnl = payoff - entryCost + stockUnits * (ST - S0);
    pnlDistribution[p] = pnl;
    sumPnl += pnl;
    if (pnl > 0) wins++;
  }
```

- [ ] **Step 4: Rodar o teste do Monte Carlo e confirmar verde**

Run: `npm test -- monte-carlo`
Esperado: PASSA.

- [ ] **Step 5: Adicionar a prop `stockUnits` ao `RiskSimulator`**

Em `src/components/RiskSimulator.tsx`, adicionar à interface `Props` (linha ~15-22) `stockUnits: number;`, incluir no destructuring (linha 24) e no `mcParams` (linha ~28-38):

```tsx
interface Props {
  legs: Leg[];
  S0: number;
  T: number;
  sigma: number;
  r: number;
  q: number;
  stockUnits: number;
}

export default function RiskSimulator({ legs, S0, T, sigma, r, q, stockUnits }: Props) {
```

```tsx
  const mcParams: MonteCarloParams = useMemo(() => ({
    S0,
    mu: mu / 100,
    sigma: sigma / 100,
    T: T / 365,
    steps: T,
    numPaths,
    legs,
    r: r / 100,
    q: q / 100,
    stockUnits,
  }), [S0, mu, sigma, T, numPaths, legs, r, q, stockUnits]);
```

- [ ] **Step 6: Adicionar a prop `stockUnits` ao `HedgingSimulator`**

Em `src/components/HedgingSimulator.tsx`:

Interface `Props` (linha ~12-19) + destructuring (linha 21):

```tsx
interface Props {
  legs: Leg[];
  S0: number;
  T: number;
  sigma: number;
  r: number;
  q: number;
  stockUnits: number;
}

export default function HedgingSimulator({ legs, S0, T, sigma, r, q, stockUnits }: Props) {
```

`baseResult` (linha ~26-28) passa `stockUnits` (7º arg) para refletir o delta da ação:

```tsx
  const baseResult = useMemo(() => {
    return calculateStrategy(legs, S0, T / 365, sigma / 100, r / 100, q / 100, stockUnits);
  }, [legs, S0, T, sigma, r, q, stockUnits]);
```

No caminho do gamma scalping, passar `stockUnits` ao reavaliar (linha ~82) e somar o P&L da ação ao `portfolioPnl` (linhas ~82-89):

```tsx
      const timeRemaining = (T - t) / 365;
      const res = calculateStrategy(legs, nextS, timeRemaining > 0 ? timeRemaining : 0.0001, impliedVolDec, rDec, qDec, stockUnits);
      const newPortfolioValue = res.totalCost * multiplier;

      // P&L do portfólio vs. entrada (opções) + P&L da ação (stockUnits·ΔS)
      const portfolioPnl = newPortfolioValue - currentPortfolioCost + stockUnits * (nextS - S0) * multiplier;
```

Adicionar `stockUnits` às deps do `useMemo` do caminho (linha ~106):

```tsx
  }, [legs, S0, T, sigma, realizedVol, multiplier, r, q, stockUnits, baseResult.totalCost, baseResult.greeks.delta]);
```

- [ ] **Step 7: Passar `stockUnits` a partir do builder**

Em `src/components/StrategiesBuilder.tsx`, nas duas últimas linhas de render (linhas ~443-446), passar a prop:

```tsx
      <RiskSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} stockUnits={stockUnits} />

      <HedgingSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} stockUnits={stockUnits} />
```

- [ ] **Step 8: Rodar testes, lint e build**

Run: `npm test`, `npm run lint`, `npm run build`
Esperado: tudo verde.

- [ ] **Step 9: Verificação manual (stock nos simuladores)**

Run: `npm run dev` → `/estrategias` → selecionar **Collar**.
Conferir que "Risk Management & Monte Carlo" e "Delta Hedging" agora refletem a ação (ex.: o Delta Total do Collar fica próximo de +1 menos o delta da call vendida; a distribuição de P&L do Monte Carlo desloca com o preço do ativo).

- [ ] **Step 10: Commit**

```bash
git add src/lib/monte-carlo.ts src/components/RiskSimulator.tsx src/components/HedgingSimulator.tsx src/components/StrategiesBuilder.tsx src/lib/__tests__/monte-carlo.test.ts
git commit -m "feat(estrategias): propaga stockUnits para Monte Carlo e Hedging"
```

---

## Task 5: Guia Rápido — blocos das 5 novas categorias

Adiciona um segundo card de documentação na página, com blocos concisos para as 18 novas estratégias agrupadas em 5 categorias (1 exemplo B3 por categoria). Não altera o card existente.

**Files:**
- Modify: `src/app/estrategias/page.tsx` (inserir novo card após o card "Guia Rápido" existente)

- [ ] **Step 1: Inserir o novo card de documentação**

Em `src/app/estrategias/page.tsx`, inserir o bloco abaixo **imediatamente após** o fechamento do card existente (a `</div>` que encerra o `<div className="card mt-6">` do "Guia Rápido", logo antes do `</div>` final do `main-content`, em torno da linha 246):

```tsx
      {/* Documentação — Estratégias Avançadas (novas categorias) */}
      <div className="card mt-6">
        <h3 className="font-serif text-lg text-dw-ink mb-4">Estratégias Avançadas</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-dw-ink-mid leading-relaxed">

          {/* Coluna 1 */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>⚖️</span> Razão / Backspread
              </h4>
              <p className="mb-1"><strong>Call Ratio Backspread</strong> — vende 1 call e compra 2 acima (geralmente crédito). Viés de alta forte + long vol; lucro ilimitado p/ cima, perda limitada no strike das compradas.</p>
              <p className="mb-1"><strong>Put Ratio Backspread</strong> — compra 2 puts e vende 1 acima. Baixa forte + long vol; grande lucro na queda.</p>
              <p className="mb-1"><strong>Call Front Ratio Spread</strong> — compra 1 call e vende 2 acima. Neutro/leve alta, short vol; <strong>risco ilimitado</strong> p/ cima (call a descoberto).</p>
              <p className="mb-1"><strong>Put Front Ratio Spread</strong> — compra 1 put e vende 2 abaixo. Neutro/leve baixa, short vol; risco grande p/ baixo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$36. Call Ratio Backspread: vende 1 call R$36 e compra 2 calls R$40, montando por crédito para uma alta explosiva.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🦋</span> Borboletas &amp; Condores Avançados
              </h4>
              <p className="mb-1"><strong>Iron Butterfly</strong> — vende straddle ATM e compra as asas (put OTM + call OTM). Neutro, short vol; lucro máximo no strike central.</p>
              <p className="mb-1"><strong>Long Condor</strong> — compra as pontas e vende o miolo (mesmo tipo). Neutro; lucro num intervalo amplo, risco = débito.</p>
              <p className="mb-1"><strong>Broken Wing Butterfly</strong> — borboleta com asas de larguras diferentes; pode zerar o risco de um lado se montada por crédito.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$60. Iron Butterfly: vende call e put R$60, compra put R$56 e call R$64. Lucro máximo se fechar nos R$60.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🎯</span> Direcionais (Vol)
              </h4>
              <p className="mb-1"><strong>Strap</strong> — 2 calls + 1 put no mesmo strike. Long vol com viés de alta; ganho assimétrico p/ cima.</p>
              <p className="mb-1"><strong>Strip</strong> — 2 puts + 1 call no mesmo strike. Long vol com viés de baixa; ganho assimétrico p/ baixo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Prévia de balanço da BBAS3 a R$28. Strap: compra 2 calls R$28 e 1 put R$28, apostando em movimento forte com viés de alta.
              </div>
            </div>
          </div>

          {/* Coluna 2 */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🦎</span> Crédito Híbridas
              </h4>
              <p className="mb-1"><strong>Jade Lizard</strong> — put OTM vendida + call spread de alta. Neutro/alta, short vol; sem risco de alta se o crédito ≥ largura do call spread.</p>
              <p className="mb-1"><strong>Collar</strong> — ação + put protetora + call coberta. Neutro/protegido; trava a posição numa banda (piso e teto).</p>
              <p className="mb-1"><strong>Seagull</strong> — call spread comprado + put vendida (bullish). Alta financiada pela put.</p>
              <p className="mb-1"><strong>Risk Reversal</strong> — vende put OTM e compra call OTM. Direcional sintético via skew, quase sem custo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ITUB4 a R$32. Collar: tem a ação, compra put R$30 (piso) e vende call R$34 (teto), reduzindo o custo do seguro.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🔁</span> Sintéticas / Arbitragem
              </h4>
              <p className="mb-1"><strong>Box Spread</strong> — bull call spread + bear put spread nos mesmos strikes. Renda fixa sintética; payoff travado = Δstrikes.</p>
              <p className="mb-1"><strong>Conversão</strong> — ação + put − call no mesmo strike. Captura desvio de paridade put-call.</p>
              <p className="mb-1"><strong>Reversão</strong> — inverso da conversão (vende ação + vende put + compra call).</p>
              <p className="mb-1"><strong>Sintético Comprado/Vendido</strong> — replica a ação com opções (+call −put / −call +put), com menos capital.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Box Spread em BOVA11: bull call spread R$125/135 + bear put spread R$125/135 — payoff travado em R$10, equivalente a uma taxa pré-fixada.
              </div>
            </div>
          </div>

        </div>
      </div>
```

- [ ] **Step 2: Rodar build e verificar visualmente**

Run: `npm run build` (esperado: sem erros de JSX) e `npm run dev` → `/estrategias` → rolar até o novo card "Estratégias Avançadas".
Conferir que as 5 seções renderizam corretamente.

- [ ] **Step 3: Commit**

```bash
git add src/app/estrategias/page.tsx
git commit -m "docs(estrategias): guia rapido das estrategias avancadas (5 categorias)"
```

---

## Task 6: Limpeza e verificação final

Remove os arquivos de referência da raiz e roda a suíte completa.

**Files:**
- Delete: `payoff_engine.ts`, `estrategias_payoff.json` (raiz — untracked)

- [ ] **Step 1: Confirmar que nada no `src/` referencia os arquivos da raiz**

Run (grep): procurar por `payoff_engine` e `estrategias_payoff` em `src/`.
Esperado: nenhum resultado (eram apenas referência).

- [ ] **Step 2: Remover os arquivos**

```bash
git rm --cached payoff_engine.ts estrategias_payoff.json 2>$null; Remove-Item -Force payoff_engine.ts, estrategias_payoff.json
```

(Os arquivos são untracked; `git rm --cached` é tolerado se já não estiverem no índice. O essencial é removê-los do disco.)

- [ ] **Step 3: Suíte completa**

Run: `npm test` && `npm run lint` && `npm run build`
Esperado: testes verdes, lint sem novos erros, build OK.

- [ ] **Step 4: Commit final (se houver mudanças rastreadas)**

```bash
git add -A
git commit -m "chore(estrategias): remove arquivos de referencia (payoff_engine, catalogo)"
```

(Se os arquivos eram untracked e não há nada staged, pular o commit — a remoção do disco basta.)

---

## Self-Review

**Cobertura do spec:**
- Registro `STRATEGY_DEFS` + tipos → Task 2 ✓
- Painel de strikes genérico → Task 3 (Steps 2, 5) ✓
- `instantiateLegs` → Task 2 ✓
- `stockOffset` → `stockUnits` (motor) → Task 1 ✓; threading MC/Hedging → Task 4 ✓
- 18 definições → Task 2 (objeto completo) ✓
- 5 categorias no seletor → Task 3 (Step 1) ✓
- Guia Rápido → Task 5 ✓
- Testes (invariantes, instantiate, payoff, MC) → Tasks 1, 2, 4 ✓
- Limpeza dos arquivos da raiz → Task 6 ✓
- Preservar 16 atuais + `custom` vestigial → Task 2 (entradas) + Task 3 (Step 8 verificação) ✓

**Scan de placeholders:** nenhum "TBD/TODO"; todos os steps de código têm o código completo.

**Consistência de tipos/nomes:** `StrategyId`, `StrategyDef`, `LegTemplate`, `STRATEGY_DEFS`, `instantiateLegs`, `defaultStrikes`, `stockUnits` usados de forma idêntica entre as tasks. `calculateStrategy(...ustockUnits)` como 7º arg em Task 1, 2 (testes), 3 e 4. `MonteCarloParams.stockUnits` opcional em Task 4 (compatível com `monte-carlo.test.ts` existente, que não passa o campo).

**Riscos conhecidos:** Box/Conversão/Reversão exibem payoff ~plano (correto, sinalizado com `locked`); render transitório ao trocar estratégia é coberto pelo guard `strikes.length === def.strikeOffsets.length` em Task 3 Step 2.
