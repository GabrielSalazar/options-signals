# Greeks e Black-Scholes — Pipeline do Scanner

## 1. Onde os Greeks entram

```
core_engine.analisar_ativo()
    └── estima prêmio (options_math.estimar_premio_otm)
    └── calcula greeks (greeks.calculate_greeks)
    └── filtra por |delta| ∈ [delta_min, delta_max]
    └── retorna dict com greeks no JSON
```

Os Greeks ficam disponíveis no campo `greeks` de cada sinal e são persistidos
no Supabase (coluna `greeks` JSONB).

## 2. Fórmulas (Black-Scholes europeu, sem dividendos)

```
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d2 = d1 − σ·√T

CALL = S·N(d1) − K·e^(−rT)·N(d2)
PUT  = K·e^(−rT)·N(−d2) − S·N(−d1)
```

Onde:
- `S` = preço do ativo-objeto
- `K` = strike
- `T` = tempo até o vencimento em **anos** (DTE em dias úteis / 252)
- `r` = taxa livre de risco (Selic ~13,5%)
- `σ` = volatilidade implícita (aqui usamos HV de 20 dias como proxy)

## 3. Greeks calculados

| Greek | Significado | Como usamos |
|---|---|---|
| **Delta** | dC/dS — sensibilidade ao preço do ativo | Filtro de qualidade: rejeita se `|Δ|` fora de `[delta_min, delta_max]` (0,15–0,45 por padrão) — garante OTM ideal |
| **Gamma** | dΔ/dS | Informativo (curvatura do delta) |
| **Theta** | dC/dt (por dia) | Exibido no SignalCard — alerta sobre decaimento temporal |
| **Vega** | dC/dσ (por 1% de IV) | Exibido — sensibilidade à vol |
| **Rho** | dC/dr | Informativo |
| **POP** | N(d2) para CALL, N(−d2) para PUT | Probabilidade neutra de exercício |

## 4. Volatilidade Implícita (IV)

A função `greeks.implied_volatility()` resolve via Newton-Raphson o σ que faz
`BS(σ) = preço_mercado`. **Importante:** enquanto o preço da opção é estimado
por BS (caminho de fallback quando `opcoes.net` não retorna book real), a IV
converge para a HV usada como input — não há informação nova. A função fica
pronta para o dia em que integrarmos preço REAL (MT5, corretora, etc.).

## 5. Limitações

- **Sem dividendos:** ativos pagadores de dividendos terão BS levemente
  enviesado (CALL superestimada, PUT subestimada).
- **Sem skew:** assumimos IV constante para todos os strikes.
- **HV ≠ IV de mercado:** quando o mercado precifica eventos (resultado,
  Copom, política), a IV real diverge da HV. Sinais perto desses eventos
  devem ser interpretados com cautela.

## 6. Exemplos numéricos

Para `S = 30, K = 32, T = 30/252, σ = 0,40, r = 0,135`:

```
CALL ≈ R$ 0,71      Δ ≈ 0,42      POP ≈ 0,32
```

Strike 12% OTM (`K = 33.6`):

```
CALL ≈ R$ 0,28      Δ ≈ 0,22      POP ≈ 0,14
```

Note como o delta cai rapidamente com a distância do strike — daí o
intervalo-alvo 0,15–0,45 (nem ATM, nem deep-OTM).
