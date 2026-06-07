# Design — Construtor de Estratégias data-driven (+18 estratégias)

**Data:** 2026-06-07
**Status:** Aprovado (aguardando revisão do spec)

## Contexto e objetivo

A página **Estratégias** ([src/app/estrategias/page.tsx](../../../src/app/estrategias/page.tsx)) usa o componente
[StrategiesBuilder](../../../src/components/StrategiesBuilder.tsx), que hoje oferece **16 estratégias**
(+ `custom`) definidas em [src/lib/strategies.ts](../../../src/lib/strategies.ts).

O objetivo é **adicionar 18 novas estratégias** de vencimento único ao construtor, de forma que sejam
totalmente simuláveis (curva de payoff, max profit/loss, breakevens, Gregas, Monte Carlo e Hedging),
reusando o motor Black-Scholes existente.

### Decisões já tomadas (brainstorming)

1. **Motor de preço:** manter o motor **Black-Scholes** atual *intacto* (prêmios derivados de S, σ, T, r, q —
   o usuário não digita prêmios). O `payoff_engine.ts` colocado na raiz serve **apenas como referência da
   estrutura** das estratégias (pernas, `strikeRef`, ratios). Após a integração, `payoff_engine.ts` e
   `estrategias_payoff.json` são **descartados** da raiz.
2. **Estratégias de tempo adiadas:** Calendar Spread, Diagonal Spread e PMCC têm pernas em vencimentos
   diferentes (`requerModeloPreco`) — o motor de vencimento único não as modela corretamente. Ficam para
   uma **2ª etapa** (modelagem de duplo vencimento). Não entram neste escopo.
3. **Arquitetura:** Abordagem **A — registro genérico orientado a dados**. Cada estratégia vira uma linha
   de dados (template); um motor genérico lê os dados para montar pernas e renderizar o painel de strikes.

### Escopo — as 18 estratégias (37 catálogo − 16 atuais − 3 adiadas = 18)

| Categoria | Estratégias |
|---|---|
| Razão / Backspread (4) | Call Ratio Backspread, Put Ratio Backspread, Call Front Ratio Spread, Put Front Ratio Spread |
| Borboletas & Condores Avançados (3) | Iron Butterfly, Long Condor, Broken Wing Butterfly |
| Crédito Híbridas (4) | Jade Lizard, Collar, Seagull, Risk Reversal |
| Direcionais (Vol) (2) | Strap, Strip |
| Sintéticas / Arbitragem (5) | Box Spread, Conversão, Reversão, Sintético Comprado, Sintético Vendido |

**Fora de escopo:** Calendar Spread, Diagonal Spread, PMCC (2ª etapa).

## Arquitetura

### 1. Registro único (`STRATEGY_DEFS`)

Em `strategies.ts`, fundir o `STRATEGY_META` atual com os templates de pernas num registro único.
O tipo `Leg` **público não muda** (continua `{ type, strike, side, quantity }`), preservando
`RiskSimulator`, `HedgingSimulator` e `monte-carlo.ts`.

```ts
interface LegTemplate {
  type: 'call' | 'put';
  side: 'long' | 'short';
  qty: number;
  strikeRef: number;          // índice no array de strikes ASCENDENTE
}

interface StrategyDef {
  id: StrategyName;
  label: string;              // nome de mercado (EN)
  labelPT: string;
  description: string;
  category: StrategyCategory;
  profile: StrategyProfile;   // alta | baixa | neutro | renda | hedge
  icon: string;
  unlimitedLoss: boolean;     // dirige o badge ⚠️
  stockUnits: number;         // +1 / -1 / 0  (substitui hasStockComponent + stockOffset)
  legs: LegTemplate[];        // SÓ as pernas de opção; a ação entra via stockUnits
  strikeLabels: string[];     // 1 rótulo por strikeRef distinto (ordem ascendente)
  strikeOffsets: number[];    // default de cada strike como offset de S (ascendente)
  locked?: boolean;           // payoff travado (box/conversão/reversão) → dica na UI
}
```

`numLegs` e `hasStockComponent` passam a ser **derivados**:
`numLegs = legs.length + (stockUnits !== 0 ? 1 : 0)`, `hasStockComponent = stockUnits !== 0`.

As **16 estratégias atuais migram** para o mesmo formato (um único caminho de dados). O `STRATEGY_META`
antigo deixa de existir como fonte separada — vira derivação ou é absorvido por `STRATEGY_DEFS`.

**Preservar os defaults atuais** das 16 ao migrar (base S=100 de hoje → offsets): strike único `[0]`;
dual `[-5, +5]`; butterfly `[-10, 0, +10]`; iron condor `[-10, -5, +5, +10]`. Rótulos e ícones atuais
mantidos. A entrada vestigial **`custom`** (não exibida em nenhuma categoria do grid hoje) permanece com
`legs: []`, `strikeLabels: []`, `strikeOffsets: []` — continua fora do seletor; `instantiateLegs` devolve
`[]` para ela, preservando o comportamento atual.

### 2. Painel de strikes genérico (`StrategiesBuilder`)

Substituir estados fixos `K1..K5` e os branches `isSingleStrike / isDualStrike / isButterfly /
isIronCondor` por **um estado `strikes: number[]`** e **um loop**:

```tsx
const [strikes, setStrikes] = useState<number[]>(() => defaultStrikes(def, S));
const setStrike = (i: number, v: number) =>
  setStrikes(prev => prev.map((s, j) => (j === i ? v : s)));

// reinicializa ao trocar de estratégia
useEffect(() => { setStrikes(defaultStrikes(def, S)); }, [strategy]);

// render:
{def.strikeLabels.map((label, i) => (
  <SliderControl key={i} label={label} value={strikes[i]} min={50} max={200} step={1}
                 onChange={v => setStrike(i, v)} suffix=" R$" />
))}
```

`defaultStrikes(def, S) = def.strikeOffsets.map(o => Math.round(S + o))`.

`S`, `σ`, `T` permanecem como estados próprios. O `r` (Selic) e `q` seguem fixos como hoje.

### 3. Montagem das pernas (`instantiateLegs`)

```ts
export function instantiateLegs(def: StrategyDef, strikes: number[]): Leg[] {
  return def.legs.map(l => ({
    type: l.type, side: l.side, quantity: l.qty, strike: strikes[l.strikeRef],
  }));
}
```

O `useMemo` de `legs` no builder passa a ser `instantiateLegs(def, strikes)` — substitui o `switch`.

### 4. Generalização `stockUnits` (com sinal)

`stockOffset: boolean` → `stockUnits: number` (default `0`) em `calculateStrategy` e `calculatePayoffCurve`:

- delta da posição: `delta += stockUnits` (era `if (stockOffset) delta += 1`)
- P&L da ação: `stockUnits * (s - S_center)` (era `stockOffset ? (s - S_center) : 0`)
- custo de entrada das opções inalterado (custo da ação segue "afundado"/não somado, mantendo a convenção atual)

**Threading para Monte Carlo e Hedging:** hoje `RiskSimulator`/`monte-carlo.ts` e `HedgingSimulator`
chamam o motor **sem** o offset de ação — ignoram a perna de stock. Para Collar/Conversão/Reversão
simularem corretamente (e corrigindo de quebra Covered Call/Protective Put nesses dois simuladores),
adicionar `stockUnits` ao fluxo:

- `monte-carlo.ts`: novo parâmetro `stockUnits` em `MonteCarloParams`; no cálculo de PnL por caminho,
  somar `stockUnits * (ST - S0)` ao payoff (o custo de entrada da ação não entra, pois o termo já mede o
  ganho a partir de S0 — mesma convenção da curva de payoff).
- `RiskSimulator` e `HedgingSimulator`: receber `stockUnits` por prop (derivado de `def.stockUnits`) e
  repassá-lo.

### 5. Categorias no seletor (`StrategiesBuilder` / `StrategyCategory`)

Estender o type `StrategyCategory` e o array `CATEGORIES` com 5 categorias novas, **mantendo as 5 atuais**
(`puras`, `acao`, `spreads`, `volatilidade`, `complexas`) intactas:

| key | label | estratégias |
|---|---|---|
| `razao` | ⚖️ Razão / Backspread | callRatioBackspread, putRatioBackspread, callFrontRatioSpread, putFrontRatioSpread |
| `borboletasAvancadas` | 🦋 Borboletas & Condores Avançados | ironButterfly, longCondor, brokenWingButterfly |
| `creditoHibridas` | 🦎 Crédito Híbridas | jadeLizard, collar, seagull, riskReversal |
| `direcionalVol` | 🎯 Direcionais (Vol) | strap, strip |
| `sinteticas` | 🔁 Sintéticas / Arbitragem | boxSpread, conversion, reversal, syntheticLong, syntheticShort |

### 6. Guia Rápido (rodapé de `estrategias/page.tsx`)

Adicionar blocos concisos para as 5 novas categorias no mesmo estilo visual existente
(nome EN/PT, badge de perfil, badge crédito/débito, 1 linha de descrição + 1 exemplo curto B3),
espelhando as tabelas da documentação. Mais enxutos que os blocos atuais para não inflar a página.

## Definições das 18 estratégias (fonte: payoff_engine.ts)

`strikeRef` indexa o array de strikes **ascendente**. `qty` em lotes. `stockUnits` default 0.

```
callRatioBackspread   strikes:2  legs: short call@0 x1, long call@1 x2
  labels: ['Call Vendida (K₁)','Calls Compradas (K₂)']   offsets: [0, +10]   profile: alta
putRatioBackspread    strikes:2  legs: long put@0 x2, short put@1 x1
  labels: ['Puts Compradas (K₁)','Put Vendida (K₂)']     offsets: [-10, 0]   profile: baixa
callFrontRatioSpread  strikes:2  legs: long call@0 x1, short call@1 x2     unlimitedLoss: true
  labels: ['Call Comprada (K₁)','Calls Vendidas (K₂)']   offsets: [0, +10]   profile: renda
putFrontRatioSpread   strikes:2  legs: long put@1 x1, short put@0 x2
  labels: ['Puts Vendidas (K₁)','Put Comprada (K₂)']     offsets: [-10, 0]   profile: renda
ironButterfly         strikes:3  legs: long put@0, short put@1, short call@1, long call@2
  labels: ['Put Longa (K₁)','Strikes ATM (K₂)','Call Longa (K₃)']  offsets: [-10,0,+10]  profile: renda
longCondor            strikes:4  legs: long call@0, short call@1, short call@2, long call@3
  labels: ['Call Longa inf. (K₁)','Call Curta (K₂)','Call Curta (K₃)','Call Longa sup. (K₄)']
  offsets: [-15,-5,+5,+15]  profile: neutro
brokenWingButterfly   strikes:3  legs: long call@0, short call@1 x2, long call@2   (asa direita larga)
  labels: ['Asa Esq. (K₁)','Corpo (K₂)','Asa Dir. larga (K₃)']  offsets: [-10,0,+20]  profile: neutro
jadeLizard            strikes:3  legs: short put@0, short call@1, long call@2
  labels: ['Put Vendida (K₁)','Call Vendida (K₂)','Call Comprada (K₃)']  offsets: [-10,+10,+20]  profile: renda
collar                strikes:2  stockUnits:+1  legs: long put@0, short call@1
  labels: ['Put Protetora (K₁)','Call Coberta (K₂)']     offsets: [-10,+10]  profile: hedge
seagull               strikes:3  legs: short put@0, long call@1, short call@2
  labels: ['Put Vendida (K₁)','Call Comprada (K₂)','Call Vendida (K₃)']  offsets: [-10,+5,+15]  profile: alta
riskReversal          strikes:2  legs: short put@0, long call@1
  labels: ['Put Vendida (K₁)','Call Comprada (K₂)']      offsets: [-10,+10]  profile: alta
strap                 strikes:1  legs: long call@0 x2, long put@0 x1
  labels: ['Strike (K)']                                  offsets: [0]        profile: alta
strip                 strikes:1  legs: long put@0 x2, long call@0 x1
  labels: ['Strike (K)']                                  offsets: [0]        profile: baixa
boxSpread             strikes:2  legs: long call@0, short call@1, long put@1, short put@0   locked
  labels: ['Strike Inferior (K₁)','Strike Superior (K₂)']  offsets: [-5,+5]   profile: neutro
conversion            strikes:1  stockUnits:+1  legs: long put@0, short call@0   locked
  labels: ['Strike (K)']                                  offsets: [0]        profile: neutro
reversal              strikes:1  stockUnits:-1  legs: short put@0, long call@0   locked
  labels: ['Strike (K)']                                  offsets: [0]        profile: neutro
syntheticLong         strikes:1  legs: long call@0, short put@0
  labels: ['Strike (K)']                                  offsets: [0]        profile: alta
syntheticShort        strikes:1  legs: short call@0, long put@0               unlimitedLoss: true
  labels: ['Strike (K)']                                  offsets: [0]        profile: baixa
```

Ícones sugeridos: ratios `⚖️`, iron butterfly `🦋`, condor `🪁`, broken wing `🪶`, jade lizard `🦎`,
collar `⛓️`, seagull `🕊️`, risk reversal `🔄`, strap `📈`, strip `📉`, box `📦`, conversão `🔁`,
reversão `🔃`, sintético comprado `🟢`, sintético vendido `🔴`. (Ajustáveis na implementação.)

## Testes ([src/lib/__tests__/strategies.test.ts](../../../src/lib/__tests__/strategies.test.ts))

- **Compatibilidade:** os testes atuais permanecem (a troca `stockOffset`→`stockUnits` é compatível —
  default `0`, `q` segue sendo o 6º argumento de `calculateStrategy`).
- **Novos:**
  - `instantiateLegs`: strikes distintos (iron butterfly → 4 pernas em 3 strikes), qty de ratio
    (call ratio backspread → 2 calls longas), sinal de stock (reversão → `stockUnits === -1`).
  - Payoff/extremos de algumas novas: Box ≈ travado (max profit ≈ max loss, sem cauda), Sintético
    Comprado ≈ payoff linear ≈ ação, Strap com alta ilimitada (`maxProfit === 'Infinito'`),
    Call Front Ratio com perda ilimitada (`maxLoss === 'Ilimitado'`).

## Limpeza

Após integração e testes verdes, **remover** da raiz: `payoff_engine.ts` e `estrategias_payoff.json`.

## Riscos e mitigações

- **Regressão nas 16 atuais:** migrá-las ao registro com os mesmos strikes/labels de hoje; testes +
  verificação visual de algumas (long call, iron condor, butterfly, covered call).
- **Box/Conversão/Reversão planas:** sob vol uniforme do BS o payoff é ~constante — *correto* (arbitragem
  travada). Sinalizar com `locked` + dica "payoff travado" na UI para não parecer bug.
- **Strikes independentes:** arrastar um slider "fora de ordem" pode tornar os rótulos imprecisos, mas a
  matemática segue consistente (mesmo comportamento de hoje).
- **Assinatura de `monte-carlo.ts`:** mudança contida (+1 parâmetro com default); atualizar os 2 call sites.

## Critérios de sucesso

1. As 18 estratégias aparecem no seletor, agrupadas nas 5 novas categorias.
2. Cada uma renderiza o nº correto de sliders de strike e simula payoff/extremos/breakevens/Gregas
   coerentes; Collar/Conversão/Reversão refletem a perna de ação no payoff **e** no Monte Carlo/Hedging.
3. As 16 estratégias atuais continuam idênticas (sem regressão).
4. `npm test` (Vitest) e o lint passam; `payoff_engine.ts`/`estrategias_payoff.json` removidos.
