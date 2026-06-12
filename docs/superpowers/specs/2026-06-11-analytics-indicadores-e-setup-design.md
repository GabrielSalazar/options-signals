# Design — Sub-página "Indicadores e Setup" (`/analytics/indicadores`)

Data: 2026-06-11
Status: aprovado (aguardando revisão do spec)

## 1. Objetivo

Criar uma sub-página de `/analytics` chamada **"Indicadores e Setup"** onde, ao digitar um ticker da B3, o usuário vê em tempo real:

1. **Indicadores técnicos mais usados (ações)** — momento, tendência, reversão e volatilidade.
2. **Setups operacionais (price action / tape)** mais difundidos no mercado BR.
3. Uma **leitura de mercado** que indica se o momento favorece operar o ativo **ou opções** dele (vol rica/barata, expected move), **sem recomendar operação concreta**.

Fora de escopo: estratégias estruturadas (já existem em `/estrategias`) e qualquer sugestão de operação específica.

## 2. Decisões de produto (definidas no brainstorm)

- **Dados sem fonte hoje** (Open Interest/Max Pain, Put/Call por OI, aluguel BTC / short interest / days-to-cover, IV Rank 252d): exibidos como painéis **"em breve"** — presentes no layout, marcados como indisponíveis, nunca quebram.
- **Setups**: implementar **todos** os difundidos — Larry Williams 9.1/9.2/9.3, Inside Bar, Rompimento de máxima/mínima, Engolfo (bullish/bearish), Pin Bar/Martelo (e Shooting Star), Doji, Pullback em MME9/MME21.
- **Card de sugestão**: vira **"Leitura para opções"** — vol rica/barata + expected move + viés "favorece comprar/vender prêmio". Sem strike/operação concreta.

## 3. Arquitetura (Abordagem A — endpoint dedicado)

```
Frontend  /analytics/indicadores  ──fetch──▶  GET /market/indicators/{ticker}
  page.tsx + components/indicators/*                     │
  hooks/useIndicators.ts                                 ▼
  lib/types/indicators.ts                    market.py monta payload
                                              ├─ _fetch_historical_with_fallback (6mo OHLC)
                                              ├─ calcular_indicadores(df)  [já existe]
                                              ├─ domain/setups.py  [novo, puro]
                                              └─ leitura de vol (σ20 / chain ATM)
```

Não altera `/market/analysis` nem `AssetAnalyzer` (e seus testes). Reusa o pipeline de indicadores e o fetch histórico já testados.

## 4. Backend

### 4.1 `backend/domain/setups.py` (novo, puro e testável)

Cada detector recebe o `df` (com colunas OHLCV + indicadores de `calcular_indicadores`) e retorna:

```python
@dataclass
class SetupResult:
    nome: str            # "Larry 9.1", "Inside Bar", ...
    status: str          # "ativo" | "armado" | "inativo"
    vies: str            # "alta" | "baixa" | "neutro"
    descricao: str       # frase curta explicando o estado atual
```

Definições determinísticas (avaliadas no candle mais recente; índices em pandas: `-1` = atual, `-2` = anterior):

- **Tendência da MME9**: `slope = ema9[-1] - ema9[-4]`; `up` se `slope > 0`, `down` se `slope < 0`.
- **Larry 9.1 (continuação por rompimento)**:
  - Compra (ativo): MME9 `up` **e** `close[-1] > high[-2]` (rompeu a máxima do candle anterior).
  - Venda (ativo): MME9 `down` **e** `close[-1] < low[-2]`.
  - Caso contrário: inativo.
- **Larry 9.2 (pivô de retorno à média)**:
  - Compra armado: MME9 `up` **e** `low[-1] < low[-2]` (candle de pullback) → status `armado`, alvo = `high[-1]`.
  - Compra ativo (disparado): MME9 `up`, `low[-2] < low[-3]` (anterior era pullback) **e** `high[-1] > high[-2]`.
  - Simétrico para venda em MME9 `down`.
- **Larry 9.3 (continuação após 2 pullbacks)**: MME9 `up` **e** dois candles consecutivos de mínimas decrescentes (`low[-1] < low[-2] < low[-3]`) → status `armado`, alvo = `high[-1]`. Simétrico para baixa.
- **Inside Bar**: `high[-1] <= high[-2]` **e** `low[-1] >= low[-2]` → ativo; viés = tendência da MME9 (neutro se lateral).
- **Rompimento de máxima/mínima (janela 20)**: usa `resistencia_20`/`suporte_20` já calculados. `close[-1] > resistencia_20[-2]` → rompimento de máxima (alta); `close[-1] < suporte_20[-2]` → mínima (baixa).
- **Engolfo**: bullish = candle[-1] verde cujo corpo cobre o corpo do candle[-2] vermelho (`open[-1] <= close[-2]` e `close[-1] >= open[-2]`); bearish simétrico.
- **Pin Bar / Martelo**: corpo = `|close-open|`; sombra inferior `>= 2×corpo` e corpo no terço superior do range → Martelo (alta). Shooting Star simétrico (sombra superior).
- **Doji**: `|close[-1]-open[-1]| <= 0.1 × (high[-1]-low[-1])` → indecisão (neutro).
- **Pullback em MME9/MME21**: em tendência (`ema9 > ema21` para alta), preço tocou a média (`low[-1] <= ema9[-1] <= high[-1]` **ou** distância `< 0.5×ATR`) → ativo, viés a favor da tendência.

Função agregadora `detectar_setups(df) -> list[SetupResult]` retorna todos, na ordem acima.

> Nota: são interpretações simplificadas e determinísticas, adequadas a um **flag de estado** numa página de leitura (não a um robô de execução). Os testes fixam o comportamento.

### 4.2 `GET /market/indicators/{ticker}` (em `market.py`)

Reusa `_fetch_historical_with_fallback(ticker)` (6 meses) e `calcular_indicadores(df)`. Erros: 404 (sem dados), 422 (`< 60` pregões), como `/market/analysis`.

Monta e retorna o payload (seção 5). A **leitura de vol**:
- **Expected move** (sempre disponível, base HV): `em = preco_atual × σ20 × sqrt(DTE/252)`, com `DTE` do próximo vencimento mensal B3 (3ª sexta). Faixa `±1σ = [preco−em, preco+em]`.
- **IV ATM** (quando a chain permitir): pega o próximo vencimento, strike ATM (mais próximo do spot), inverte Black-Scholes no preço médio da opção → `iv_atm`. Compara com `hv_20`: `iv/hv > 1.2` → "prêmio gordo (favorece vender prêmio)"; `< 0.9` → "prêmio barato (favorece comprar)"; senão neutro. Se a chain não trouxer vencimento/strike ATM utilizável, `iv_atm = null` e a leitura de vol cai para "baseada em HV".

> Para obter `iv_atm` é preciso estender o parse da chain para capturar a **data de vencimento** por opção (hoje o endpoint usa apenas `op[:10]` e descarta vencimento). Isso é um ajuste localizado em `market.py`/`data_providers.py`; se a fonte não trouxer, o campo degrada para `null` sem quebrar a página.

## 5. Contrato do payload (`IndicatorsPayload`)

```ts
interface IndicatorsPayload {
  ticker: string;
  preco_atual: number;
  hora: string;                 // "HH:MM" do último dado

  // Momento
  rsi14: number;
  stoch_k: number;
  stoch_d: number;
  vol_ratio: number;            // volume / média 20 (já em indicators.py)

  // Tendência
  ma20: number; ma50: number; ma200: number;
  adx: number;
  macd_diff: number;

  // Reversão
  bollinger_pct_b: number;
  z_score_20: number;
  atr14: number;                // novo (expor de indicators.py)
  vwap: number;                 // novo (expor)
  vwap_dist_pct: number;        // (preco-vwap)/vwap*100

  // Volatilidade / leitura para opções
  hv_20: number; hv_60: number;
  sigma_20: number;
  expected_move: number;        // ±R$ (base HV)
  expected_move_pct: number;
  faixa_1sigma: [number, number];
  dte_proximo_venc: number;
  iv_atm: number | null;        // null se chain não permitir
  iv_hv_ratio: number | null;
  vol_read: 'premio_gordo' | 'premio_barato' | 'neutro' | 'indisponivel';

  // Campos para o valuation (calculado no front via scoreAsset)
  faixa_52s_min: number;
  faixa_52s_max: number;

  // Setups
  setups: { nome: string; status: 'ativo'|'armado'|'inativo'; vies: 'alta'|'baixa'|'neutro'; descricao: string }[];
}
```

O **valuation 0..10** NÃO vem no payload: é calculado no front por `scoreAsset` (`src/lib/asset-analysis.ts`), reusando os campos já presentes (RSI, MA20/50, %B, z-score, faixa 52s). Evita duplicar a regra no backend. Por isso `faixa_52s_min/max` entram no payload.

## 6. Frontend

### 6.1 Rota e navegação
- Nova página: `src/app/analytics/indicadores/page.tsx` (`'use client'`).
- Link **"Indicadores e Setup →"** no cabeçalho de `/analytics` apontando para a sub-página, e a sub-página tem link de volta. Entrada opcional no `SiteNav` (decisão de menor risco: link interno na página `/analytics`, sem inchar o nav de topo).

### 6.2 Hook e tipos
- `src/lib/types/indicators.ts` — interface acima.
- `src/hooks/useIndicators.ts` — espelha `useAssetAnalysis` (fetch + loading + error).

### 6.3 Componentes (`src/components/indicators/`)
Apresentacionais, isolados, sem lógica de fetch:
- `IndicatorsHeader` — preço, hora, badges (Valuation X/10, Técnica: `<narrativa>`), frase-resumo.
- `MomentoPanel`, `TendenciaPanel`, `ReversaoPanel`, `VolatilidadePanel` — usam gauges/barras no estilo do `AssetAnalyzer` (RSI/Stoch/%B/ADX). Os primitivos de gauge podem ser extraídos do `AssetAnalyzer` para um módulo compartilhado se houver reuso real; caso contrário, versões locais compactas.
- `SetupCard` + `SetupsGrid` — um card por setup, badge de status (ativo=verde, armado=âmbar, inativo=cinza) e viés colorido.
- `VolReadCard` — "Leitura para opções": expected move (faixa ±1σ), vol rica/barata, viés comprar/vender prêmio. Sem operação concreta.
- `ComingSoonPanel` — painéis "em breve": Open Interest/Max Pain, Fluxo B3/Aluguel, IV Rank/Estrutura a termo. Layout fiel ao mockup, com selo "em breve".

### 6.4 Narrativa (regras puras, no front)
- **Valuation**: `scoreAsset` → "descontado/neutro/caro X/10".
- **Técnica**: combina tendência (MA20/50/200, ADX) + momento (RSI/Stoch). Ex.: baixa forte + sobrevendido → "faca caindo"; alta + RSI alto → "esticado".
- **Resumo (1 linha)**: compõe momento + tendência + leitura de vol. Ex.: "Sobrevendido em tendência de baixa forte — reversão prematura. IV elevada favorece venda de prêmio."

## 7. Tratamento de erro
- Ticker inválido/sem dados: 404/422 do endpoint → mensagem na página (igual `/market/analysis`).
- `iv_atm` indisponível: `vol_read = 'indisponivel'`/HV-only, sem quebrar.
- Painéis "em breve": estáticos, sempre renderizam.

## 8. Testes
- **pytest** `backend/tests` para `setups.py`: OHLC sintético construído para cada setup → asserts de `status`/`vies` (inside bar, engolfo, martelo, doji, rompimento, Larry 9.1/9.2/9.3, pullback). Casos negativos (inativo) inclusos.
- **pytest** para as derivações novas do endpoint (atr14, vwap_dist, expected_move) com série conhecida.
- **vitest** (opcional) para a narrativa/regras puras do front, se extraídas para função testável.
- Verificação visual: rodar app, abrir `/analytics/indicadores`, digitar PETR4, conferir painéis e setups.

## 9. Entregáveis / arquivos
Backend:
- `backend/domain/setups.py` (novo)
- `backend/api/routers/market.py` (novo endpoint + expor atr/vwap + parse de vencimento da chain)
- `backend/tests/test_setups.py` (novo)

Frontend:
- `src/app/analytics/indicadores/page.tsx` (novo)
- `src/hooks/useIndicators.ts` (novo)
- `src/lib/types/indicators.ts` (novo)
- `src/components/indicators/*` (novos)
- link em `src/app/analytics/page.tsx`

## 10. Fora de escopo (YAGNI)
- Open Interest/Max Pain/aluguel/IV Rank reais (sem fonte) → "em breve".
- Recomendação de operação concreta.
- Alterar `/market/analysis` ou `AssetAnalyzer`.
