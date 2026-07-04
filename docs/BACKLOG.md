# Backlog — Motor de Sinais B3

Itens pendentes priorizados. Referência cruzada: plano da Camada PUCK
(`docs/superpowers/plans/2026-07-02-puck-adaptacao-motor.md`) e comparação com o
documento **OPÇÕES B3 v8.2 "ZERO NOISE"** (`docs/OPCOES_B3_v2_Documentacao.docx`).

Última atualização: 2026-07-03.

---

## Gaps do v8.2 (dos 9 filtros / gestão do trade)

Estes três itens são o que falta para o motor cobrir integralmente o v8.2. Os
demais filtros do v8.2 já estão implementados ou têm equivalente superior
(ver `docs/CHANGELOG.md` e a análise da Camada PUCK).

### Gap 1 — Buffer de 0,1×ATR no stop
- **O que o v8.2 faz:** `stop = Close − (1,5×ATR) − (0,1×ATR)` — folga extra de 10%
  do ATR abaixo do stop padrão.
- **Por quê:** evita que micro-oscilações intraday (ruído) estourem o stop antes
  do movimento direcional acontecer ("caça-stop").
- **Hoje:** `ativo_stop = entrada − 1,5×ATR` (sem buffer), em
  `_niveis_ativo_atr` (`backend/services/core_engine.py`), exibido no card e no
  Telegram.
- **Esforço:** Trivial (~15 min). Novo knob `atr_stop_buffer = 0.1` em
  `MotorSettings`; subtrair `atr_stop_buffer × ATR` no `ativo_stop`; ajustar teste.
- **Impacto:** Baixo e isolado (só o nível informativo de stop no ativo). Não
  afeta emissão.
- **Bloqueio:** Nenhum — pode ser feito a qualquer momento.

### Gap 2 — Trailing stop após o TP1
- **O que o v8.2 faz:** ao atingir o TP1, ativa trailing que segue o preço a
  1×ATR (`novoTrail := Close − ATR`, só sobe). Protege o lucro parcial depois do
  primeiro alvo.
- **Por quê:** trava lucro parcial e deixa a posição correr com risco travado.
- **Hoje:** Inexistente. Os níveis (`ativo_stop/tp1/tp2`) são calculados uma vez
  no sinal e ficam estáticos; não há reavaliação diária de sinal aberto.
- **Esforço:** Médio (~1-2 sessões). Lugar natural: `outcome_service` (já roda
  diariamente reprecificando sinais); calcularia o trailing por dia e atualizaria
  o stop efetivo.
- **Impacto / dependência:** Interage com a decisão de **medir o desfecho pelo
  ativo subjacente** (hoje o outcome acompanha o prêmio da opção, não o ativo).
  É a parte mais sensível.
- **Bloqueio:** Adiado até a Fase 4 (decisão sobre outcome pelo subjacente).

### Gap 3 — OBV > EMA(OBV)
- **O que o v8.2 faz:** filtro 6 exige `OBVacum > EMA(OBV)` — OBV acima da própria
  média exponencial.
- **Por quê:** confirmação de fluxo de volume mais estável que a variação de curto
  prazo.
- **Hoje:** Temos `obv` e os gatilhos G14/B14, mas por **slope de regressão sobre
  5 candles**, não `OBV > EMA(OBV)`. Conceito coberto, fórmula diferente.
- **Esforço:** Baixo (~30 min). Coluna `obv_ema` (EMA do OBV) em
  `backend/domain/indicators.py`; trocar/complementar a condição de G14/B14 para
  `obv > obv_ema`; ajustar testes.
- **Impacto:** Baixo (gatilho em shadow na matriz v2; mudar a fórmula não afeta
  emissão até a flag ativar).
- **Bloqueio:** Nenhum — só decidir se troca a fórmula (slope-5) ou mantém as duas.

### Prioridade dos gaps

| Gap | Esforço | Impacto | Bloqueio |
|-----|---------|---------|----------|
| 1 — Buffer 0,1×ATR no stop | Trivial (~15 min) | Baixo/isolado | Nenhum |
| 3 — OBV > EMA(OBV) | Baixo (~30 min) | Baixo (shadow) | Nenhum |
| 2 — Trailing pós-TP1 | Médio (1-2 sessões) | Médio | Fase 4 (outcome pelo subjacente) |

**Recomendação:** gaps 1 e 3 são baratos e sem bloqueio — podem ser fechados a
qualquer momento (inclusive enquanto os dados da Fase 4 acumulam). O gap 2 é o
mais valioso, mas deve esperar a Fase 4 por tocar na forma de medir o desfecho.

---

## Outros itens pendentes (Camada PUCK / matriz v2)

- **Fase 4 — validação shadow (marco principal):** medir frequência e hit-rate
  dos gatilhos PUCK (G20-G22/B20-B22), vetos de liquidez e classe v2 via
  `supabase/queries/fase4_monitor_shadow.sql`; então ativar flags por etapas.
  Hit-rate depende de tempo (swing, desfecho em semanas).
- **Delta/DTE por classe:** A→ITM (0,40-0,55 / 30-45 du), B→ATM, C→OTM curto.
  Mexe na emissão (strike/vencimento) → exige classe_v2 validada + recalibração +
  re-backtest.
- **Etiqueta "ZERO_NOISE":** telemetria composta (AND dos filtros análogos) para
  medir se sinais "zero noise" têm hit-rate superior, antes de considerar adotar a
  filosofia de AND rígido do v8.2 (hoje o motor usa score ponderado).
- **Decomposição do `SignalCard.tsx`:** componente já grande; dividir em
  subcomponentes quando for mexer nele.
- **Policy RLS da `telegram_config`:** hoje só libera `service_role`; o backend usa
  a chave anon, então a persistência da config só funciona via env var no Render
  (não pela tabela). Baixa prioridade — env var já resolve.
- **Testar o branch ativo dos modificadores de classe** (absorção/persistência)
  antes de flipar `absorcao_classe_mode`/`fluxo_upgrade_mode`.

---

## Notas de ativação (Fase 4) — dos reviews

- **G22:** avaliar restringir o toque a `hc_min ≤ Low` se a telemetria mostrar
  falsos positivos (barra que vara a zona inteira e fecha acima ainda conta como
  "teste").
- **Família ESTRUTURA (cap 4):** satura com G3/G8/G19 co-disparando → pontos de
  G20/G22 podem ser marginais mesmo ativos; considerar no writeup de hit-rate.
- **G21** (`cmf<0` + preço subiu) tensiona com o redutor `RED_FLUXO` (mesma
  condição de cmf) — conferir efeito líquido ao ativar.
- **`cmf_z_periodo` > 28** estenderia o warm-up além do ADX e mudaria linhas do
  backtest (dropna) — manter 21 salvo recalibração deliberada.

---

## Precificação — próximos passos (análise repositórios B3, jul/2026)
- [ ] Métricas de performance no backtest (Sharpe/Sortino/drawdown) — ref. ffn
- [ ] IV robusta com fallback LetsBeRational — ref. vollib
- [ ] Curva de juros por vencimento (estrutura a termo) — ref. brasa/ANBIMA
- [ ] Superfície de volatilidade / skew — ref. ysaporito/QuantLib
- [ ] Integrar COTAHIST no fluxo de backtest para medir hit-rate PUCK (Fase 4)
- [ ] Implementar parser fixed-width real para `cotahist_service.carregar_cotahist_diario`
  (sem pacote PyPI viável; usar layout oficial B3 — ver docstring do módulo)
