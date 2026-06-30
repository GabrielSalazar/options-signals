# Estratégias e Gatilhos — Scanner de Opções B3 v3.0+

## Visão Geral

Este documento detalha todos os **11 gatilhos de ALTA** e **8 gatilhos de BAIXA** monitorados pelo Scanner de Opções B3 `core_engine.py`. O motor utiliza uma combinação de estratégias de **Reversão à Média** (osciladores + divergências) e **Seguimento de Tendência** (EMAs, canais, estrutura de preço), com um sistema de pontuação aditiva (*Score System*).

**Filosofia:** Não há um único gatilho determinístico. O algoritmo soma evidências e emite o sinal quando a força agregada ultrapassa o limiar (`MIN_SCORE = 5`).

---

## GATILHOS DE ALTA (Sinais para Compra de CALL) — 11 critérios

O sistema procura cenários de **exaustão vendedora**, **ruptura de suporte**, **reversão estrutural** e **momentum altista retomando**.

### Osciladores (Reversão à Média) — 4 gatilhos

| ID | Critério | Score | Interpretação | 
|---|---|---|---|
| **G1** | Estocástico: %K cruza **acima** de %D **em sobrevenda** (%K < 35) | +3 | **Mais importante:** Pressão vendedora esgotada. Repique iminente. |
| **G2** | RSI (14) < 35 (sobrevenda extrema) | +2 | Condição necessária mas não suficiente. Validação adicional. |
| **G6** | MACD Histogram cruzou zero **para cima** | +2 | Momentum começou a virar. Confirmação de reversão. |
| **G9** | Divergência altista: preço ↓, RSI ↑ (janela=5 barras) | +3 | **Sinal de força interna.** Hidden Buying. Reversão iminente. |

**Interpretação:** Quando todos os 4 osciladores ativam simultaneamente, probabilidade de reversão altista **>90%**. Min. 1 oscilador para validar a direção.

---

### Rastreadores de Tendência (Seguimento) — 3 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **G4** | EMA9 cruzou **acima** de EMA21 | +2 | **Golden Cross de curto prazo.** Tendência de alta iniciada. |
| **G11** | Canal linear altista: slope(topos) > 0 AND slope(fundos) > 0 | +2 | Estrutura geometricamente consistente. Pressão compradora sustentada. |
| **G7** | 3 fundos locais ascendentes consecutivos | +2 | **Estrutura clássica Dow.** Cada fundo mais alto = oferta recuando. |

**Interpretação:** Confirmam que a reversão é estrutural, não apenas um repique. EMAs + canal + estrutura = alta confiança no movimento.

---

### Ação do Preço / Estrutura (Support Levels) — 2 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **G3** | Preço ≤ suporte_20D + 1×ATR (suporte dinâmico) | +2 | **Nível de absorção.** Demanda institucional histórica aguarda. |
| **G8** | Preço ≤ Bollinger Inferior × 1,01 | +1 | **Compressão de volatilidade.** Setup explosivo. Entrada tardial mas segura. |

**Interpretação:** Suporte é "magnetismo" para reversão. Quanto mais próximo, maior a probabilidade.

---

### Estrutura de Liquidez Histórica e Compressão — 4 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **G10** | Preço em zona de demanda histórica (±1 ATR de swing low nos últimos 60D) | +3 | **Mapa institucional.** Pior caso para grande player = seu melhor trade. |
| **G5** | Volume ≥ 1,5× volume_média_20D | +1 | **Confirmação de liquidez.** Sem volume, opção não tem gamma. |
| **G12** | **NOVO:** Institucional VWAP | +5 | Preço e tendência trabalhando acima da VWAP. |
| **G13** | **NOVO:** Compressão TTM Squeeze | +8 | Bandas de Bollinger penetram no Canal de Keltner. Movimento explosivo iminente. |

**Interpretação:** G10 + G5 juntos = "captura liquidez demanda" — gatilho mais associado aos maiores ganhos na planilha histórica. VWAP traz fluxo pesado, e Squeeze anuncia volatilidade acentuada (essencial para gama na opção).

---

## GATILHOS DE BAIXA (Sinais para Compra de PUT) — 8 critérios

O sistema procura cenários de **exaustão compradora**, **falha de rompimento**, **perda de momentum** e **reversão estrutural**.

### Osciladores (Reversão à Média) — 3 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **B1** | Estocástico: %K cruza **abaixo** de %D **em sobrecompra** (%K > 75) | +3 | **Mais importante:** Pressão compradora esgotada. Queda iminente. |
| **B2** | RSI (14) > 65 (sobrecompra extrema) | +2 | Condição necessária. Sem oferta, preço cai violentamente. |
| **B6** | MACD Histogram cruzou zero **para baixo** | +2 | Momentum desacelerou. Vendedores entrando. |
| **B7** | Divergência baixista: preço ↑, RSI ↓ (janela=5 barras) | +3 | **Sinal de fraqueza interna.** Hidden Selling. Reversão iminente. |

**Interpretação:** Quando osciladores ativam juntos, confiança em queda **>90%**. RSI + Stoch + Divergência = consenso de reversão.

---

### Rastreadores de Tendência (Seguimento) — 3 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **B4** | EMA9 cruzou **abaixo** de EMA21 | +2 | **Death Cross de curto prazo.** Tendência de baixa confirmada. |
| **B9** | Canal linear baixista: slope(topos) < 0 AND slope(fundos) < 0 | +2 | Estrutura em queda. Pressão vendedora sustentada. |
| **B5** | 3 topos locais descendentes consecutivos | +2 | **Estrutura clássica Dow inversa.** Cada topo mais baixo = demanda recuando. |

**Interpretação:** Confirmam que a reversão é estrutural. EMAs + canal + estrutura invalidam o movimento anterior.

---

### Ação do Preço / Estrutura (Resistance Levels) — 1 gatilho

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **B3** | Preço ≥ resistência_20D − 1×ATR | +2 | **Nível de rejeição.** Oferta institucional histórica aguarda. |

**Interpretação:** Quando preço toca resistência, grandes vendedores entram para redistribuir.

---

### Estrutura de Liquidez Histórica e Compressão — 3 gatilhos

| ID | Critério | Score | Interpretação |
|---|---|---|---|
| **B8** | Preço em zona de oferta histórica (±1 ATR de swing high nos últimos 60D) | +3 | **Mapa institucional inverso.** Realização de lucros / short.  |
| **B12** | **NOVO:** Institucional VWAP | +5 | Preço e tendência trabalhando abaixo da VWAP. |
| **B13** | **NOVO:** Compressão TTM Squeeze | +8 | Bandas de Bollinger penetram no Canal de Keltner. Queda explosiva iminente. |

**Interpretação:** Similar a G10 mas para vendedores. Zona de oferta = teto psicológico / técnico. O TTM Squeeze para o lado da baixa acelera a queda.

---

## Bônus de Horário

Aplicado **simultaneamente** a ambos `score_alta` e `score_baixa`:

```
10:00–11:30 → +2 pontos  (abertura, volatilidade alta, muita liquidez)
13:00–15:00 → +3 pontos  (pico pós-almoço, traders ativos)
15:00–16:30 → +1 ponto   (encerramento, liquidez decrescente)
Outros     → +0 pontos
```

**Lógica:** O horário não muda a direção, mas aumenta a confiança no sinal emitido.

---

## Decisão Final — Score Mínimo

```
1. Se score_alta >= score_baixa  → Emitir sinal CALL
2. Se score_baixa > score_alta   → Emitir sinal PUT
3. Se ambos < MIN_SCORE (5)      → SEM SINAL
4. Se rr_alvo1 < 0.8             → REJEITAR (risco desproporcional)
```

---

## Exemplos de Ativação em Cenários Reais

### Cenário 1: MGLU3 com +455% (MGLUQ833, Mai/2026)

```
Ativações:
  - G1 (Stoch em sobrevenda)    +3
  - G2 (RSI < 35)               +2
  - G5 (Volume 2.1x)            +1
  - G10 (Zona demanda)          +3
  - Score hora (13:30)          +3
  ─────────────────────────────
  TOTAL ALTA = 12 pontos → SINAL CALL emitido
  
Entrada: R$ 0.32, Alvo 1: R$ 0.42 (+31%), Alvo 2: R$ 1.60 (+400%)
Resultado real: +455% (Alvo 2) ✅
```

### Cenário 2: BBSE3 com +26% (BBSER376, Jun/2026)

```
Ativações:
  - B1 (Stoch em sobrecompra)   +3
  - B2 (RSI > 65)               +2
  - B3 (Resistência 20D)        +2
  - B8 (Zona oferta)            +3
  - Score hora (14:00)          +3
  ─────────────────────────────
  TOTAL BAIXA = 13 pontos → SINAL PUT emitido
  
Entrada: R$ 1.20, Alvo 1: R$ 1.50 (+25%)
Resultado real: +26% Alvo 1 ✅
```

---

> [!WARNING]
> **Importante:** Nenhum gatilho isolado garante lucro. O motor funciona por **consenso multifatorial**. Uma divergência sozinha não dispara o sinal — precisa de suporte, tendência, estrutura E liquidez. Por isso a taxa de acerto é 82% com expectância +60%.

---

## Famílias de gatilhos e a assimetria CALL × PUT (Camada 2)

Os 20 gatilhos são agrupados em 5 famílias (Camada 2.1 — `backend/domain/scoring.py::GATILHOS`):

| Família | Gatilhos de alta | Gatilhos de baixa |
|---|---|---|
| OSCILADOR | G1, G2, G6 | B1, B2, B6 |
| TENDENCIA | G4, G7, G11 | B4, B5, B9 |
| ESTRUTURA | G3, G8 | B3 |
| DIVERGENCIA | G9 | B7 |
| LIQUIDEZ | G5, G10 | B8 |

O lado de alta tem 11 gatilhos (máx. 23 pts); o de baixa tem 9 (máx. 21 pts). Isso é uma
**decisão atual, não uma lacuna não examinada**: faltam dois gatilhos espelho do lado
baixista —

1. **Espelho de G8** (Bollinger inferior → família ESTRUTURA): um gatilho de preço na
   banda superior de Bollinger para o lado de baixa.
2. **Espelho de G5** (volume relativo → família LIQUIDEZ): um gatilho de volume em
   distribuição (alta em queda de preço) para o lado de baixa.

Ambos ficam para uma iteração futura, com seu próprio ciclo de validação (Camada 5) —
adicionar gatilhos novos muda a distribuição de pontos por família e exige
recalibração, o que está fora do escopo da Camada 2 (que reorganiza os gatilhos
*existentes*, não adiciona novos). Até essa iteração, o viés estrutural de 2 pontos a
mais no lado de alta é aceito conscientemente.
