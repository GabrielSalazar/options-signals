# Spec — Implementação da Matriz de Sinais v2 (docs/matriz_sinais_b3_v2.md)

**Data:** 2026-07-01
**Status:** Fase 0 aprovada (decisões fechadas com o usuário); Fases 1–4 pendentes
**Documentos-base:** `docs/matriz_sinais_b3_v2.md` (spec de produto), `docs/PLANO_IMPLEMENTACAO_MELHORIAS.md` (roadmap — a matriz é a especificação das Camadas 2–4)

---

## 1. Decisões fechadas (não rediscutir sem novo alinhamento)

| # | Questão | Decisão | Racional |
|---|---|---|---|
| D1 | Bônus de horário dentro do score v2? | **NÃO** — permanece fora da decisão de emissão (mantém a separação `score_tecnico` × `bonus_sessao` da Camada 0). Usado apenas como **desempate de classe**: sinal na fronteira A/B com bônus ≥ 2 sobe de classe. | Um sinal não fica tecnicamente melhor por ser 14h; reintroduzir horário no score seria regressão metodológica. A matriz §5 é sobrescrita neste ponto. |
| D2 | Destino da família DIVERGENCIA | **Absorvida por MOMENTUM** (G9/B7 mantêm +3). MACD (G6/B6) migra de OSCILADOR para MOMENTUM. **✅ já implementado** (`scoring.py::GATILHOS`, caps 4/4/4/4/3). | Divergência é sinal de momentum interno; alinha a taxonomia com as 5 famílias da matriz. |
| D3 | Ichimoku e Williams %R | **CORTADOS da v1 da implementação.** | Williams %R é o Estocástico %K deslocado (correlação ~1); Ichimoku é redundante com SuperTrend+EMA21/200. Reavaliar só se a validação da Fase 4 mostrar lacuna. |
| D4 | Position sizing 1–2% (checklist §6.33) | **Sugestão informativa no card do sinal** (frontend), sem participação na emissão. Campo `sizing_sugerido_pct` no payload. | Decisão de gestão é do usuário; o scanner apenas informa. |

## 2. Pré-requisitos já entregues (antes desta spec)

- Fase A/B de correções do motor (jul/2026): precificação BS com Selic, look-ahead S/R, divergência por pivôs, zonas com ≥2 toques, canal com R², simetria B10/B11, empate não emite.
- Recalibrações da matriz já aplicadas (jul/2026, junto com esta spec):
  - `G3`/`B3`: tolerância S/R = **1,5×ATR** (`CONFIG["sr_tolerancia_atr"]`).
  - Filtro IV: **bloqueio >80, atenção >70, piso <10** (`iv_rank_bloqueio/atencao/piso`) — piso e atenção exigem score ≥7; ainda em `iv_filter_mode="shadow"`.
  - Delta hard filter = **0,10–0,50** (veto absoluto §4 da matriz; a faixa ideal 0,15–0,45 é critério de classe, não de emissão).
  - Famílias: OSCILADOR/MOMENTUM/TENDENCIA/ESTRUTURA/LIQUIDEZ com caps 4/4/4/4/3.

## 3. Tabela canônica de pontos — gatilhos novos (Fase 1)

Regra geral: cada gatilho novo vale no máximo 2; os pesos 3 ficam reservados aos gatilhos "âncora" já existentes (G1/B1 estocástico, G9/B7 divergência, G10/B8 zona). Caps por família seguram a soma.

| ID | Família | Condição (CALL / PUT espelhado) | Pontos |
|---|---|---|---|
| G12/B12 | OSCILADOR | CCI(20) < −100 / > +100 | +2 |
| G13/B13 | MOMENTUM | MFI(14) ≤ 30 / ≥ 70 | +2 |
| G14/B14 | MOMENTUM | OBV subindo/caindo nos últimos 5 candles (regressão simples, slope no sentido) | +1 |
| G15/B15 | MOMENTUM | CMF(20) > 0 / < 0 | +1 |
| G16/B16 | TENDENCIA | SuperTrend(10, 3) na direção do sinal | +1 |
| G17/B17 | TENDENCIA | Fechamento do lado correto da EMA21 | +1 |
| G18/B18 | TENDENCIA | ADX(14) ≥ 25 | +2 |
| G19/B19 | ESTRUTURA | Bollinger Bandwidth < 10% (compressão pré-expansão) + oscilador em zona extrema | +2 |

**Redutores** (novos, aplicados após a soma; score nunca fica negativo):
- OBV **ou** CMF contra o sinal: **−2**
- ADX < 20: **−2**

**Bônus de confluência:** gatilhos em ≥4 famílias distintas: **+2**.

**Vetos técnicos** (Fase 1, cada um atrás de flag própria, default shadow):
- ADX(14) < 15 → veto (lateralidade).
- SuperTrend contra o sinal → veto.
- Bollinger BW > 25% com 0,35 < %B < 0,65 → veto (bandas abertas sem direção).
- Distância ao nível estrutural (S/R 20D ou zona 60D) > 2,5×ATR → G3/B3/G10/B8 não pontuam (já implícito na tolerância 1,5) **e** sinal classificado REVERSAO exige score de classe A.
- EMA200 contra o sinal → **não veta**, exige score +2 (matriz §2.3).

## 4. Classes de emissão (Fase 2 — shadow primeiro)

| Classe | Score (após caps/redutores/bônus) | Famílias distintas | Extras |
|---|---|---|---|
| **A** | ≥ 12 | ≥ 5 | RSI ≤30/≥70; ADX ≥25; delta 0,20–0,35; spread ≤5%; OI ≥1000; VXBR <25 |
| **B** | 8–11 | ≥ 4 | ADX ≥20; delta 0,15–0,45; spread ≤10%; OI ≥500; VXBR <28 |
| **C** | <8 ou qualquer veto | — | **Não emite** |

- Regra dos 60%: nenhuma família pode responder por >60% do score total (senão rebaixa uma classe).
- Desempate de classe pelo bônus de horário (D1).
- Requisitos que dependem de dados ainda indisponíveis (spread, OI, VXBR) são **avaliados como "desconhecido"** e não impedem a classe até a Fase 3 — registrados no payload como `null`.
- Persistir por sinal: `classe_shadow`, `score_v2_shadow`, `redutores_aplicados`, `vetos_shadow` (lista). O motor clássico (min_score=5) continua decidindo até a Fase 4.

## 5. Semântica do checklist §6 da matriz

- **Bloco 1 (filtros obrigatórios)** = vetos hard (executabilidade). Itens 1, 4, 5, 7 já são hard hoje; 2 e 6 dependem da Fase 3; 3 (prêmio real vs. modelado <15%) entra na Fase 2 como campo informativo `divergencia_premio_pct` + veto shadow.
- **Blocos 2–3 (indicadores)** = componentes de score, NÃO vetos — exceto os itens espelhados na lista de vetos §4 (ADX<15, SuperTrend contra).
- **Bloco 4 (confluência)** = regras de classe (seção 4 desta spec).
- **Bloco 5 (gestão)** = estrutura de saída já existente + `sizing_sugerido_pct` informativo (D4).

## 6. Fases de implementação

- **Fase 1 — indicadores/gatilhos sem dependência externa** — ✅ **CONCLUÍDA (2026-07-01)**:
  - **Sondagem do payload opcoes.net**: a chain tem 18 campos (não 10). Campos livres úteis: [4] moneyness ITM/OTM, [6] distância % ao strike, [10] volume financeiro, [11] data do último negócio, [17] ativo base. **Campos 12–16 (OI/bid/ask/vol) vêm como `<img volblur.png>` — bloqueados atrás do paywall para requisições anônimas.** Consequência: a Fase 3 precisará dos arquivos públicos de OI da B3 (ou assinatura do opcoes.net) para os vetos de executabilidade; o campo [11] (data do último negócio) pode virar um proxy fraco de liquidez sem custo.
  - MFI/OBV/CMF em `indicators.py` (via `ta` + fallbacks manuais) e SuperTrend(10,3) manual (`supertrend_dir` = ±1).
  - Gatilhos G12–G19/B12–B19 em `core_engine._avaliar_gatilhos_v2` + registro em `GATILHOS`; redutores RED_FLUXO/RED_ADX (−2); flag `matriz_v2_gatilhos_mode` (shadow default — em "ativo" somam no score e mesclam nos IDs, com piso 0).
  - Vetos técnicos em `scoring.avaliar_vetos_tecnicos` (VETO_ADX, VETO_SUPERTREND, VETO_BW, EMA200_CONTRA) com flags individuais `veto_*_mode` (shadow default); wire em `analisar_ativo` (ativo bloqueia, shadow reporta).
  - Telemetria no payload do sinal: `gatilhos_v2_ids`, `score_v2_extra`, `redutores_v2`, `vetos_v2` (ainda não persistidos no Supabase — persistência de classe/score v2 é Fase 2).
- **Fase 2 — classificação A/B/C em shadow** — ✅ **CONCLUÍDA (2026-07-02)**:
  - `calcular_classe_v2(score, familias_breakdown, score_tecnico)` → (classe, [razoes_downgrade]), aplicando thresholds (A: ≥12 pts + ≥5 famílias; B: ≥8 pts + ≥4 famílias; C: demais).
  - Regra dos 60%: se uma família responde por >60% do score total, downgrade de uma classe (A→B, B→C).
  - `divergencia_premio_pct(premio_real, premio_modelado)` — campo informativo (Bloco 1 item 3 matriz), retorna % de divergência ou None se modelado ≤0.
  - `sizing_sugerido_pct(preco, atr, risco_pct)` — fórmula risco_pct / (atr/preco), retorna % do capital sugerido com stop a ATR, capped a 5%.
  - Telemetria adicionada ao payload: `classe_v2`, `razoes_downgrade_classe`, `divergencia_premio_pct`, `sizing_sugerido_pct` (todos ainda em shadow, não decidem emissão).
  - 662 testes verdes (15 novos para classe/60%/informacionals).
- **Fase 3 — dados externos** (~1–2 semanas): ✅ **CONCLUÍDA (2026-07-02)** — OI + bid/ask via **arquivos públicos B3, validados em 2026-07-01 (gratuitos, sem auth)**:
  - **OI por série**: `https://www.b3.com.br/pesquisapregao/download?filelist=PRAAMMDD.zip` — zip aninhado com XMLs BVBG.086.01 (PriceReport); tag `<OpnIntrst>` por `<TckrSymb>` (~175 mil instrumentos, ~11 MB, publicado pós-fechamento). Validado: PETRG360 OI=518.200 em 30/06/2026. Obs.: `SIAAMMDD.zip` retorna zip vazio; `INAAMMDD.zip` é BVBG.028 (cadastro, sem OI).
  - **Bid/ask de fechamento**: `https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_DDDMMAAAA.ZIP` — campos posicionais PREOFC (82:95) / PREOFV (95:108), TPMERC 070/080 = call/put. Validado: PETRG42 bid 1,43/ask 1,55 (spread 8,4%). Limitação aceita: spread do fechamento D-1, não intraday (a API `cotacao.b3.com.br/mds/api/v1/instrumentQuotation/{ticker}` funciona para opções mas não expõe book).
  - Design: job diário pós-fechamento (padrão `iv_history_service`, ~18h BRT) baixa PR+COTAHIST, extrai séries dos ativos monitorados e persiste em `option_liquidity`; vetos de executabilidade consultam de lá, com `null` = "desconhecido" (não veta).
  - VXBR (coleta diária) e calendário de eventos (Copom hardcode + resultados via brapi) → veto "evento dentro do DTE".
  - **Entregue (2026-07-02):**
    - **OI**: `liquidity_service.py::_parse_pr_zip()` baixa/descompacta PR, extrai `<OpnIntrst>` por `<TckrSymb>`, agrega por ticker base e persiste em `option_liquidity` (migração `013`); job diário 18h BRT no scheduler (`coletar_liquidity_diaria()`).
    - **Bid/ask**: `liquidity_service.py::_parse_cotahist_zip()` extrai PREOFC/PREOFV (TPMERC 070/080), agrega melhor bid/pior ask e calcula spread_pct.
    - **VXBR**: `indicators.py::obter_vxbr_diaria()` via brapi (fail-safe).
    - **Eventos**: `event_service.py::registrar_copom_datas()` cadastra Copom 2026 no boot (tabela `calendar_events`, migração `014`); `obter_evento_na_data()` consulta no ato como fallback em `core_engine.py`.
    - **Vetos shadow**: `scoring.py::avaliar_filtro_liquidez_shadow()` (normal/atencao/bloquear), wired em `core_engine.py::analisar_ativo()` sem bloquear emissão; telemetria (`oi`, `bid`, `ask`, `spread_pct`, `vxbr`, `evento_label`, `filtro_liquidez_decisao/motivo`) persistida em `signals` (migração `015`, `signal_service.py`).
    - **Testes**: `tests/test_liquidity_service.py`, `tests/test_core_engine_liquidity.py`, `tests/test_event_service.py` — suíte total 681 verdes.
- **Fase 4 — validação e ativação** (~1 semana; é a Camada 5 do roadmap): medir em shadow taxa de emissão por classe e hit-rate dos vetados vs. aprovados (backtest + histórico real); ativar por etapas — 1º executabilidade (OI/spread), 2º vetos técnicos, 3º thresholds 8/12. Cada etapa reversível por flag; reverter se derrubar expectância.

## 7. Riscos aceitos e mitigações

- **Motor mudo** (empilhamento de filtros): nada ativa sem medição em shadow (Fase 4); flags individuais.
- **Pseudo-confluência**: caps por família + corte de Ichimoku/Williams (D3).
- **VWAP diário ≠ rolling-20**: o proxy atual fica **fora** do score v2 diário; critério VWAP fica reservado a um futuro modo intraday (documentado, não implementado).
- **Falsa precisão da matriz** (calibrada em ~22–31 trades): todos os thresholds são knobs em `MotorSettings`; tratados como hipóteses da Camada 5.
