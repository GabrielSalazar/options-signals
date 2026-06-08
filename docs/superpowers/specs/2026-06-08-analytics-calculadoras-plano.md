# Plano de Implementação — Calculadoras de Análise (Analytics)

**Spec de referência:** `2026-06-08-analytics-calculadoras-design.md`
**Data:** 2026-06-08

---

## Divisão de responsabilidades

| Agente | Camada | Linguagem |
|---|---|---|
| **Gemini** | Backend | Python / FastAPI |
| **Claude** | Frontend | TypeScript / React |

As tarefas de cada agente são **independentes entre si** — backend e frontend podem ser desenvolvidos em paralelo. A única dependência real é que o frontend precisará do contrato do endpoint (tipos da resposta) antes de integrar; esse contrato está definido abaixo.

---

## Contrato compartilhado — `AssetAnalysisPayload`

```typescript
// src/lib/types/analytics.ts  (Claude cria; Gemini usa como referência)
export interface ChainItem {
  strike: number;
  preco: number;
  tipo: 'call' | 'put';
  negocios: number;
}

export interface AssetAnalysisPayload {
  ticker: string;
  preco_atual: number;
  hv_20: number;
  hv_60: number;
  ma20: number;
  ma50: number;
  ma200: number;
  sigma_20: number;
  rsi14: number;
  bollinger_pct_b: number;
  z_score_20: number;
  faixa_52s_min: number;
  faixa_52s_max: number;
  chain: ChainItem[];
}
```

**Endpoint:** `GET /api/market/analysis/{ticker}`
**Resposta de erro:** `{ detail: string }` com HTTP 404 se ticker não encontrado, 503 se provedor indisponível.

---

## TAREFAS — GEMINI (Backend Python)

### G-1 — Endpoint `/market/analysis/{ticker}`

**Arquivo:** `backend/api/routers/market.py`

**O que fazer:**
- Criar rota `GET /analysis/{ticker}` no router existente
- Chamar `fetch_brapi_historical(ticker, "6mo")` para obter OHLCV
- Calcular com funções já existentes em `backend/domain/`:
  - `estimar_iv_historica(df, 20)` → `hv_20`
  - `estimar_iv_historica(df, 60)` → `hv_60`
  - MA20, MA50, MA200 via `indicators.py` ou cálculo direto com pandas (rolling mean)
  - RSI₁₄ via `indicators.py` (função já existe)
  - Bollinger %B: `(preco - lower) / (upper - lower)` com banda de 20 períodos, 2σ
  - σ₂₀: desvio padrão dos log-retornos × √252 (janela 20 dias)
  - Z-Score vs MA20: `(preco_atual - ma20) / sigma_20`
  - Faixa 52 semanas: min/max dos últimos 252 pregões
- Chamar `_fetch_chain(ticker)` para obter a chain
- Retornar JSON conforme `AssetAnalysisPayload` acima

**Tratamento de erros:**
- Ticker não encontrado no brapi → HTTP 404
- Falha no provedor de chain → retornar `chain: []` (não falhar o endpoint inteiro)
- Dados históricos insuficientes (< 60 dias) → HTTP 422 com mensagem explicativa

**Exemplo de resposta esperada:**
```json
{
  "ticker": "PETR4",
  "preco_atual": 38.50,
  "hv_20": 0.32,
  "hv_60": 0.28,
  "ma20": 37.80,
  "ma50": 36.50,
  "ma200": 34.20,
  "sigma_20": 0.018,
  "rsi14": 58.3,
  "bollinger_pct_b": 0.65,
  "z_score_20": 0.39,
  "faixa_52s_min": 28.40,
  "faixa_52s_max": 44.60,
  "chain": [
    { "strike": 38.0, "preco": 1.45, "tipo": "call", "negocios": 320 }
  ]
}
```

**Critério de aceite:**
- `GET /api/market/analysis/PETR4` retorna 200 com todos os campos numéricos não-nulos
- `GET /api/market/analysis/TICKERINVALIDO` retorna 404
- `chain` nunca causa 500 (falha silenciosa com `[]`)

---

### G-2 — Teste do endpoint

**Arquivo:** `backend/tests/test_market_analysis.py` (criar se não existir)

**O que fazer:**
- Mockar `fetch_brapi_historical` com DataFrame de 300 linhas sintéticas (preços simulados)
- Mockar `_fetch_chain` com lista de 3 opções
- Verificar que todos os campos do `AssetAnalysisPayload` estão presentes na resposta
- Verificar HTTP 404 para ticker inválido
- Verificar que `chain: []` não causa erro 500

---

## TAREFAS — CLAUDE (Frontend TypeScript/React)

### C-1 — Tipos compartilhados

**Arquivo:** `src/lib/types/analytics.ts` (novo)

Criar as interfaces `AssetAnalysisPayload` e `ChainItem` conforme contrato acima. Exportar também:

```typescript
export type AssetVerdict = 'barato' | 'neutro' | 'caro';
export type OptionVerdict = 'barata' | 'neutra' | 'cara';
```

---

### C-2 — Solver de IV

**Arquivo:** `src/lib/black-scholes.ts` (adicionar função)

```typescript
export function impliedVol(
  marketPrice: number,
  S: number,
  K: number,
  T: number,
  r: number,
  type: 'call' | 'put',
): number
```

- Usar `hv` como chute inicial σ₀ = 0,3 (fallback fixo; o chamador passa HV₂₀ como σ₀ se quiser)
- Newton-Raphson: `σₙ₊₁ = σₙ − (BS(σₙ) − marketPrice) / Vega(σₙ)`
- Convergência: `|BS(σₙ) − marketPrice| < 1e-6`, máximo 100 iterações
- Fallback bisecção em `[0.001, 5.0]` se NR divergir ou Vega ≈ 0
- Retornar `NaN` se bisecção também falhar

**Testes** em `src/lib/__tests__/black-scholes.test.ts`:
- Round-trip: `impliedVol(callPrice(0.3, ...), ...) ≈ 0.3` com tolerância `1e-4`
- `impliedVol` converge em < 20 iterações para casos normais
- Retorna `NaN` para `marketPrice = 0` (opção sem valor)

---

### C-3 — Lógica de score do ativo

**Arquivo:** `src/lib/asset-analysis.ts` (novo)

```typescript
export function scoreAsset(payload: AssetAnalysisPayload): {
  score: number;        // 0–10
  verdict: AssetVerdict;
  breakdown: Record<string, number>; // pontos por indicador
}
```

Tabela de pontuação (conforme spec):

| Indicador | 0 pts | 1 pt | 2 pts |
|---|---|---|---|
| Posição 52s (`pos52s`) | > 50% | 30–50% | < 30% |
| Distância MAs | preço > MA20 e MA50 | preço < MA20 OU MA50 | preço < MA20 E MA50 |
| RSI₁₄ | > 55 | 30–55 | < 30 |
| Bollinger %B | > 0,5 | 0,2–0,5 | < 0,2 |
| Z-Score MA20 | > 0 | -1–0 | < -1 |

Onde `pos52s = (preco_atual - faixa_52s_min) / (faixa_52s_max - faixa_52s_min)`.

Thresholds finais: 0–3 → `'barato'`, 4–6 → `'neutro'`, 7–10 → `'caro'`.

**Testes** em `src/lib/__tests__/asset-analysis.test.ts`:
- Payload "barato" (RSI=15, %B=0.05, z=-1.5, pos52s=10%) → `verdict = 'barato'`
- Payload "neutro" → `verdict = 'neutro'`
- Payload "caro" (RSI=80, %B=0.9, z=1.2) → `verdict = 'caro'`

---

### C-4 — Hook de dados com cache

**Arquivo:** `src/hooks/useAssetAnalysis.ts` (novo)

```typescript
export function useAssetAnalysis(ticker: string | null): {
  data: AssetAnalysisPayload | null;
  loading: boolean;
  error: string | null;
}
```

- Cache em `Map<string, { payload, fetchedAt }>` fora do componente (módulo-level)
- TTL: 5 minutos — se `Date.now() - fetchedAt < 300_000` reutiliza sem nova requisição
- `ticker = null` não dispara fetch

---

### C-5 — Seletor rápido de tickers

**Arquivo:** `src/components/TickerSelector.tsx` (novo)

- Busca `SELECT DISTINCT ticker FROM signals ORDER BY timestamp DESC LIMIT 20` via Supabase client existente
- Renderiza `<input>` com `<datalist>` — digitação livre + sugestões dos sinais
- Props: `value: string`, `onChange: (ticker: string) => void`

---

### C-6 — Painel A: Calculadora do Ativo

**Arquivo:** `src/components/AssetAnalyzer.tsx` (novo)

- Usa `useAssetAnalysis` e `scoreAsset`
- Renderiza: barra faixa 52s, chips MAs, gauge RSI, barra Bollinger, z-score com semáforo
- Badge de veredicto: `🟢 Barato` / `🟡 Neutro` / `🔴 Caro`
- Expõe `verdict: AssetVerdict` via prop `onVerdict` para o alerta cruzado

---

### C-7 — Painel B: Calculadora de Opção

**Arquivo:** `src/components/OptionAnalyzer.tsx` (novo)

Entradas: `tipo C/P`, `strike (number)`, `vencimento (date)`, `preço de mercado (number)`.
Reutiliza o payload já carregado pelo Painel A (passa via props: `payload: AssetAnalysisPayload | null`).

Exibe:
- IV calculada (`impliedVol`) vs HV₂₀ — barra comparativa
- Preço justo BS (`callPrice` / `putPrice` com σ = HV₂₀) vs preço digitado
- Greeks: Delta, Theta (por dia), Vega — via `calcAll`
- Break-even: call → `K + prêmio`, put → `K − prêmio`
- Moneyness (% OTM/ITM), DTE
- IV Rank na chain: percentil da IV calculada entre as IVs de todas as opções da chain com `negocios > 0`

Veredicto: `IV > HV₂₀ × 1,2` → `🔴 Cara` / `IV < HV₂₀ × 0,8` → `🟢 Barata` / senão `🟡 Neutra`
Expõe `verdict: OptionVerdict` via prop `onVerdict`.

---

### C-8 — Painel C: HV vs IV

**Arquivo:** `src/components/VolatilityPanel.tsx` (novo, substitui `VolatilitySkew`)

- Barras duplas HV₂₀ e HV₆₀ (Recharts `BarChart`)
- Scatter dos strikes da chain com IV calculada por NR para cada item com `negocios > 0`, calls e puts em cores distintas (Recharts `ScatterChart`)
- Props: `payload: AssetAnalysisPayload`, `selectedIV?: number`

Atualizar `src/app/analytics/page.tsx`: substituir `<VolatilitySkew>` por `<VolatilityPanel>`.

---

### C-9 — Alerta cruzado

**Arquivo:** `src/components/AnalyticsCrossAlert.tsx` (novo)

```typescript
interface Props {
  assetVerdict: AssetVerdict | null;
  optionVerdict: OptionVerdict | null;
}
```

Renderiza banner verde apenas quando `assetVerdict === 'barato' && optionVerdict === 'barata'`:

> `✦ Ponto de entrada: ativo subavaliado com IV baixa — custo de compra de call reduzido`

Caso contrário renderiza `null`.

---

### C-10 — Integração na página `/analytics`

**Arquivo:** `src/app/analytics/page.tsx`

Adicionar seção "Calculadoras" após os cards existentes:

```
[TickerSelector]          ← ticker compartilhado entre painéis
[AnalyticsCrossAlert]     ← alerta cruzado
[AssetAnalyzer]  [OptionAnalyzer]   ← layout grid 2 colunas em desktop
[VolatilityPanel]         ← largura total
```

State local: `ticker`, `assetVerdict`, `optionVerdict` — gerenciados na page, passados como props.

---

## Ordem de execução sugerida

```
Paralelo:
  Gemini:  G-1 → G-2
  Claude:  C-1 → C-2 → C-3 → C-4 (independentes do backend)
           C-5 → C-6 → C-7 → C-8 → C-9 → C-10 (após C-1/C-2/C-3/C-4)

Integração final:
  C-10 integra tudo + testa com endpoint real do G-1
```

**Ponto de integração:** quando G-1 estiver pronto, C-7 e C-8 podem ser testados com dados reais. Antes disso, usar mock `AssetAnalysisPayload` nos componentes.

---

## Critérios de aceite globais

- [ ] `GET /api/market/analysis/PETR4` retorna 200 com todos os campos
- [ ] Round-trip IV: `impliedVol(callPrice(0.3)) ≈ 0.3` com tolerância `1e-4`
- [ ] `scoreAsset` cobre os três vereditos nos testes
- [ ] Painel A exibe veredicto para PETR4 sem erro
- [ ] Painel B calcula IV e break-even para uma opção real da chain
- [ ] Painel C renderiza scatter com IVs reais (não mock)
- [ ] Alerta cruzado aparece e some conforme condições
- [ ] Cache: segunda chamada com mesmo ticker não dispara nova requisição por 5 min
- [ ] `VolatilitySkew` substituído; sem referências ao mock restantes
