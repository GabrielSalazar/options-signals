# Matriz de Sinais de Qualidade para Opções de Ações na B3

## Documento de referência para emissão de sinais CALL e PUT — Versão 2.0

---

## 1. Introdução

Este documento define os parâmetros mínimos e máximos, thresholds de emissão e regras de veto para o scanner de sinais de opções sobre ações na B3 (Bolsa Brasileira). O objetivo é eliminar ruído operacional e garantir que apenas sinais com alta probabilidade de executabilidade e relação risco/retorno favorável sejam apresentados.

A matriz foi calibrada para opções OTM (Out of The Money) de ações do mercado brasileiro, considerando liquidez local, volatilidade típica e dinâmica de precificação de opções americanas. Esta versão 2.0 incorpora indicadores de força de tendência, fluxo de capital e níveis institucionais para reduzir falsos positivos em mercados sem direção definida.

---

## 2. Matriz de Thresholds por Indicador

### 2.1 Osciladores de Momentum

| Indicador | Parâmetro | CALL (mínimo / máximo) | PUT (mínimo / máximo) | Observação |
|---|---|---|---|---|
| **RSI** | RSI(14) | ≤ 35 / < 50 | ≥ 65 / > 50 | Abaixo de 35: sobrevenda extrema. Acima de 65: sobrecompra. Evitar emitir se RSI já cruzou 50 no meio do movimento. |
| **Estocástico** | %K / %D | %K < 35 e cruzamento %K > %D | %K > 65 e cruzamento %K < %D | Zonas < 20 (CALL) e > 80 (PUT) são mais fortes. Cruzamento dentro da zona extrema é o gatilho real. |
| **Williams %R** | %R(14) | < −80 / < −50 | > −20 / > −50 | Oscilador complementar ao Estocástico. Leituras < −80 indicam fundo de range; > −20 indicam topo. |
| **CCI** | CCI(20) | < −100 / < 0 | > +100 / > 0 | Commodity Channel Index. < −100: preço muito abaixo da média estatística; > +100: muito acima. |

### 2.2 Momentum e Fluxo de Capital

| Indicador | Parâmetro | CALL (mínimo / máximo) | PUT (mínimo / máximo) | Observação |
|---|---|---|---|---|
| **MACD Histograma** | Diff | Cruzamento de negativo para positivo | Cruzamento de positivo para negativo | Mede aceleração independente dos osciladores. Geralmente confirma 1–2 candles após o RSI. |
| **MFI** | MFI(14) | ≤ 30 / < 50 | ≥ 70 / > 50 | Money Flow Index. RSI ponderado por volume. < 30: pressão vendedora esgotada com confirmação de volume. |
| **OBV** | Direção | OBV subindo nos últimos 5 candles | OBV caindo nos últimos 5 candles | On-Balance Volume. Acumula volume de alta/baixa. Direção deve confirmar o sinal — divergência é redutor. |
| **Chaikin Money Flow** | CMF(20) | > 0 / > −0,10 | < 0 / < +0,10 | Mede fluxo de capital acumulado. Positivo = compra institucional predominante; negativo = venda. |

### 2.3 Tendência e Força de Direção

| Indicador | Parâmetro | CALL (mínimo / máximo) | PUT (mínimo / máximo) | Observação |
|---|---|---|---|---|
| **EMA 21** | Posição do preço | Fechamento > EMA21 | Fechamento < EMA21 | Filtro de tendência de curto prazo. Sinais contra EMA21 exigem score mais alto e ADX > 25. |
| **EMA 200** | Posição do preço | Preferencialmente > EMA200 | Preferencialmente < EMA200 | Filtro de tendência de longo prazo. Não é gatilho isolado, mas sinais contra EMA200 exigem score +2. |
| **ADX** | ADX(14) | > 25 / sem teto | > 25 / sem teto | Average Directional Index. Mede força da tendência, não direção. < 20 = mercado lateral; > 25 = tendência com força. |
| **SuperTrend** | Direção | SuperTrend verde (bullish) | SuperTrend vermelho (bearish) | Indicador de tendência baseado em ATR. Deve alinhar com a direção do sinal. |
| **Ichimoku** | Tenkan/Kijun | Tenkan > Kijun e preço acima da nuvem | Tenkan < Kijun e preço abaixo da nuvem | Confirmação de tendência multi-timeframe. Cruzamento Tenkan/Kijun é sinal de momentum. |

### 2.4 Estrutura de Preço e Volatilidade

| Indicador | Parâmetro | CALL (mínimo / máximo) | PUT (mínimo / máximo) | Observação |
|---|---|---|---|---|
| **ATR** | Distância até nível | Preço dentro de ±1,5 ATR do suporte 20D | Preço dentro de ±1,5 ATR da resistência 20D | Tolerância para ativos voláteis. Acima de 2,5 ATR, o nível estrutural perde validade. |
| **Bollinger %B** | %B | ≤ 0,05 / < 0,50 | ≥ 0,95 / > 0,50 | Posição do preço dentro das bandas. 0 = banda inferior; 1 = banda superior. |
| **Bollinger Bandwidth** | BW | < 10% / < 25% | < 10% / < 25% | Compressão das bandas. BW < 10% indica volatilidade muito baixa — possível setup pré-expansão. |
| **Suporte/Resistência 20D** | Nível | Preço dentro de 1,5 ATR do suporte | Preço dentro de 1,5 ATR da resistência | Mínima/máxima dos últimos 20 candles. Zona de reação institucional de curto prazo. |
| **Zona histórica 60D** | Swing low/high | Preço dentro de ±1 ATR de swing low | Preço dentro de ±1 ATR de swing high | Mínimos/máximos locais dos últimos 60 candles. Mapa de demanda/oferta institucional. |

### 2.5 Liquidez, Precificação e Contexto da Opção

| Indicador | Parâmetro | CALL (mínimo / máximo) | PUT (mínimo / máximo) | Observação |
|---|---|---|---|---|
| **Volume relativo** | Volume / Média 20D | ≥ 1,5× / sem teto | ≥ 1,5× / sem teto | Mínimo 1,5× confirma presença institucional. Abaixo disso, descarte por ruído. |
| **VWAP** | Posição do preço | Fechamento > VWAP diário | Fechamento < VWAP diário | Volume Weighted Average Price. Nível médio de preço do dia. Acima = pressão compradora dominante. |
| **OI da série** | Contratos em aberto | ≥ 500 / ideal ≥ 1.000 | ≥ 500 / ideal ≥ 1.000 | Série com OI < 500 tem spread inaceitável e risco de não conseguir sair pelo preço justo. |
| **Spread bid-ask** | (Ask − Bid) / Bid | ≤ 10% / ideal ≤ 5% | ≤ 10% / ideal ≤ 5% | Spread > 10% destrói o R/R teórico. Se > 15%, veto automático. |
| **IV Rank/Percentile** | Percentil histórico 6M | 10–70 / ideal 20–60 | 10–70 / ideal 20–60 | Evitar comprar opções no percentil 80–100 (IV cara, risco de IV crush). Abaixo de 10 o movimento tende a ser lento demais. |
| **Delta** | Δ da opção | 0,15–0,45 / ideal 0,20–0,35 | −0,15 a −0,45 / ideal −0,20 a −0,35 | Abaixo de 0,15: prêmio muito barato, gamma fraco. Acima de 0,45: muito próximo do ATM, R/R piora. |
| **DTE** | Dias úteis até venc. | 6–30 / ideal 10–20 | 6–30 / ideal 10–20 | < 6: theta-decay acelerado. > 30: gamma diluído, exige movimento desproporcional. |
| **VXBR** | Nível de volatilidade | Contexto: < 25 | Contexto: < 25 | VXBR > 25 → mercado tenso, exigir score +2 e reduzir tamanho. VXBR > 30 → veto ou apenas score 10+. |

---

## 3. Regras de Emissão por Classe

### Classe A — Prioridade Alta

| Requisito | Valor |
|---|---|
| Score | ≥ 12 |
| Gatilhos por família | Pelo menos 1 em 5 famílias diferentes (oscilador, momentum, tendência, estrutura, liquidez/contexto) |
| RSI | ≤ 30 (CALL) ou ≥ 70 (PUT) |
| Estocástico ou Williams %R | Zona extrema com cruzamento confirmado |
| ADX | ≥ 25 |
| Delta | 0,20–0,35 |
| Spread bid-ask | ≤ 5% |
| OI da série | ≥ 1.000 |
| VXBR | < 25 |
| VWAP | Alinhado com direção do sinal |
| OBV | Alinhado com direção do sinal |

### Classe B — Prioridade Média

| Requisito | Valor |
|---|---|
| Score | 8 a 11 |
| Gatilhos por família | Pelo menos 1 em 4 famílias diferentes |
| RSI | ≤ 35 (CALL) ou ≥ 65 (PUT) |
| ADX | ≥ 20 |
| Delta | 0,15–0,45 |
| Spread bid-ask | ≤ 10% |
| OI da série | ≥ 500 |
| VXBR | < 28 |
| VWAP | Preferencialmente alinhado |

### Classe C — Não Emitir

| Requisito | Valor |
|---|---|
| Score | < 8 |
| Gatilhos por família | Concentrado em 1 ou 2 famílias |
| Spread bid-ask | > 10% |
| OI da série | < 500 |
| IV Percentil | > 80 |
| VXBR | > 30 |
| DTE | < 6 ou > 30 |
| RSI | Entre 40–60 |
| ADX | < 15 |
| Bollinger Bandwidth | > 25% com preço no meio das bandas (mercado sem direção) |

---

## 4. Regras de Veto Absoluto

Um sinal deve ser descartado imediatamente se qualquer uma das condições abaixo for atendida:

- [ ] **Spread bid-ask > 10%**: a opção existe na tela, mas não é executável pelo preço justo.
- [ ] **OI da série < 500**: risco de não conseguir sair, ou sair com prejuízo de liquidez.
- [ ] **Delta < 0,10 ou > 0,50**: fora da zona OTM operável; gamma ou custo inadequado.
- [ ] **DTE < 6 dias úteis**: theta-decay acelerado destrói o setup antes do movimento.
- [ ] **IV Percentil > 80**: opção está cara demais; comprar aqui é pagar prêmio de evento.
- [ ] **VXBR > 30 e sinal de reversão**: reversões em pânico de mercado têm taxa de falha alta.
- [ ] **ADX < 15**: mercado sem força de direção; operar reversão aqui é tentar adivinhar fundo/topo em lateralidade.
- [ ] **Score > 50% vindo de uma única família**: confluência fraca, ruído elevado.
- [ ] **Preço distante > 2,5 ATR do nível estrutural**: o suporte/resistência perdeu validade local.
- [ ] **Evento relevante dentro do DTE**: resultados, Copom, fato relevante — gap pode invalidar stop.
- [ ] **Divergência OBV forte contra o sinal**: fluxo de capital está indo na direção oposta à do preço, indicando que o movimento não tem sustentação institucional.
- [ ] **SuperTrend contra o sinal**: tentar comprar CALL com SuperTrend vermelho ou PUT com SuperTrend verde é operar contra a estrutura de momentum atual.
- [ ] **Bollinger Bandwidth > 20% com preço próximo da média**: bandas abertas sem direção = mercado errático, não operável com opções direcionais.

---

## 5. Sistema de Pontuação (Score) — Versão 2.0

### Famílias e pesos máximos

| Família | Indicadores | Peso máximo | Observação |
|---|---|---|---|
| Osciladores | RSI, Estocástico, Williams %R, CCI | 4 pts | Sem concentração: máximo 3 pts de qualquer indicador individual |
| Momentum | MACD, MFI, OBV, CMF | 4 pts | Divergência de OBV contra o sinal aplica redutor de −2 pts |
| Tendência | EMA 21/200, SuperTrend, Ichimoku, ADX | 4 pts | ADX ≥ 25 vale +2; ADX < 15 vale 0 e ativa veto |
| Estrutura | ATR, Bollinger (%B, BW), S/R 20D, Zona 60D | 4 pts | BW < 10% em setup de reversão vale +2 (compressão pré-expansão) |
| Liquidez/Contexto | Volume, VWAP, OI, Spread, IV Rank, Delta, DTE, VXBR | 3 pts | Volume ≥ 2× vale +2; spread ≤ 5% vale +1 |
| Bônus de Horário | Janelas de liquidez | +3 pts | 10h–11h30: +2; 13h–15h: +3; 15h–16h30: +1 |

### Regras de score

- **Score mínimo para emissão**: 8 pts
- **Score Classe A**: ≥ 12 pts
- **Score Classe B**: 8–11 pts
- **Máximo por família**: 60% do score total (evitar concentração)
- **Redutor de divergência**: OBV ou CMF contra o sinal = −2 pts
- **Redutor de ADX baixo**: ADX < 20 = −2 pts
- **Bônus de confluência**: gatilhos em 4+ famílias = +2 pts

---

## 6. Checklist de Execução Final

Antes de apresentar o sinal:

### Bloco 1 — Filtros Obrigatórios

1. [ ] O ativo está líquido de forma consistente (volume médio ≥ 1.000.000)?
2. [ ] A série de opção tem OI ≥ 500 (ideal ≥ 1.000), negócios recentes e spread ≤ 10%?
3. [ ] O prêmio real está próximo do prêmio modelado (divergência < 15%)?
4. [ ] O DTE está na janela operacional (6–30 dias úteis, ideal 10–20)?
5. [ ] A Delta está na faixa operacional (0,15–0,45)?
6. [ ] Não há evento relevante dentro da janela do trade (resultado, ex-dividendo, Copom, macro)?
7. [ ] O ativo não teve sinal nos últimos 3 dias úteis (cooldown)?

### Bloco 2 — Indicadores Técnicos

8. [ ] RSI está na zona correta para a direção (≤ 35 CALL, ≥ 65 PUT).
9. [ ] Estocástico ou Williams %R cruzou na zona extrema com direção confirmada.
10. [ ] MACD histograma cruzou zero no sentido do sinal.
11. [ ] CCI está na zona extrema (< −100 CALL, > +100 PUT) ou pelo menos no lado correto.
12. [ ] MFI está na zona extrema (≤ 30 CALL, ≥ 70 PUT) ou confirmando direção.
13. [ ] Preço está do lado correto da EMA21 (acima para CALL, abaixo para PUT).
14. [ ] ADX ≥ 25 (Classe A) ou ≥ 20 (Classe B). ADX < 15 = veto.
15. [ ] SuperTrend está alinhado com a direção do sinal.
16. [ ] Ichimoku (Tenkan/Kijun) confirma direção e preço está do lado correto da nuvem.
17. [ ] A distância até o nível estrutural (S/R 20D ou zona 60D) está dentro de ±1,5 ATR.
18. [ ] Bollinger %B está na zona extrema (≤ 0,05 CALL, ≥ 0,95 PUT) ou compressão BW < 10%.

### Bloco 3 — Liquidez, Fluxo e Contexto

19. [ ] Volume relativo ≥ 1,5× (ideal ≥ 2×).
20. [ ] VWAP está alinhado com a direção do sinal.
21. [ ] OBV está alinhado com a direção do sinal nos últimos 5 candles.
22. [ ] CMF está alinhado com a direção do sinal (> 0 CALL, < 0 PUT).
23. [ ] IV Percentil está entre 10 e 70 (ideal 20–60).
24. [ ] VXBR não está em nível de veto (> 30). Se entre 25–30, score compensa.
25. [ ] Spread bid-ask ≤ 10% (ideal ≤ 5%).

### Bloco 4 — Confluência e Score

26. [ ] Score veio de pelo menos 4 famílias técnicas diferentes (Classe A) ou 3 (Classe B).
27. [ ] Nenhuma família responde por mais de 60% do score total.
28. [ ] Não há gatilho forte contraditório de peso alto na direção oposta.
29. [ ] Score mínimo atingido: ≥ 8 (Classe B) ou ≥ 12 (Classe A).

### Bloco 5 — Gestão de Risco

30. [ ] Zona de entrada definida com tolerância de spread (±3,5%).
31. [ ] Alvo 1, Alvo 2 e Alvo Final definidos com lógica de scale-out.
32. [ ] Stop loss definido como percentual fixo do prêmio (−43%).
33. [ ] Tamanho da posição calculado como % fixo do capital de risco (1–2%).
34. [ ] O trade seria tomado independentemente do resultado das operações anteriores.

**Regra de ouro:** Se qualquer item de veto falhar, o sinal não sai. Se todos passarem, emite na classe A ou B conforme o score total.

---

## 7. Estrutura de Saída (Gerenciamento de Risco)

| Nível | Cálculo | Lógica |
|---|---|---|
| Entrada Mín | prêmio × 0,965 | Spread do book (±3,5%) |
| Entrada Máx | prêmio × 1,035 | Spread do book (±3,5%) |
| Alvo 1 | prêmio × 1,25 | Realização parcial (50% da posição) |
| Alvo 2 | prêmio × 3,50 | Alvo técnico principal |
| Alvo Final | prêmio × 8,00 | Especulação remanescente |
| Stop Loss | prêmio × 0,57 | Proteção absoluta (−43%) |

---

## 8. Notas sobre o Mercado Brasileiro (B3)

- **Liquidez da série**: A B3 divulga diariamente posições em aberto (OI) por série. Isso deve ser usado como filtro primário antes de qualquer análise técnica. Série sem liquidez real, mesmo em ativo líquido, é inoperável.
- **Vencimentos**: A B3 negocia opções com vencimento toda sexta-feira (séries semanais), além da série mensal na 3ª sexta. O motor deve preferir séries com DTE entre 10 e 20 dias úteis.
- **Black-Scholes**: O modelo de apreçamento da B3 serve como referência, mas o prêmio real do book deve sempre substituir a estimativa teórica quando disponível.
- **Gamma Exposure (GEX)**: Popular no mercado americano, mas com aplicação limitada no Brasil devido à menor liquidez em opções de curtíssimo prazo e obrigações distintas de hedge dos formadores de mercado locais. Se testado, deve ser usado como filtro experimental de baixo peso.
- **IV Rank/Percentile**: Deve ser calculado com base no histórico de volatilidade implícita da própria B3 ou via opcoes.net.br, não apenas IV histórica do ativo.
- **Regra dos 3 dias**: Cooldown obrigatório entre sinais do mesmo ativo para evitar overtrading e exposição duplicada em janelas de curto prazo.
- **ADX no mercado brasileiro**: Ativos brasileiros frequentemente ficam em consolidação lateral de 10–20 candles. ADX < 15 nesse período é o filtro mais eficiente para evitar sinais de reversão falsa. Só operar reversões quando ADX ≥ 20 e confirmar com ≥ 25 para Classe A.
- **VWAP intraday**: Para sinais intraday (day trade em opções), o VWAP diário funciona como nível de equilíbrio institucional. Fechamento acima do VWAP em CALL ou abaixo em PUT confirma que o fluxo dominante do dia está alinhado.
- **Bollinger Bandwidth e compressão**: No mercado brasileiro, BW < 10% frequentemente precede movimentos de 5–15% em 3–5 dias. Usar como gatilho extra de timing quando combinado com osciladores em zona extrema.

---

## 9. Exemplos de Sinais Aprovados

### Exemplo 1 — Classe A (CALL)

**Ativo**: PETR4
**Direção**: CALL
**Score**: 14

**Gatilhos ativados:**
- Estocástico em sobrevenda com cruzamento altista (+3)
- RSI < 30 (+3)
- Williams %R < −80 (+2)
- Zona de demanda histórica (+3)
- Volume 2,1× média (+2)
- MACD histograma cruzando para cima (+2)
- ADX = 28 (+2)
- SuperTrend verde (+1)
- OBV subindo (+1)
- Bônus de horário (+1)

**Parâmetros da opção:**
- Delta: 0,25
- DTE: 14 dias úteis
- IV Percentil: 45
- OI da série: 2.400
- Spread bid-ask: 3%
- VXBR: 22

**Resultado**: Classe A emitido. Operação com alvo 1 em +25%, alvo 2 em +250%, stop em −43%.

### Exemplo 2 — Classe A (PUT)

**Ativo**: BBSE3
**Direção**: PUT
**Score**: 13

**Gatilhos ativados:**
- Estocástico em sobrecompra com cruzamento baixista (+3)
- RSI > 70 (+3)
- CCI > +100 (+2)
- Resistência 20D (−1 ATR) (+2)
- Zona de oferta histórica (+3)
- CMF negativo (+1)
- SuperTrend vermelho (+1)
- Bônus de horário (+1)

**Parâmetros da opção:**
- Delta: −0,28
- DTE: 12 dias úteis
- IV Percentil: 38
- OI da série: 1.800
- Spread bid-ask: 4%
- VXBR: 20

**Resultado**: Classe A emitido. Operação com alvo 1 em +25%, alvo 2 em +250%, stop em −43%.

---

## 10. Ativos de Referência da B3

### Alta volatilidade (OTM 12%)
MGLU3, BEEF3

### Volatilidade média-alta (OTM 10%)
BRKM5, USIM5, ASAI3, MRVE3, BRAV3

### Volatilidade média (OTM 7–8%)
VALE3, SUZB3, LREN3, RADL3, GGBR4, GOAU4, KLBN11

### Baixa volatilidade (OTM 5–6%)
ITUB4, BBDC4, ABEV3, BBSE3, BBAS3, SANB11, BPAC11, WEGE3, EGIE3, PETR4, EVEN3, COGN3, RENT3

### Ultra-baixa volatilidade (OTM 4%)
BOVA11

---

*Documento gerado em 01 de julho de 2026 — Versão 2.0. Valores sujeitos a recalibração periódica conforme evolução do mercado e performance da base histórica.*
