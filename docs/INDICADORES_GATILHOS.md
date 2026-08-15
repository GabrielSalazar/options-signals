# Indicadores e Gatilhos — B3 Options Signals

**Data:** 2026-08-14  
**Atualizado:** Mapeamento completo do motor atual

---

## 📊 Indicadores Técnicos

Calculados em `backend/domain/indicators.py` e enriquecidos em tempo real.

### Indicadores de Momentum

| Indicador | Período | Uso | Intervalo | Descrição |
|-----------|---------|-----|-----------|-----------|
| **RSI** | 14 | Overbought/Oversold | 0-100 | Força relativa (30=oversold, 70=overbought) |
| **Stochastic (K/D)** | K=14, D=3 | Confirmação de reversão | 0-100 | Oscilador de momentum, cruza em 20/80 |
| **MACD** | 12/26/9 | Cruzamento de médias | -∞ a +∞ | Convergência/divergência exponencial |
| **Williams %R** | 14 | Momentum reverso | -100 a 0 | Variação: alta em -80, baixa em -20 |
| **CCI** | 20 | Desvio cíclico | -∞ a +∞ | Commodity Channel Index (desvio de média) |

### Indicadores de Tendência

| Indicador | Período | Uso | Fórmula | Descrição |
|-----------|---------|-----|---------|-----------|
| **EMA 9** | 9 | Rápida/decisão | Exponencial | Tendência muito rápida, suporte imediato |
| **EMA 21** | 21 | Média/operação | Exponencial | Tendência média, nível técnico |
| **EMA 50** | 50 | Camada PUCK | Exponencial | Filtro de "alta institucional" |
| **EMA 200** | 200 | Long-term | Exponencial | Média móvel de longo prazo |
| **ADX** | 14 | Força de tendência | D+/D- | Índice de força da tendência (>25=forte) |
| **Supertrend** | 14, mult=3.0 | Stop/direction | ATR+High/Low | Envelope de tendência com breakeven |

### Indicadores de Volatilidade

| Indicador | Período | Uso | Aplicação | Descrição |
|-----------|---------|-----|-----------|-----------|
| **ATR** | 14 | Stops, Squeeze | Níveis | Average True Range (amplitude típica) |
| **Bollinger Bands** | 20, desvio=2 | Extremo, squeeze | Upper/Mid/Lower | Envelope de volatilidade (±2σ) |
| **Keltner Channels** | EMA20, ATR=14 | Suporte dinâmico | Upper/Mid/Lower | Envelope baseado em ATR (1.5x) |
| **IV Rank** | Histórico 52w | Filtro de emissão | 0-100% | Ranking de volatilidade implícita vs. histórico |
| **IV Premium** | Histórico | Comparação B3 | % acima/abaixo | Custo relativo da volatilidade |

### Indicadores de Volume

| Indicador | Período | Uso | Intervalo | Descrição |
|-----------|---------|-----|-----------|-----------|
| **Volume Relativo** | 20 | Confirmação | Ratio | Volume hoje vs. média 20d |
| **MFI** (Money Flow Index) | 14 | Pressão de preço | 0-100 | RSI ponderado por volume |
| **OBV** (On Balance Volume) | Contínuo | Fluxo acumulado | -∞ a +∞ | Volume acumulado com sinal |
| **CMF** (Chaikin Money Flow) | 20 | Agressividade | -1 a +1 | Fluxo institucional (PUCK v3) |
| **VWAP** (Volume Weighted Avg) | 20 | Nível de executabilidade | Preço | Preço médio ponderado por volume |

### Indicadores PUCK (Camada Shadow)

| Indicador | Período | Uso | Intervalo | Descrição |
|-----------|---------|-----|-----------|-----------|
| **HC Max/Min** | Volume × fator 1.5 | Absorção institucional | Preço | Zonas de negociação de alto volume |
| **CLV** (Close Location Value) | Candle | Pressão de fechamento | -1 a +1 | Onde o close ocorreu (topo/fundo/meio) |
| **CMF Normalizado** | 21 | Intensidade do fluxo | 0-2.0 | Fluxo vs. média histórica do ativo (>1.5=evento) |
| **Pivots Confirmados** | Ordem=1 | Suporte/Resistência | Alto/Baixo | Fundos/topos locais sem look-ahead |

---

## 🎯 Gatilhos (v1 e v2)

Funções de decisão que determinam emissão de sinais. Implementadas em `backend/services/core_engine.py`.

### Gatilhos v1 — Análise Técnica

**Estratégia:** Avaliar cada indicador individualmente e somar pontos de alta/baixa.

| Gatilho | Critério CALL | Critério PUT | Peso | Status |
|---------|---------------|--------------|------|--------|
| **Tendência EMA** | Close acima EMA21 | Close abaixo EMA21 | Alto | Ativo |
| **MACD Cruzamento** | MACD acima sinal + acelerando | MACD abaixo sinal + acelerando | Alto | Ativo |
| **RSI Zona** | RSI 35-60 (recuperação) | RSI 40-65 (recuperação) | Médio | Ativo |
| **Stochastic** | K < 20 (sobrevendido) | K > 80 (sobrecomprado) | Médio | Ativo |
| **ADX Força** | ADX > 25 (tendência forte) | ADX > 25 (tendência forte) | Baixo | Ativo |
| **Bollinger Breakout** | Close acima BB Upper | Close abaixo BB Lower | Baixo | Ativo (Bônus) |
| **VWAP Confirmação** | Close acima VWAP | Close abaixo VWAP | Baixo | Ativo (Bônus) |
| **Volume Relativo** | Volume > média 20d × 1.2 | Volume > média 20d × 1.2 | Médio | Ativo |
| **Volatility Squeeze** | BB/KC estão apertados | BB/KC estão apertados | Baixo | Ativo (Bônus) |

**Score:** Soma ponderada → 0-100 (cap em 100)

### Gatilhos v2 — Fluxo Institucional (Matriz PUCK)

**Estratégia:** Detectar pressão de "mãos pesadas" (institucionais) através de volume anormal e padrões de absorção.

| Gatilho | Critério | Indicador | Status |
|---------|----------|-----------|--------|
| **CMF Evento** | CMF norm > 1.5 | Pressão institucional detectada | Shadow (Telemetria) |
| **HC Absorção** | Vela se fecha dentro de HC Max/Min | Zona de volume alto internalizado | Shadow (Telemetria) |
| **Persistência de Fluxo** | Fluxo mantém sinal por 3+ velas | CLV + CMF coerentes | Shadow (Telemetria) |
| **Rompimento com Sustentação** | Rompimento de resistência + volume | OBV + MFI + Volume acelerado | Shadow (Telemetria) |
| **Reversão Institucional** | Reversão em nível de HC | Volume reverso abrupto | Shadow (Telemetria) |

**Modo:** Todos em shadow (observacional). Ativação prevista Fase 4.

---

## 🚫 Vetos Técnicos

Bloqueios de emissão mesmo com score alto.

### Vetos Ativos (Impedem Emissão)

| Veto | Condição | Motivo | Status |
|------|----------|--------|--------|
| **Reentrada (Cooldown)** | Mesmo ticket+direção emitido <72h | Evita duplicação | Ativo |
| **Preço da Opção** | Prêmio < R$0.10 ou > R$3.00 | Impossível negociar/gamma alto | Ativo |
| **IV Muito Caro** | IV Rank > 80% | Prêmio pagará muita volatilidade | Shadow |
| **Spread Muito Largo** | Bid-Ask > 10% do mid | Executabilidade ruim | Shadow |
| **Evento Econômico** | Notícia importante próxima | Risco de gap overnight | Shadow |
| **VXBR Extremo** | VXBR > 30 | Volatilidade de mercado muito alta | Shadow |

**Shadow Mode:** Registra telemetria mas não bloqueia (Fase 4 ativa).

---

## 📈 Filtragem Multinível

### Filtro 1: Indicadores Básicos
```
✓ Volume mínimo?
✓ Preço na faixa?
✓ DTE ideal (10-60 dias)?
✓ Score >= 5 (mínimo)?
```
→ Retorna None se qualquer falha

### Filtro 2: Vetos Técnicos
```
✓ Não em cooldown?
✓ Prêmio operável?
✓ IV não explosiva (shadow)?
```
→ Retorna None se veto ativo

### Filtro 3: Volatilidade Implícita
```
✓ IV Rank não extremo?
✓ Prêmio não acima de histórico?
✓ Score >= 7 se IV exigir?
```
→ Shadow: só telemetria

### Filtro 4: Liquidez (Shadow)
```
- OI suficiente?
- Spread razoável?
- Sem evento econômico?
- VXBR normal?
```
→ Shadow: só telemetria

### Filtro 5: Consenso de Famílias (Shadow)
```
- Famílias ativas >= 2?
- Setup coerente?
- Absorção confirmada (PUCK)?
```
→ Shadow: só telemetria

---

## 🎲 Score Ponderado

Implementado em `backend/domain/scoring.py`.

### Pesos (Total Bruto: 118)

```
Preço na faixa operável            12 pontos
DTE no range ideal                  8 pontos
Delta OTM (0.15-0.45)              10 pontos
Tendência (0/8/16/20)              20 pontos
────────────────────────────────────────────
MACD (cruzamento/favor/aceleração) 18 pontos
RSI na zona de direção             14 pontos
Estocástico (cruzamento)            9 pontos
ADX >= 25                            5 pontos
────────────────────────────────────────────
Volume relativo                     8 pontos
Bônus Bollinger                     4 pontos
Bônus VWAP                          5 pontos
Bônus Volatility Squeeze            5 pontos
────────────────────────────────────────────
TOTAL BRUTO                       118 pontos
CAP FINAL (mínimo de emissão)     >= 5
MÁXIMO (cap)                      100 pontos
```

### Interpretação de Score

| Score | Interpretação | Ação |
|-------|---------------|------|
| >= 95 | Muito forte (≈ 4+ gatilhos sinérgicos) | Emitir + alerta |
| 80-94 | Forte (3 gatilhos bem coerentes) | Emitir |
| 60-79 | Médio (2 gatilhos + bônus) | Emitir (conforme config) |
| 40-59 | Fraco (1 gatilho) | Não emitir (config padrão) |
| < 40  | Muito fraco | Nunca emite |
| MIN_SCORE (config) | Liminat configurável | Padrão: 5 |

---

## 🏗️ Famílias de Gatilhos

Agrupamento de gatilhos por categoria (Fase 2.1).

| Família | Gatilhos | Descrição |
|---------|----------|-----------|
| **Média Móvel** | EMA9/21/200, cruzamentos | Tendência via MA |
| **Momentum** | MACD, RSI, Stochastic | Força de movimento |
| **Volatilidade** | Bollinger, Keltner, Squeeze | Extremos de volatilidade |
| **Volume** | MFI, OBV, CMF, Volume Rel. | Força de compradores/vendedores |
| **Fluxo Institucional** | CMF Event, HC, CLV | Pressure of "mãos pesadas" |

**Consenso:** Mínimo 2 famílias ativas = sinal mais robusto (Fase 2.2).

---

## 📍 Setups Classificados

Tipificação de padrões (Fase 2.2).

| Setup | Características | Confiabilidade |
|-------|-----------------|-----------------|
| **Continuação Simples** | 1 MA + Volume | Média (40-60%) |
| **Reversão Confirmada** | Pivot + Bollinger + MACD cross | Alta (70-80%) |
| **Breakout Sustentado** | Breakout + ADX>25 + Volume | Alta (75-85%) |
| **Flux Institucional** | HC + CMF Event + OBV acelerando | Muito alta (80-90% shadow) |
| **Empate/Ambíguo** | Score CALL = Score PUT | Não emite (0%) |

---

## 🎭 Exemplo: PETR4 — De Gatilhos a Sinal

**Cenário Real (Fictício):**

```
Ticker: PETR4
Data: 2026-08-14 16:00 UTC
Preço: R$ 35.42
Volume: 45M (vs. média 20d: 32M → 1.4x)

GATILHOS v1 DETECTADOS:
├─ Close (35.42) acima EMA21 (35.10) ✅ → +Alta
├─ EMA9 (35.25) acima EMA21 ✅ → +Alta
├─ MACD (0.145) acima sinal (0.138) ✅ → +Alta aceleração
├─ RSI (48) na zona 35-60 ✅ → +Alta recuperação
├─ Stoch K (42) em zona de subida ✅ → +Alta
├─ ADX (22) abaixo 25 ❌ → Sem bônus tendência
├─ BB: Close (35.42) acima Mid (35.28) ✓ → +Bônus
└─ VWAP (35.35) abaixo Close ✓ → +Bônus

SCORE CALCULADO:
├─ Preço OK (faixa 0.10-3.00)        +12 = 12
├─ DTE ideal                          +8 = 20
├─ Delta 0.30 (OTM bom)              +10 = 30
├─ Tendência alta (3/3)              +20 = 50
├─ MACD cruzamento bullish           +18 = 68
├─ RSI zona recuperação              +14 = 82
├─ Stochastic cruzamento              +9 = 91
├─ ADX < 25 (sem bônus)               +0 = 91
├─ Volume relativo (1.4x)             +8 = 99
├─ Bônus Bollinger                    +4 = 103 (cap=100)
└─ FINAL                             ≤100

DECISÃO: SCORE_ALTA (100) > SCORE_BAIXA (45) → CALL

VERIFICAÇÕES:
├─ Veto reentrada? Não ✅
├─ Veto preço? R$1.45 OK ✅
├─ IV Rank 65% (shadow)? OK ✅
├─ Spread < 10%? OK ✅
│
└─ SINAL EMITIDO: CALL em PETR4
    Score: 100
    Prêmio: R$1.45
    DTE: 23 dias
    Delta: 0.32
    Gatilhos: 8/9 ativos
    Setup: Continuação + Volume
    Confiabilidade: Alta
```

---

## 📚 Referência Rápida

### Arquivo de Configuração
```
backend/core/config.py
```

### Indicadores Calculados
```
backend/domain/indicators.py
```

### Gatilhos Avaliados
```
backend/services/core_engine.py → _avaliar_gatilhos()
```

### Score Ponderado
```
backend/domain/scoring.py → score_ponderado()
```

### Vetos Técnicos
```
backend/services/core_engine.py → avaliar_vetos_tecnicos()
```

### Filtro de IV
```
backend/services/core_engine.py → avaliar_filtro_iv()
```

---

## 🔄 Status por Fase

| Componente | Status | Fase |
|-----------|--------|------|
| Indicadores base (RSI, MACD, BB, ATR) | ✅ Ativo | v1 |
| Gatilhos v1 (técnico) | ✅ Ativo | v1 |
| Score ponderado | ✅ Ativo | v1 |
| Vetos técnicos | ✅ Ativo | v2 |
| IV Rank / IV Premium | ✅ Ativo | v2 |
| Filtro Liquidez | 🔶 Shadow | v3 |
| Gatilhos v2 (fluxo institucional) | 🔶 Shadow | PUCK v3 |
| Consenso de famílias | 🔶 Shadow | v2.1 |
| Setup classification | 🔶 Shadow | v2.2 |

---

**Última atualização:** 2026-08-14  
**Mantido por:** Motor de Sinais B3 Options  
**Próxima review:** Fase 1 — Contrato Tipado

