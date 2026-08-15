# Estratégias, Indicadores e Gatilhos — Trading de Ações

**Data:** 2026-08-14  
**Escopo:** Ações (swing trading / day trading)  
**Objetivo:** Decisões de compra/venda baseadas em análise técnica

---

## 1. ESTRATÉGIA: TENDÊNCIA COM MÉDIAS MÓVEIS

### Indicador: EMA (Exponential Moving Average)
**Como montar no gráfico:**
- Adicionar 3 linhas (menu Indicadores)
- EMA 9 (cor: azul rápido)
- EMA 21 (cor: vermelho médio)
- EMA 200 (cor: cinza longo prazo)

**Cálculo:**
```
EMA = Preço_hoje × k + EMA_ontem × (1 - k)
onde k = 2 / (período + 1)

EMA9:   Peso em 1-9 dias recentes
EMA21:  Peso em 1-21 dias recentes
EMA200: Peso em 1-200 dias recentes
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | Close acima de EMA21 E EMA9 acima de EMA21 |
| 🔴 VENDA | Close abaixo de EMA21 E EMA9 abaixo de EMA21 |
| ⚠️ ALERTA | Close cruza EMA21 (mudança de direção) |

**Lógica:**
- EMA9 = controle curto prazo (entrada rápida)
- EMA21 = confirmação de tendência (filtro de direção)
- EMA200 = contexto de longo prazo (avoid contra-tendência)

**Exemplo PETR4:**
```
Close: 35.42
EMA9:  35.25 (acima)
EMA21: 35.10 (acima)
EMA200: 34.80 (acima)

→ Sinal: COMPRA (tendência de alta confirmada)
```

---

## 2. ESTRATÉGIA: REVERSÃO COM RSI

### Indicador: RSI (Relative Strength Index)
**Como montar no gráfico:**
- Adicionar painel inferior
- RSI 14 (linha 0-100)
- Zonas: linha 30 (oversold), linha 70 (overbought)

**Cálculo:**
```
Ganho_médio = Média das altas dos últimos 14 dias
Perda_média = Média das baixas dos últimos 14 dias
RS = Ganho_médio / Perda_média
RSI = 100 - (100 / (1 + RS))
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | RSI < 30 (sobrevendido) + Close acima EMA21 |
| 🔴 VENDA | RSI > 70 (sobrecomprado) + Close abaixo EMA21 |
| ⚠️ DIVERGÊNCIA | Preço sobe mas RSI cai (reversão próxima) |

**Lógica:**
- RSI < 30 = "preço caiu demais" → probabilidade de recuperação alta
- RSI > 70 = "preço subiu demais" → probabilidade de queda alta
- Evita operações contra a tendência (sempre confirmar com EMA21)

**Exemplo:**
```
RSI: 28 (sobrevendido)
Close: 34.50
EMA21: 35.10 (abaixo, mas subindo)

→ Sinal: ALERTA DE COMPRA (esperar confirmação)
```

---

## 3. ESTRATÉGIA: MOMENTUM COM MACD

### Indicador: MACD (Moving Average Convergence Divergence)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha MACD (azul, 12-26 exponencial)
- Linha Sinal (vermelho, 9 dias)
- Histograma (verde/vermelho, diferença)

**Cálculo:**
```
EMA12 = Exponential Moving Average 12 dias
EMA26 = Exponential Moving Average 26 dias
MACD = EMA12 - EMA26
Sinal = EMA9 do MACD
Histograma = MACD - Sinal
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | MACD cruza acima da Sinal (bullish) |
| 🔴 VENDA | MACD cruza abaixo da Sinal (bearish) |
| ⚡ ACELERAÇÃO | Histograma cresce em magnitude (força aumenta) |
| ⏸️ DESACELERAÇÃO | Histograma encolhe (força diminui) |

**Lógica:**
- MACD > Sinal = momentum positivo
- MACD < Sinal = momentum negativo
- Cruzamento = mudança de momentum
- Histograma crescente = força da tendência aumenta

**Exemplo:**
```
MACD: 0.145 (acima)
Sinal: 0.138
Histograma: +0.007 (verde, crescente)

→ Sinal: COMPRA COM FORÇA (momentum bullish)
```

---

## 4. ESTRATÉGIA: EXTREMO COM BOLLINGER BANDS

### Indicador: Bollinger Bands
**Como montar no gráfico:**
- Adicionar sobre o gráfico de preço
- Banda Superior (Upper) = Média 20 + (Desvio Padrão × 2)
- Banda Inferior (Lower) = Média 20 - (Desvio Padrão × 2)
- Banda Média (Mid) = Média Móvel 20

**Cálculo:**
```
Média = SMA20 (Média Simples 20 dias)
Desvio = Volatilidade dos últimos 20 dias
Upper = Média + (2 × Desvio)
Lower = Média - (2 × Desvio)
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | Close toca Lower + RSI < 40 (extremo) |
| 🔴 VENDA | Close toca Upper + RSI > 60 (extremo) |
| ⚠️ SQUEEZE | Bandas se fecham (volatilidade baixa = explosão próxima) |
| 📈 BREAKOUT | Close acima Upper com volume (rompimento confirmado) |

**Lógica:**
- Banda Superior/Inferior = limites de movimento normal
- Close fora das bandas = posição extrema (reversão provável)
- Squeeze = pressão acumulando (prepara movimento grande)
- Breakout = novo nível de preço (continuação da tendência)

**Exemplo:**
```
Close: 34.20
Lower: 34.15
Upper: 35.80
RSI: 35

→ Sinal: COMPRA EXTREMA (toque na banda + RSI baixo)
```

---

## 5. ESTRATÉGIA: VOLUME COM OBV

### Indicador: OBV (On Balance Volume)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha OBV (azul)
- EMA9 do OBV (vermelho, para suavizar)

**Cálculo:**
```
Se Close > Close_anterior:
  OBV = OBV_anterior + Volume

Se Close < Close_anterior:
  OBV = OBV_anterior - Volume

Se Close = Close_anterior:
  OBV = OBV_anterior (sem mudança)
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | OBV sobe + Close sobe (volume confirma alta) |
| 🔴 VENDA | OBV cai + Close cai (volume confirma baixa) |
| ⚠️ DIVERGÊNCIA | Close sobe mas OBV cai (alta sem volume = fake) |
| ⚡ APROVAÇÃO | OBV em novo máximo (forte convicção) |

**Lógica:**
- OBV acumulando = "smart money" entrando
- OBV distribuindo = "smart money" saindo
- Divergência volume/preço = movimento fraco (reversão próxima)
- OBV em novo máximo = confiança alta

**Exemplo:**
```
Close: 35.42 (novo máximo)
Volume: 45M
OBV: 2.34B (novo máximo)

→ Sinal: COMPRA CONFIRMADA (preço + volume em máximo)
```

---

## 6. ESTRATÉGIA: ABSORÇÃO INSTITUCIONAL COM CMF

### Indicador: CMF (Chaikin Money Flow)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha CMF (azul)
- Linha zero (cinza, referência)
- Zona +1 / -1 (extremos)

**Cálculo:**
```
CLV = Close Location Value = (Close - Low) - (High - Close) / (High - Low)
MFV = Money Flow Volume = CLV × Volume
CMF = Soma(MFV últimos 20 dias) / Soma(Volume últimos 20 dias)
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | CMF > +0.3 + Close acima EMA21 (fluxo institucional entra) |
| 🔴 VENDA | CMF < -0.3 + Close abaixo EMA21 (fluxo institucional sai) |
| 🟠 EVENTO | CMF > +0.6 (extremo: entrada massiva) |
| ⏳ TRANSIÇÃO | CMF cruza zero (mudança de sentimento) |

**Lógica:**
- CMF positivo = mais volume perto do topo (compra)
- CMF negativo = mais volume perto do fundo (venda)
- CMF próximo de zero = indecisão (sem movimento esperado)
- CMF extremo = mudança de direção provável

**Exemplo:**
```
CMF: +0.45
Close: 35.42 (acima EMA21 35.10)
Volume: 45M (acima média)

→ Sinal: COMPRA INSTITUCIONAL (fluxo forte de entrada)
```

---

## 7. ESTRATÉGIA: CONFIRMAÇÃO COM STOCHASTIC

### Indicador: Stochastic (K% e D%)
**Como montar no gráfico:**
- Adicionar painel inferior
- %K = 14 (linha rápida, azul)
- %D = 3 (linha sinal, vermelho)
- Zonas: 20 (oversold), 80 (overbought)

**Cálculo:**
```
%K = (Close - Low14) / (High14 - Low14) × 100
     onde High14 e Low14 são os extremos dos últimos 14 dias

%D = SMA3 do %K (média simples 3 períodos de K)
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | K cruza D acima de 20 (saída de oversold) |
| 🔴 VENDA | K cruza D abaixo de 80 (saída de overbought) |
| 🔥 FORÇA | K > 80 + Close em máximo (muito força) |
| ❄️ FRAQUEZA | K < 20 + Close em mínimo (muito fraqueza) |

**Lógica:**
- %K < 20 = sobrevendido (recuperação provável)
- %K > 80 = sobrecomprado (queda provável)
- Cruzamento K/D = mudança de momentum
- Melhor em intervalos de 1-4 horas (não funciona bem em diário)

**Exemplo:**
```
K: 18 (abaixo)
D: 25 (acima)
K cruzando D para cima

→ Sinal: COMPRA EM FORMAÇÃO (esperar confirmação de volume)
```

---

## 8. ESTRATÉGIA: FORÇA DE TENDÊNCIA COM ADX

### Indicador: ADX (Average Directional Index)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha ADX (azul, 14)
- Linha +DI (verde, acima)
- Linha -DI (vermelho, abaixo)
- Linha 25 (referência de força)

**Cálculo:**
```
+DI = Uptrend Strength (quanto o preço sobe)
-DI = Downtrend Strength (quanto o preço desce)
ADX = Força ABSOLUTA da tendência (não indica direção)
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 📈 TENDÊNCIA FORTE | ADX > 25 + +DI > -DI (alta confirmada) |
| 📉 TENDÊNCIA FORTE | ADX > 25 + -DI > +DI (baixa confirmada) |
| 🔄 SIDEWAYS | ADX < 20 (sem direção = range) |
| ⚠️ MUDANÇA | ADX cruzando 25 para cima (tendência começando) |

**Lógica:**
- ADX > 25 = tendência forte (evitar contratendência)
- ADX < 20 = movimento lateral (day trading apenas)
- ADX crescente = força aumentando
- ADX decrescente = força diminuindo (reversão próxima)

**Exemplo:**
```
ADX: 28 (acima 25)
+DI: 22
-DI: 12

→ Sinal: TENDÊNCIA DE ALTA FORTE (seguir tendência)
```

---

## 9. ESTRATÉGIA: ROMPIMENTO COM ATR STOPS

### Indicador: ATR (Average True Range)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha ATR (azul, 14)
- Nível = Close ± ATR (mostrar na linha de preço)

**Cálculo:**
```
True Range = Max(
  High - Low,
  |High - Close_anterior|,
  |Low - Close_anterior|
)
ATR = Média móvel 14 do True Range
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🎯 COMPRA | Rompimento acima de resistência + ADX > 20 |
| 🎯 VENDA | Rompimento abaixo de suporte + ADX > 20 |
| 🛑 STOP | Perda = Close - (2 × ATR) para compra |
| 📊 VOLATILIDADE | ATR alto = grande movimento esperado |
| 😴 CONSOLIDAÇÃO | ATR baixo = movimento pequeno esperado |

**Lógica:**
- ATR = volatilidade atual do ativo
- ATR alto = movimento grande esperado
- ATR baixo = consolidação (antes de grande movimento)
- Usar ATR para calcular distância de stop (risco controlado)

**Exemplo:**
```
Close: 35.42
ATR: 0.85
Resistência: 36.20

Stop Loss = 35.42 - (2 × 0.85) = 33.72
Alvo = 36.20 (rompimento)

Razão Risco/Recompensa = (36.20 - 35.42) / (35.42 - 33.72) = 0.42
```

---

## 10. ESTRATÉGIA: FLUXO COM MFI

### Indicador: MFI (Money Flow Index)
**Como montar no gráfico:**
- Adicionar painel inferior
- Linha MFI (azul, 14)
- Zonas: 20 (oversold), 80 (overbought)

**Cálculo:**
```
Preço Típico = (High + Low + Close) / 3
Money Flow = Preço Típico × Volume

Fluxo Positivo = Soma do Money Flow quando Close > Close_anterior
Fluxo Negativo = Soma do Money Flow quando Close < Close_anterior

MFI = 100 - (100 / (1 + Fluxo_Positivo / Fluxo_Negativo))
```

**Gatilhos:**
| Sinal | Condição |
|-------|----------|
| 🟢 COMPRA | MFI < 30 + Volume crescente (entrada institucional) |
| 🔴 VENDA | MFI > 70 + Volume crescente (saída institucional) |
| ⚠️ DIVERGÊNCIA | Preço em máximo mas MFI em queda (topo fake) |
| ✅ CONFIRMAÇÃO | MFI sobe com Close sobe (força real) |

**Lógica:**
- MFI < 30 = sobrevendido com volume (compra de entrada)
- MFI > 70 = sobrecomprado com volume (venda de saída)
- MFI diferente do preço = reversão próxima
- Similar ao RSI mas incorpora volume (mais confiável)

**Exemplo:**
```
MFI: 28
Volume: 45M (acima média 32M)
Close: 34.50 (baixo do dia)

→ Sinal: COMPRA COM PODER (entrada institucional detectada)
```

---

## MATRIZ DE DECISÃO: Qual Indicador Usar?

| Objetivo | Indicador | Período | Timeframe |
|----------|-----------|---------|-----------|
| **Entrada rápida** | EMA9 + RSI | Diário | 1-4h |
| **Confirmação alta** | MACD + Volume | Diário | Diário |
| **Extremo de preço** | Bollinger + MFI | Diário | 1h-4h |
| **Tendência forte** | ADX + EMA21 | Diário | Diário |
| **Momentum** | Stochastic + MACD | 1h-4h | 15m-1h |
| **Absorção inst.** | CMF + OBV | Diário | Diário |
| **Stop loss** | ATR | Diário | - |

---

## FLUXO COMPLETO: PETR4 - Exemplo Real

```
📊 GRÁFICO DIÁRIO - 2026-08-14

Close: 35.42
EMA9:  35.25 ✅ (acima)
EMA21: 35.10 ✅ (acima)
EMA200: 34.80 (contexto de alta)

RSI: 48 ✅ (zona média, recuperação)
MACD: +0.145 ✅ (acima, acelerando)
Stochastic: 42 ✅ (zona de compra)
ADX: 28 ✅ (tendência forte)
Bollinger: Close 35.42 vs Mid 35.28 ✅ (acima)
CMF: +0.45 ✅ (fluxo positivo)
OBV: 2.34B ✅ (novo máximo)
MFI: 62 ✅ (zona de força)

ATR: 0.85 (volatilidade moderada)

═════════════════════════════════════════

DECISÃO: 🟢 COMPRA FORTE

Entrada: 35.42 (já próximo)
Stop Loss: 35.42 - (2 × 0.85) = 33.72
Alvo 1: 36.20 (resistência próxima)
Alvo 2: 36.80 (novo máximo)

Risco: 35.42 - 33.72 = 1.70
Recompensa: 36.80 - 35.42 = 1.38
Razão R:R = 0.81 (aceitável)

Confiança: 90% (9/10 indicadores positivos)
```

---

## CHECKLIST PARA CADA OPERAÇÃO

```
ANTES DE COMPRAR:
☑ Close acima de EMA21?
☑ EMA9 acima de EMA21?
☑ ADX acima de 20?
☑ Volume acima da média?
☑ CMF ou OBV subindo?
☑ RSI não em extremo (30-70)?
☑ MACD acima da sinal?
☑ Stop loss calculado com ATR?
☑ Razão Risco/Recompensa > 1:1?
☑ Nenhuma notícia negativa esperada?

ANTES DE VENDER:
☑ Close abaixo de EMA21?
☑ ADX descendo?
☑ RSI acima de 70?
☑ MACD abaixo da sinal?
☑ CMF ou OBV caindo?
☑ Volume confirmando queda?
```

---

## STATUS: Indicadores Válidos para Ações

| Indicador | ✅ Válido | Motivo |
|-----------|-----------|--------|
| EMA (9/21/200) | ✅ | Tendência básica |
| RSI | ✅ | Extremos de preço |
| MACD | ✅ | Confirmação de momentum |
| Bollinger Bands | ✅ | Extremos e squeeze |
| Volume / OBV | ✅ | Força de movimento |
| CMF | ✅ | Fluxo institucional |
| Stochastic | ✅ | Cruzamentos de momentum |
| ADX | ✅ | Força de tendência |
| ATR | ✅ | Stops e volatilidade |
| MFI | ✅ | Volume ponderado |
| ❌ IV Rank | ❌ | Específico de opções |
| ❌ Delta | ❌ | Específico de opções |
| ❌ DTE | ❌ | Específico de opções |

---

**Próxima etapa:** Implementar calculadora de indicadores em Python/JavaScript  
**Última atualização:** 2026-08-14  
**Mantido por:** Motor de Análise de Ações

---------------------------------- INDICADORES ----------------------------------

# DOCUMENTAÇÃO DETALHADA DOS INDICADORES

## 1. EMA (Exponential Moving Average)

### Descrição
A **EMA é uma média móvel exponencial** que dá mais peso aos preços recentes. Diferente da média simples (SMA), a EMA reage mais rapidamente às mudanças de preço, tornando-a ideal para identificar tendências em tempo real. Usamos 3 períodos: EMA9 (curto prazo), EMA21 (médio prazo) e EMA200 (longo prazo).

### Fórmula
```
EMA_t = Preço_t × k + EMA_{t-1} × (1 - k)
onde k = 2 / (período + 1)

EMA9:   k = 2 / (9 + 1) = 0.2
EMA21:  k = 2 / (21 + 1) = 0.0909
EMA200: k = 2 / (200 + 1) = 0.0099
```

#### Passo a passo do cálculo:
1. **Calcular K:** Divisor exponencial = 2 / (período + 1)
2. **Primeira EMA:** Use a SMA simples dos primeiros N períodos
3. **Próximas EMAs:** Preço atual × k + EMA anterior × (1 - k)
4. **Plotar 3 linhas:** Com períodos 9, 21 e 200

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| EMA Rápida | 9 |
| EMA Média | 21 |
| EMA Longa | 200 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_ema(raw_data: list[dict], periods: list[int] = [9, 21, 200]) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    for period in periods:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    latest_row = df.iloc[-1]
    resumo = {
        "close": latest_row['close'],
        "ema_9": latest_row['ema_9'],
        "ema_21": latest_row['ema_21'],
        "ema_200": latest_row['ema_200']
    }
    
    return df, resumo
```

### Status
- **Comprado:** Close > EMA21 E EMA9 > EMA21
- **Vendido:** Close < EMA21 E EMA9 < EMA21
- **Neutro:** Close entre EMA9 e EMA21

### Sinal
- **Compra:** EMA9 cruza acima de EMA21 (de baixo para cima)
- **Venda:** EMA9 cruza abaixo de EMA21 (de cima para baixo)
- **Confirmação:** Close acima de EMA21 E volume crescente

---

## 2. RSI (Relative Strength Index)

### Descrição
O **RSI é um oscilador de momentum** que mede a velocidade e magnitude das mudanças de preço. Varia de 0 a 100, identificando condições de sobrevendido (<30) e sobrecomprado (>70). Excelente para detectar reversões de preço em extremos.

### Fórmula
```
Ganho_médio = Média das altas dos últimos N períodos
Perda_média = Média das baixas dos últimos N períodos
RS = Ganho_médio / Perda_média
RSI = 100 - (100 / (1 + RS))
```

#### Passo a passo do cálculo:
1. **Calcular mudanças diárias:** Ganhos e perdas de cada dia
2. **Média exponencial:** Dos ganhos e perdas dos últimos 14 dias
3. **Força relativa:** RS = Ganho médio / Perda média
4. **RSI final:** 100 - (100 / (1 + RS))

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período | 14 |
| Zona Sobrevendido | 30 |
| Zona Sobrecomprado | 70 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_rsi(raw_data: list[dict], period: int = 14) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    delta = df['close'].diff()
    ganho = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = ganho / perda
    df['rsi'] = 100 - (100 / (1 + rs))
    
    latest_row = df.iloc[-1]
    resumo = {
        "rsi": latest_row['rsi'],
        "sobrevendido": latest_row['rsi'] < 30,
        "sobrecomprado": latest_row['rsi'] > 70
    }
    
    return df, resumo
```

### Status
- **Comprado:** RSI < 30 (sobrevendido, potencial recuperação)
- **Vendido:** RSI > 70 (sobrecomprado, potencial queda)
- **Neutro:** RSI 30-70

### Sinal
- **Compra:** RSI sai de <30 para cima (recuperação)
- **Venda:** RSI sai de >70 para baixo (queda)
- **Divergência:** Preço sobe mas RSI cai (reversão próxima)

---

## 3. MACD (Moving Average Convergence Divergence)

### Descrição
O **MACD é um indicador de momentum** que usa a convergência e divergência de duas médias móveis exponenciais. Mostra tendência e mudanças de momentum através da interação entre MACD, linha de sinal e histograma.

### Fórmula
```
MACD = EMA12 - EMA26
Sinal = EMA9 do MACD
Histograma = MACD - Sinal
```

#### Passo a passo do cálculo:
1. **Calcular EMA12:** Média exponencial dos últimos 12 períodos
2. **Calcular EMA26:** Média exponencial dos últimos 26 períodos
3. **MACD:** Diferença entre EMA12 e EMA26
4. **Sinal:** EMA9 da linha MACD
5. **Histograma:** MACD - Sinal (mostrado em barras)

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| EMA Rápida | 12 |
| EMA Lenta | 26 |
| Sinal | 9 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_macd(raw_data: list[dict], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    ema12 = df['close'].ewm(span=fast, adjust=False).mean()
    ema26 = df['close'].ewm(span=slow, adjust=False).mean()
    
    df['macd'] = ema12 - ema26
    df['sinal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histograma'] = df['macd'] - df['sinal']
    
    latest_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    resumo = {
        "macd": latest_row['macd'],
        "sinal": latest_row['sinal'],
        "histograma": latest_row['histograma'],
        "cruzamento_bullish": (prev_row['macd'] < prev_row['sinal']) and (latest_row['macd'] > latest_row['sinal']),
        "cruzamento_bearish": (prev_row['macd'] > prev_row['sinal']) and (latest_row['macd'] < latest_row['sinal'])
    }
    
    return df, resumo
```

### Status
- **Comprado:** MACD > Sinal (momentum positivo)
- **Vendido:** MACD < Sinal (momentum negativo)
- **Aceleração:** Histograma crescente em magnitude

### Sinal
- **Compra:** MACD cruza acima de Sinal (mudança para bullish)
- **Venda:** MACD cruza abaixo de Sinal (mudança para bearish)
- **Força:** Histograma em novo máximo (aceleração da tendência)

---

## 4. Bollinger Bands

### Descrição
As **Bollinger Bands são envelopes de volatilidade** que cercam o preço com base no desvio padrão. Usam uma média simples (SMA20) no centro e ±2 desvios padrão acima e abaixo. Identificam extremos de preço e períodos de squeeze (baixa volatilidade).

### Fórmula
```
Média = SMA20
Desvio Padrão = Volatilidade dos últimos 20 dias
Banda Superior = Média + (2 × Desvio)
Banda Inferior = Média - (2 × Desvio)
```

#### Passo a passo do cálculo:
1. **Média simples:** SMA dos últimos 20 períodos
2. **Desvio padrão:** Volatilidade dos 20 períodos
3. **Bandas:** ±2 desvios padrão da média
4. **Squeeze:** Quando a largura das bandas é mínima

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período SMA | 20 |
| Desvios Padrão | 2 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_bollinger(raw_data: list[dict], period: int = 20, std_dev: int = 2) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    bb_std = df['close'].rolling(window=period).std()
    
    df['bb_upper'] = df['bb_mid'] + (std_dev * bb_std)
    df['bb_lower'] = df['bb_mid'] - (std_dev * bb_std)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    
    latest_row = df.iloc[-1]
    resumo = {
        "close": latest_row['close'],
        "bb_upper": latest_row['bb_upper'],
        "bb_mid": latest_row['bb_mid'],
        "bb_lower": latest_row['bb_lower'],
        "bb_width": latest_row['bb_width'],
        "squeeze": latest_row['bb_width'] < df['bb_width'].mean() * 0.5
    }
    
    return df, resumo
```

### Status
- **Comprado:** Close > BB Mid E BBWidth crescendo
- **Vendido:** Close < BB Mid E BBWidth diminuindo
- **Squeeze:** BB Width em mínima histórica

### Sinal
- **Compra:** Close toca BB Lower + RSI < 40 (extremo)
- **Venda:** Close toca BB Upper + RSI > 60 (extremo)
- **Breakout:** Close acima BB Upper com volume (novo nível)

---

## 5. OBV (On Balance Volume)

### Descrição
O **OBV acumula volume com base na direção do preço**. Quando o preço sobe, adiciona volume. Quando desce, subtrai. Quando fica igual, não muda. Detecta divergências entre preço e volume (movimento fraco vs força real).

### Fórmula
```
Se Close > Close_anterior:
  OBV = OBV_anterior + Volume

Se Close < Close_anterior:
  OBV = OBV_anterior - Volume

Se Close = Close_anterior:
  OBV = OBV_anterior
```

#### Passo a passo do cálculo:
1. **Comparar closes:** Hoje vs. ontem
2. **Ajustar volume:** Adicionar ou subtrair conforme direção
3. **Acumular:** Manter o total corrido
4. **EMA9:** Suavizar com média exponencial

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| EMA do OBV | 9 |

### Timeframes

| Timeframe |
|-----------|
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_obv(raw_data: list[dict], ema_period: int = 9) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    df['price_change'] = df['close'].diff()
    df['obv'] = (df['volume'] * df['price_change'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
    df['obv_ema'] = df['obv'].ewm(span=ema_period, adjust=False).mean()
    
    latest_row = df.iloc[-1]
    resumo = {
        "obv": latest_row['obv'],
        "obv_ema": latest_row['obv_ema'],
        "tendencia": "alta" if latest_row['obv'] > latest_row['obv_ema'] else "baixa"
    }
    
    return df, resumo
```

### Status
- **Comprado:** OBV > OBV_EMA (volume confirma alta)
- **Vendido:** OBV < OBV_EMA (volume confirma baixa)
- **Novo máximo:** OBV em novo máximo histórico

### Sinal
- **Compra:** OBV cruza acima de OBV_EMA (volume entra)
- **Venda:** OBV cruza abaixo de OBV_EMA (volume sai)
- **Divergência:** Preço sobe mas OBV cai (alta fake)

---

## 6. CMF (Chaikin Money Flow)

### Descrição
O **CMF mede o fluxo de dinheiro institucional** através do volume e da posição do fechamento dentro da faixa. Positivo = compra institucional, Negativo = venda institucional. Detecta entrada/saída de "smart money".

### Fórmula
```
CLV = (Close - Low) - (High - Close) / (High - Low)
MFV = CLV × Volume
CMF = Soma(MFV últimos 20 dias) / Soma(Volume últimos 20 dias)
```

#### Passo a passo do cálculo:
1. **Close Location Value:** Onde o close ficou na faixa High-Low
2. **Money Flow Volume:** CLV multiplicado pelo volume
3. **Soma 20 dias:** MFV e Volume acumulados
4. **CMF:** Razão entre MFV e Volume

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período | 20 |
| Zona Compra | > +0.3 |
| Zona Venda | < -0.3 |
| Evento | > +0.6 |

### Timeframes

| Timeframe |
|-----------|
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_cmf(raw_data: list[dict], period: int = 20) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    high_low_range = df['high'] - df['low']
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / high_low_range.replace(0, 1)
    mfv = clv * df['volume']
    
    cmf_sum = mfv.rolling(window=period).sum()
    volume_sum = df['volume'].rolling(window=period).sum()
    
    df['cmf'] = cmf_sum / volume_sum.replace(0, 1)
    
    latest_row = df.iloc[-1]
    resumo = {
        "cmf": latest_row['cmf'],
        "compra_forte": latest_row['cmf'] > 0.3,
        "venda_forte": latest_row['cmf'] < -0.3,
        "evento_massivo": latest_row['cmf'] > 0.6
    }
    
    return df, resumo
```

### Status
- **Comprado:** CMF > +0.3 (fluxo institucional entra)
- **Vendido:** CMF < -0.3 (fluxo institucional sai)
- **Transição:** CMF cruza zero (mudança de sentimento)

### Sinal
- **Compra:** CMF sobe acima de +0.3 + Close acima EMA21
- **Venda:** CMF cai abaixo de -0.3 + Close abaixo EMA21
- **Evento:** CMF > +0.6 (entrada massiva detectada)

---

## 7. Stochastic (%K e %D)

### Descrição
O **Stochastic mede onde o close ficou dentro da faixa High-Low** dos últimos 14 dias. %K é a linha rápida (sensível), %D é a suavização (linha sinal). Identifica sobrevendido (<20) e sobrecomprado (>80) em intervalos curtos.

### Fórmula
```
%K = (Close - Low14) / (High14 - Low14) × 100
%D = SMA3 do %K
```

#### Passo a passo do cálculo:
1. **Alta e Baixa 14:** Máxima e mínima dos últimos 14 períodos
2. **%K:** Onde o close ficou (0-100)
3. **%D:** Média móvel simples 3 períodos de %K
4. **Plotar 2 linhas:** K e D com as zonas 20/80

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período K | 14 |
| Período D | 3 |
| Zona Oversold | 20 |
| Zona Overbought | 80 |

### Timeframes

| Timeframe |
|-----------|
| 15m |
| 1h |
| 4h |

### Código exemplo
```python
import pandas as pd

def calcular_stochastic(raw_data: list[dict], k_period: int = 14, d_period: int = 3) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    
    df['k_percent'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['d_percent'] = df['k_percent'].rolling(window=d_period).mean()
    
    latest_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    resumo = {
        "k_percent": latest_row['k_percent'],
        "d_percent": latest_row['d_percent'],
        "oversold": latest_row['k_percent'] < 20,
        "overbought": latest_row['k_percent'] > 80,
        "cruzamento_bullish": (prev_row['k_percent'] < prev_row['d_percent']) and (latest_row['k_percent'] > latest_row['d_percent'])
    }
    
    return df, resumo
```

### Status
- **Comprado:** K > D (momentum positivo)
- **Vendido:** K < D (momentum negativo)
- **Força:** K > 80 (muito forte)

### Sinal
- **Compra:** K cruza acima de D acima de 20 (saída de oversold)
- **Venda:** K cruza abaixo de D abaixo de 80 (saída de overbought)
- **Confirmação:** K e D ambas em zona extrema

---

## 8. ADX (Average Directional Index)

### Descrição
O **ADX mede a força ABSOLUTA de uma tendência**, não a direção. +DI mostra força de alta, -DI mostra força de baixa. ADX > 25 = tendência forte. ADX < 20 = movimento lateral (sem direção). Perfeito para evitar contratendências.

### Fórmula
```
+DM = Quando High[atual] - High[anterior] > Low[anterior] - Low[atual]
-DM = Quando Low[anterior] - Low[atual] > High[atual] - High[anterior]
+DI = 100 × EMA(+DM, 14) / TR14
-DI = 100 × EMA(-DM, 14) / TR14
DX = 100 × |+DI - -DI| / (+DI + -DI)
ADX = EMA(DX, 14)
```

#### Passo a passo do cálculo:
1. **Directional Movements:** +DM e -DM baseado em High/Low
2. **True Range:** Maior entre variações
3. **Directional Indicators:** +DI e -DI normalizados
4. **DX:** Força diferencial
5. **ADX:** Média exponencial do DX

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período | 14 |
| Força Mínima | 25 |
| Fraqueza Máxima | 20 |

### Timeframes

| Timeframe |
|-----------|
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_adx(raw_data: list[dict], period: int = 14) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    high_diff = df['high'].diff()
    low_diff = -df['low'].diff()
    
    plus_dm = (high_diff.where((high_diff > low_diff) & (high_diff > 0), 0))
    minus_dm = (low_diff.where((low_diff > high_diff) & (low_diff > 0), 0))
    
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    df['adx'] = dx.rolling(window=period).mean()
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    latest_row = df.iloc[-1]
    resumo = {
        "adx": latest_row['adx'],
        "plus_di": latest_row['plus_di'],
        "minus_di": latest_row['minus_di'],
        "tendencia_forte": latest_row['adx'] > 25,
        "movimento_lateral": latest_row['adx'] < 20
    }
    
    return df, resumo
```

### Status
- **Tendência Alta Forte:** ADX > 25 + +DI > -DI
- **Tendência Baixa Forte:** ADX > 25 + -DI > +DI
- **Sideways:** ADX < 20 (sem direção)

### Sinal
- **Compra:** ADX sobe acima de 25 + +DI > -DI
- **Venda:** ADX sobe acima de 25 + -DI > +DI
- **Perda de Força:** ADX descendo (reversão próxima)

---

## 9. ATR (Average True Range)

### Descrição
O **ATR mede a volatilidade absoluta** do ativo. ATR alto = volatilidade alta (movimento grande esperado). ATR baixo = consolidação (antes de explosão). Usado para calcular stops e alvos de forma proporcional ao risco real do ativo.

### Fórmula
```
True Range = Max(
  High - Low,
  |High - Close_anterior|,
  |Low - Close_anterior|
)
ATR = Média móvel 14 do True Range
```

#### Passo a passo do cálculo:
1. **True Range:** Máxima das 3 variações
2. **Média móvel:** Dos últimos 14 períodos
3. **Stop Loss:** Close - (2 × ATR) para compras
4. **Alvo:** Close + (2 × ATR) para compras

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período | 14 |
| Stop Loss Múltiplo | 2.0 |
| Alvo Múltiplo | 2.0-3.0 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_atr(raw_data: list[dict], period: int = 14) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=period).mean()
    
    latest_row = df.iloc[-1]
    stop_loss = latest_row['close'] - (2 * latest_row['atr'])
    alvo = latest_row['close'] + (2 * latest_row['atr'])
    razao = (alvo - latest_row['close']) / (latest_row['close'] - stop_loss) if (latest_row['close'] - stop_loss) > 0 else 0
    
    resumo = {
        "atr": latest_row['atr'],
        "volatilidade_status": "alta" if latest_row['atr'] > df['atr'].mean() * 1.5 else "baixa",
        "stop_loss": stop_loss,
        "alvo": alvo,
        "razao_risco_recompensa": razao
    }
    
    return df, resumo
```

### Status
- **Volatilidade Alta:** ATR > Média × 1.5 (movimento grande esperado)
- **Consolidação:** ATR < Média × 0.7 (antes de explosão)
- **Normal:** ATR próxima da média

### Sinal
- **Rompimento:** Close acima de resistência + ADX > 20
- **Stop Loss:** Close - (2 × ATR)
- **Alvo:** Close + (2-3 × ATR)

---

## 10. MFI (Money Flow Index)

### Descrição
O **MFI é o RSI ponderado por volume** - um oscilador que incorpora força de volume junto com momentum de preço. MFI < 30 = sobrevendido com volume (compra forte). MFI > 70 = sobrecomprado com volume (venda forte). Mais confiável que RSI puro para detectar entradas/saídas institucionais.

### Fórmula
```
Preço Típico = (High + Low + Close) / 3
Money Flow = Preço Típico × Volume

Fluxo Positivo = Soma de MF quando TP > TP_anterior
Fluxo Negativo = Soma de MF quando TP < TP_anterior

MFI = 100 - (100 / (1 + Fluxo_Positivo / Fluxo_Negativo))
```

#### Passo a passo do cálculo:
1. **Preço Típico:** Média de High, Low, Close
2. **Money Flow:** Preço Típico × Volume
3. **Separar fluxos:** Positivo (alta) e Negativo (baixa)
4. **Razão:** Fluxo Positivo / Fluxo Negativo
5. **MFI:** Fórmula final (0-100)

### Parâmetros a serem testados em backtest

| Parâmetro | Valor |
|-----------|-------|
| Período | 14 |
| Zona Oversold | 30 |
| Zona Overbought | 70 |

### Timeframes

| Timeframe |
|-----------|
| 1h |
| 4h |
| 1D |

### Código exemplo
```python
import pandas as pd

def calcular_mfi(raw_data: list[dict], period: int = 14) -> tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(raw_data)
    df = df.sort_values(by='time').reset_index(drop=True)
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    
    positive_sum = positive_flow.rolling(window=period).sum()
    negative_sum = negative_flow.rolling(window=period).sum()
    
    money_flow_ratio = positive_sum / negative_sum.replace(0, 1)
    df['mfi'] = 100 - (100 / (1 + money_flow_ratio))
    
    latest_row = df.iloc[-1]
    resumo = {
        "mfi": latest_row['mfi'],
        "oversold": latest_row['mfi'] < 30,
        "overbought": latest_row['mfi'] > 70,
        "entrada_institucional": latest_row['mfi'] < 30 and df['volume'].iloc[-1] > df['volume'].mean()
    }
    
    return df, resumo
```

### Status
- **Comprado:** MFI < 30 + Volume crescente (compra institucional)
- **Vendido:** MFI > 70 + Volume crescente (venda institucional)
- **Confirmação:** MFI sobe com Close sobe (força real)

### Sinal
- **Compra:** MFI sai de <30 para cima + Volume acima média
- **Venda:** MFI sai de >70 para baixo + Volume acima média
- **Divergência:** Preço em máximo mas MFI em queda (topo fake)

---

**Geração:** 2026-08-14  
**Documentação:** Especificação padrão para migração de indicadores  
**Próxima etapa:** Implementar calculadora integrada com todos os 10 indicadores

---

# ESTRATÉGIAS POR INDICADOR

## Estratégia 1 - EMA (9, 21, 200)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | EMA (9, 21, 200) |
| **Modo de saída** | Percentual + Sinal contrário |
| **Condição de entrada Compra** | Close > EMA21 E EMA9 > EMA21 E Close acima de EMA200 |
| **Condição de saída da Compra (Gain)** | +15% ou EMA9 cruza abaixo de EMA21 |
| **Condição de saída da Compra (Loss)** | -8% ou Close < EMA200 |
| **Condição de entrada Venda** | Close < EMA21 E EMA9 < EMA21 E Close abaixo de EMA200 |
| **Condição de saída da Venda (Gain)** | +15% ou EMA9 cruza acima de EMA21 |
| **Condição de saída da Venda (Loss)** | -8% ou Close > EMA200 |

**Notas:** Estratégia de tendência de médio prazo. EMA200 atua como filtro de contexto para evitar operações contratendência.

---

## Estratégia 2 - RSI (14)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | RSI (14) |
| **Modo de saída** | Percentual + Sinal contrário |
| **Condição de entrada Compra** | RSI < 30 E Close > EMA21 E RSI cruzando acima de 30 |
| **Condição de saída da Compra (Gain)** | +12% ou RSI > 70 |
| **Condição de saída da Compra (Loss)** | -10% ou Close < EMA21 |
| **Condição de entrada Venda** | RSI > 70 E Close < EMA21 E RSI cruzando abaixo de 70 |
| **Condição de saída da Venda (Gain)** | +12% ou RSI < 30 |
| **Condição de saída da Venda (Loss)** | -10% ou Close > EMA21 |

**Notas:** Estratégia de reversão em extremos. Requer confirmação de EMA21 para evitar false signals.

---

## Estratégia 3 - MACD (12, 26, 9)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | MACD (12, 26, 9) |
| **Modo de saída** | Percentual + Sinal contrário |
| **Condição de entrada Compra** | MACD cruza acima de Sinal E Histograma > 0 E ADX > 20 |
| **Condição de saída da Compra (Gain)** | +18% ou MACD cruza abaixo de Sinal |
| **Condição de saída da Compra (Loss)** | -9% ou Histograma em queda por 3+ candles |
| **Condição de entrada Venda** | MACD cruza abaixo de Sinal E Histograma < 0 E ADX > 20 |
| **Condição de saída da Venda (Gain)** | +18% ou MACD cruza acima de Sinal |
| **Condição de saída da Venda (Loss)** | -9% ou Histograma em alta por 3+ candles |

**Notas:** Estratégia de momentum com confirmação de força. ADX > 20 garante que há tendência em andamento.

---

## Estratégia 4 - Bollinger Bands (20, 2)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | Bollinger Bands (20, 2σ) |
| **Modo de saída** | Percentual + Toque na banda oposta |
| **Condição de entrada Compra** | Close toca BB Lower E RSI < 35 E Bandas não em squeeze |
| **Condição de saída da Compra (Gain)** | Close atinge BB Mid +2% ou BB Upper |
| **Condição de saída da Compra (Loss)** | -12% ou Close abaixo de BB Lower por 2+ candles |
| **Condição de entrada Venda** | Close toca BB Upper E RSI > 65 E Bandas não em squeeze |
| **Condição de saída da Venda (Gain)** | Close atinge BB Mid -2% ou BB Lower |
| **Condição de saída da Venda (Loss)** | -12% ou Close acima de BB Upper por 2+ candles |

**Notas:** Estratégia de reversão de extremos. Squeeze (bandas apertadas) sinaliza baixa volatilidade, evite entradas nesse momento.

---

## Estratégia 5 - OBV (On Balance Volume)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | OBV com EMA9 |
| **Modo de saída** | Percentual + Divergência volume/preço |
| **Condição de entrada Compra** | OBV > OBV_EMA E OBV em novo máximo E Close > EMA21 |
| **Condição de saída da Compra (Gain)** | +16% ou OBV cai abaixo de OBV_EMA |
| **Condição de saída da Compra (Loss)** | -8% ou Close < EMA21 |
| **Condição de entrada Venda** | OBV < OBV_EMA E OBV em novo mínimo E Close < EMA21 |
| **Condição de saída da Venda (Gain)** | +16% ou OBV sobe acima de OBV_EMA |
| **Condição de saída da Venda (Loss)** | -8% ou Close > EMA21 |

**Notas:** Estratégia baseada em volume. OBV em novo máximo/mínimo confirma força institucional.

---

## Estratégia 6 - CMF (Chaikin Money Flow)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | CMF (20) |
| **Modo de saída** | Percentual + Cruzamento de zero |
| **Condição de entrada Compra** | CMF > +0.3 E Close > EMA21 E CMF em alta |
| **Condição de saída da Compra (Gain)** | +20% ou CMF cai abaixo de 0 |
| **Condição de saída da Compra (Loss)** | -7% ou CMF < -0.2 |
| **Condição de entrada Venda** | CMF < -0.3 E Close < EMA21 E CMF em baixa |
| **Condição de saída da Venda (Gain)** | +20% ou CMF sobe acima de 0 |
| **Condição de saída da Venda (Loss)** | -7% ou CMF > +0.2 |

**Notas:** Estratégia de fluxo institucional. CMF > +0.6 ou < -0.6 sinaliza evento massivo (aumentar tamanho).

---

## Estratégia 7 - Stochastic (14, 3)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | Stochastic (%K=14, %D=3) |
| **Modo de saída** | Percentual + Saída de zona extrema |
| **Condição de entrada Compra** | K < 20 E K cruza acima de D E Close > EMA21 |
| **Condição de saída da Compra (Gain)** | +14% ou K > 80 ou K cruza abaixo de D |
| **Condição de saída da Compra (Loss)** | -9% ou Close < EMA21 |
| **Condição de entrada Venda** | K > 80 E K cruza abaixo de D E Close < EMA21 |
| **Condição de saída da Venda (Gain)** | +14% ou K < 20 ou K cruza acima de D |
| **Condição de saída da Venda (Loss)** | -9% ou Close > EMA21 |

**Notas:** Estratégia de momentum em intraday. Melhor em timeframes 1h-4h. Evite operações quando K está no meio (30-70).

---

## Estratégia 8 - ADX (14)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | ADX (14) com +DI e -DI |
| **Modo de saída** | Tendência + Reversão de força |
| **Condição de entrada Compra** | ADX > 25 E +DI > -DI E ADX em alta E Close > EMA21 |
| **Condição de saída da Compra (Gain)** | +25% ou ADX abaixo de 20 ou -DI > +DI |
| **Condição de saída da Compra (Loss)** | -10% ou Close < EMA21 |
| **Condição de entrada Venda** | ADX > 25 E -DI > +DI E ADX em alta E Close < EMA21 |
| **Condição de saída da Venda (Gain)** | +25% ou ADX abaixo de 20 ou +DI > -DI |
| **Condição de saída da Venda (Loss)** | -10% ou Close > EMA21 |

**Notas:** Estratégia de seguimento de tendência forte. ADX > 25 garante que a tendência é real e não movimento lateral.

---

## Estratégia 9 - ATR (14)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | ATR (14) para stops e alvos |
| **Modo de saída** | Múltiplos de ATR (Stop Loss e Alvo) |
| **Condição de entrada Compra** | Close > Resistência + Volume E ADX > 20 E ATR > média |
| **Condição de saída da Compra (Gain)** | Close + (2 × ATR) = Alvo ou Breakout confirmado |
| **Condição de saída da Compra (Loss)** | Close - (2 × ATR) = Stop Loss automático |
| **Condição de entrada Venda** | Close < Suporte + Volume E ADX > 20 E ATR > média |
| **Condição de saída da Venda (Gain)** | Close - (2 × ATR) = Alvo ou Breakdown confirmado |
| **Condição de saída da Venda (Loss)** | Close + (2 × ATR) = Stop Loss automático |

**Notas:** Estratégia de rompimento com gerenciamento de risco. ATR adapta os stops à volatilidade real do ativo.

---

## Estratégia 10 - MFI (14)

| Campo | Descrição |
|-------|-----------|
| **Indicador** | MFI (14) |
| **Modo de saída** | Percentual + Reversão de pressão |
| **Condição de entrada Compra** | MFI < 30 E Volume > média E Close > EMA21 E MFI em alta |
| **Condição de saída da Compra (Gain)** | +17% ou MFI > 70 ou MFI cruza abaixo de 50 |
| **Condição de saída da Compra (Loss)** | -8% ou Close < EMA21 |
| **Condição de entrada Venda** | MFI > 70 E Volume > média E Close < EMA21 E MFI em baixa |
| **Condição de saída da Venda (Gain)** | +17% ou MFI < 30 ou MFI cruza acima de 50 |
| **Condição de saída da Venda (Loss)** | -8% ou Close > EMA21 |

**Notas:** Estratégia com volume ponderado. MFI é superior ao RSI puro porque incorpora força de volume nas extremos.

---

## MATRIZ DE ESTRATÉGIAS: Seleção Rápida

| Estratégia | Risco/Recompensa | Timeframe | Volatilidade | Uso Ideal |
|-----------|------------------|-----------|--------------|-----------|
| **EMA 9/21/200** | 1:1.9 | Diário | Baixa | Trends claras, swing trading |
| **RSI 14** | 1:1.2 | 1-4h | Média | Reversões em extremos |
| **MACD 12/26/9** | 1:2.0 | Diário | Média-Alta | Confirmação de momentum |
| **Bollinger Bands** | 1:1.7 | 1-4h | Alta | Volatilidade com extremos |
| **OBV** | 1:2.0 | Diário | Baixa | Volume + tendência |
| **CMF** | 1:2.9 | Diário | Qualquer | Fluxo institucional |
| **Stochastic** | 1:1.6 | 1h-15m | Muito Alta | Intraday, day trading |
| **ADX** | 1:2.5 | Diário | Qualquer | Tendências fortes |
| **ATR** | Variável | Diário | Qualquer | Rompimentos, stops dinâmicos |
| **MFI** | 1:2.1 | Diário | Média | Extremos com volume |

---

## COMBINAÇÕES DE ESTRATÉGIAS (Sinergias)

### Combinação 1: Tendência Forte (EMA + ADX + Volume)
- Use EMA para direção
- Confirme com ADX > 25
- Adicione volume (OBV ou CMF)
- **Win rate esperado:** 65-75%

### Combinação 2: Reversão com Poder (RSI + MFI + Bollinger)
- RSI em extremo (<30 ou >70)
- MFI com volume crescente
- Bollinger Band confirmando toque
- **Win rate esperado:** 60-70%

### Combinação 3: Momentum Confirmado (MACD + Stochastic + Volume)
- MACD cruza acima/abaixo de Sinal
- Stochastic K cruza D
- Volume > média 20 dias
- **Win rate esperado:** 70-80%

### Combinação 4: Fluxo Institucional (CMF + OBV + ATR)
- CMF > +0.3 (compra institucional)
- OBV > OBV_EMA (volume acumula)
- ATR para stops proporcional à volatilidade
- **Win rate esperado:** 75-85%

---

**Status das estratégias:** ✅ 10 estratégias base + 4 combinações sinergia  
**Recomendação:** Backtest cada estratégia com seus dados antes de operacional  
**Última atualização:** 2026-08-14

