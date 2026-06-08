# Design: Calculadoras de Análise — Analytics Page

**Data:** 2026-06-08
**Status:** Aprovado

---

## Contexto

A página `/analytics` exibe superfície de IV, skew (atualmente mockado), e calculadora de Greeks. O objetivo é adicionar uma nova seção "Calculadoras" com três painéis interativos que auxiliem na decisão de compra de opções na B3.

---

## Arquitetura — Abordagem C (Híbrida)

O backend calcula o **quadro de referência estático por ticker** (indicadores técnicos, HV, chain). O frontend faz os **vereditos e o solver de IV em TypeScript** (interativo, sem round-trip por campo digitado).

```
Usuário digita ticker
        │
        ▼
GET /market/analysis/{ticker}          ← novo endpoint
        │
        ├─ fetch_brapi_historical("6mo") → OHLCV diário
        │       ├─ estimar_iv_historica(df, 20)  → HV₂₀
        │       ├─ estimar_iv_historica(df, 60)  → HV₆₀
        │       └─ indicators.py:
        │               MA20, MA50, MA200
        │               RSI₁₄
        │               Bollinger %B
        │               σ₂₀ (desvio padrão 20 dias)
        │               z-score vs MA20
        │               faixa_52s_min / faixa_52s_max
        │
        └─ _fetch_chain(ticker) → [{strike, preco, tipo, negocios}]

Resposta JSON (AssetAnalysisPayload):
  { ticker, preco_atual,
    hv_20, hv_60,
    ma20, ma50, ma200, sigma_20,
    rsi14, bollinger_pct_b, z_score_20,
    faixa_52s_min, faixa_52s_max,
    chain: [{ strike, preco, tipo, negocios }] }
```

**Cache no frontend:** payload armazenado em `Map<ticker, {data, timestamp}>`. Reusado por 5 minutos sem nova requisição — evita latência repetida enquanto o usuário preenche os campos dos painéis B e C.

---

## Painel A — Calculadora do Ativo

**Entrada:** campo `ticker` + botão "Analisar" + seletor rápido com tickers já presentes nos sinais do Supabase.

**Indicadores exibidos:**

| Indicador | Visualização | Sinal barato | Sinal caro |
|---|---|---|---|
| Posição faixa 52s | Barra horizontal mín→atual→máx | < 30% da faixa | > 70% da faixa |
| Distância MA20/50/200 | Chips com % | preço < MA | preço > MA por margem |
| RSI₁₄ | Gauge semicircular 0–100 | < 30 | > 70 |
| Bollinger %B | Barra 0–1 | < 0,20 | > 0,80 |
| Z-Score vs MA20 | Número com semáforo | < -1,0 | > +1,0 |

**Veredicto:** cada indicador contribui 0–2 pontos conforme tabela abaixo:

| Indicador | 0 pts (neutro/caro) | 1 pt (levemente barato) | 2 pts (barato) |
|---|---|---|---|
| Posição 52s | > 50% | 30–50% | < 30% |
| Distância MAs | preço > MA20 e MA50 | preço < MA20 OU MA50 | preço < MA20 E MA50 |
| RSI₁₄ | > 55 | 30–55 | < 30 |
| Bollinger %B | > 0,5 | 0,2–0,5 | < 0,2 |
| Z-Score MA20 | > 0 | -1–0 | < -1 |

Total (0–10):
- 0–3 → `🟢 Barato`
- 4–6 → `🟡 Neutro`
- 7–10 → `🔴 Caro`

---

## Painel B — Calculadora de Opção

**Entradas:** ticker (compartilhado com Painel A), `tipo C/P`, `strike`, `vencimento (data)`, `preço de mercado`.

**Processamento no frontend:**

1. **Solver de IV** — Newton-Raphson sobre BS:
   ```
   σ₀ = HV₂₀ (chute inicial)
   σₙ₊₁ = σₙ − (BS(σₙ) − market_price) / Vega(σₙ)
   convergência: |BS(σₙ) − market_price| < 1e-6, max 100 iterações
   fallback: bisecção em [0,01 ; 5,0] se NR divergir
   ```
   Reutiliza `callPrice`, `putPrice`, `calcVega` de `src/lib/black-scholes.ts`.

2. **Preço justo BS** — `BS(HV₂₀)` com os parâmetros digitados.

**Exibição:**

- IV calculada vs HV₂₀ — barra comparativa com percentual de diferença
- Preço justo BS vs preço digitado — destaque se mercado > 120% do justo
- Greeks: **Delta**, **Theta** (por dia), **Vega** — calculados diretamente do solver
- **Break-even no vencimento:**
  - Call: `K + prêmio` → "ativo precisa chegar a R$ X para empatar"
  - Put: `K − prêmio`
- Moneyness (% OTM/ITM) + DTE
- IV Rank na chain carregada (posição percentual entre os strikes)

**Veredicto:**
- `IV > HV₂₀ × 1,2` → `🔴 Opção Cara` (IV alta, bom para vender)
- `IV < HV₂₀ × 0,8` → `🟢 Opção Barata` (IV baixa, bom para comprar)
- Fora dessa faixa → `🟡 Neutro`

---

## Painel C — HV vs IV (substitui VolatilitySkew mockado)

- **Barras duplas:** HV₂₀ e HV₆₀ lado a lado (componente `VolatilityPanel` substitui `VolatilitySkew`)
- **Curva de skew real:** scatter dos strikes da chain com IV calculada por NR para cada opção negociada (`negocios > 0`), calls e puts em cores distintas
- **IV Rank / IV Percentile:** onde a IV da opção selecionada se posiciona entre todas as opções da chain

---

## Alerta Cruzado

Quando **Painel A = Barato** E **Painel B = Opção Barata** simultaneamente:

> Banner verde: `✦ Ponto de entrada: ativo subavaliado com IV baixa — custo de compra de call reduzido`

Exibido entre os painéis A e B, desaparece se qualquer condição mudar.

---

## Seletor Rápido de Ticker

Dropdown populado com `SELECT DISTINCT ticker FROM signals ORDER BY timestamp DESC LIMIT 20` via Supabase client já existente. Evita digitação manual e garante tickers com histórico de sinais.

---

## Arquivos Impactados

| Arquivo | Mudança |
|---|---|
| `backend/api/routers/market.py` | + `GET /market/analysis/{ticker}` |
| `src/lib/black-scholes.ts` | + `impliedVol(marketPrice, S, K, T, r, type): number` |
| `src/lib/asset-analysis.ts` | novo — `scoreAsset(payload): AssetVerdict` + tipos |
| `src/components/AssetAnalyzer.tsx` | novo — Painel A |
| `src/components/OptionAnalyzer.tsx` | novo — Painel B |
| `src/components/VolatilityPanel.tsx` | novo — substitui `VolatilitySkew` mockado |
| `src/app/analytics/page.tsx` | + seção "Calculadoras" com os 3 painéis |

---

## Testes

- `src/lib/__tests__/black-scholes.test.ts` — round-trip: `callPrice(σ) → impliedVol → σ` com tolerância `1e-4`; NR converge em < 20 iterações para casos normais; bisecção ativada para preço ≈ 0
- `src/lib/__tests__/asset-analysis.test.ts` — `scoreAsset` com payloads sintéticos cobrindo os três vereditos (barato/neutro/caro) e casos extremos (RSI = 15, %B = 0,95)

---

## Fora do Escopo (explicitamente adiado)

- Análise fundamentalista do ativo (P/L, EV/EBITDA)
- Calendar/Diagonal spread (dual-expiry)
- Alertas persistidos no Supabase
- Notificações push
