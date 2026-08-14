# Roadmap Consolidado: Melhorias de Precificação B3

**Data:** 2026-07-03  
**Status:** Planos criados; execução pendente de aprovação

---

## Visão Geral

Análise de 35+ repositórios B3 identificou **5 melhorias de precificação** no projeto, estruturadas em prioridade e dependências. Todos os planos estão prontos em `docs/superpowers/plans/`.

| Prioridade | Item | Plano | Esforço | Status | Dependências |
|---|---|---|---|---|---|
| ⭐⭐⭐ | 1. Taxa dinâmica (SELIC/BCB) | [2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md](2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md#task-1-serviço-de-taxa-livre-de-risco-dinâmica-selic-via-bcb) | Baixo | Pronto | — |
| ⭐⭐⭐ | 2. Theta base 252 dias | [2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md](2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md#task-3-padronizar-theta-na-base-de-252-dias-úteis) | Baixo | Pronto | — |
| ⭐⭐⭐ | 3. Backtest com prêmios reais (COTAHIST) | [2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md](2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md#task-4-loader-de-prêmios-reais-de-opções-via-cotahist-rb3) | Médio | Pronto | — |
| ⭐⭐ | 4. IV robusta (LetsBeRational/vollib) | [2026-07-03-iv-robusta-letsberational.md](2026-07-03-iv-robusta-letsberational.md) | Médio | Pronto | Item 1 (taxa injetada) |
| ⭐ | 5. Superfície de volatilidade (SABR/skew) | [2026-07-03-superficie-volatilidade-skew.md](2026-07-03-superficie-volatilidade-skew.md) | Alto | Arquivo/Futuro | Itens 1–4 |

---

## Sequência Recomendada

### Fase 1: Precisão Fundacional (dias 1–3)

Execute nesta ordem:

1. **Item 1:** Taxa dinâmica (SELIC via `python-bcb`)  
   - Corrige IV e todas as gregas de uma vez  
   - Base para itens 2–5  
   - Plano: Task 1–2 (~2h)

2. **Item 2:** Theta em 252 dias  
   - Alinha convenção com T do projeto  
   - Isolado, sem dependências  
   - Plano: Task 3 (~30min)

3. **Item 3:** Backtest com COTAHIST  
   - Ativa a validação Fase 4 (hit-rate PUCK)  
   - Usa taxa dinâmica (item 1)  
   - Plano: Task 4–5 (~4h)

**Resultado esperado:** Precisão de IV/gregas melhorada, Theta correto, backtest validado contra prêmios reais.

### Fase 2: Robustez (dias 4–5, opcional imediato)

4. **Item 4:** IV robusta (LetsBeRational)  
   - Melhora estabilidade do scanner em condições extremas  
   - Fallback automático para Newton-Raphson  
   - Plano: Task 1–3 (~2h)

**Resultado esperado:** Nenhuma falha de convergência IV em opções OTM/perto de vencimento.

### Fase 3: Expansão (semana 2+, diferido)

5. **Item 5:** Superfície de volatilidade  
   - Alto esforço (semana inteira)  
   - Baixo retorno imediato (motor já validado sem superfície)  
   - Implementar quando Fase 4 feedback mostrar necessidade  
   - Plano: Task 1–3 (~40h)

**Resultado esperado:** Score sensível a smile/skew; detecção de arbitragens de volatilidade.

---

## Deps Novas

| Dep | Item | Versão mínima | Referência |
|---|---|---|---|
| `python-bcb` | 1 | 0.2.0+ | https://github.com/wilsonfreitas/python-bcb |
| `rb3` | 3 | 0.0.3+ | https://github.com/wilsonfreitas/rb3 |
| `vollib` | 4 | 0.5.0+ | https://github.com/vollib/vollib |
| `scipy` | — | Já presente | — |

Adicionar todas ao `requirements.txt` em uma PR consolidada após Fase 1, ou incrementalmente por item.

---

## Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| API `python-bcb` muda (série 432 descontinuada) | Fallback offline em `RISK_FREE_RATE_DEFAULT = 0.135`; teste sem rede |
| `rb3` coluna COTAHIST diferente da esperada | Ajustar nomes em `cotahist_service.py:filtrar_opcoes_do_ativo`; teste com mock |
| `vollib` não instala em Windows | Compilar de source ou usar WSL; fallback Newton-Raphson sempre disponível |
| Superfície de vol (item 5) nunca ativada | Arquivo sem risco; evitar escopo creep no roadmap principal |

---

## Métricas de Sucesso

**Item 1:** SELIC buscada do BCB no startup; taxa dinâmica usada em 100% de calls de `calculate_greeks`.

**Item 2:** Theta em testes bate com base 252; Theta diário = Theta anual / 252.

**Item 3:** Backtest aceita fonte COTAHIST; hit-rate PUCK reportado contra prêmios reais (não OHLCV do ativo).

**Item 4:** Nenhuma falha de convergência IV em opções OTM; vollib chamado em 100% dos casos.

**Item 5 (futuro):** Score PUCK detecta mispricing de smile; relatório mensal de desvios vs superfície.

---

## Execução

### Opção A: Subagent-Driven (recomendado para velocidade)

```bash
# Dispatchar subagent por task com revisão entre elas
# Paraleliza implementação, mantém qualidade
# Tempo esperado: Fase 1 = 2–3 dias úteis
```

### Opção B: Inline Esta Sessão (recomendado para aprendizado)

```bash
# Executar tasks sequencialmente aqui; checkpoint após cada task
# Você revisa a cada passo
# Tempo esperado: Fase 1 = 3–4 horas contínuas
```

**Qual prefere?**

---

## Links aos Planos

1. [Precificação Fundamentação (itens 1–3)](2026-07-03-precificacao-taxa-dinamica-e-backtest-real.md)
2. [IV Robusta (item 4)](2026-07-03-iv-robusta-letsberacional.md)
3. [Superfície de Vol (item 5)](2026-07-03-superficie-volatilidade-skew.md)

---

## Próximos Passos Após Execução

1. **Validação Fase 4:** Usar backtest com prêmios reais (item 3) para medir hit-rate PUCK final.
2. **Integração Telegram:** Alertar mudanças SELIC via webhook na produção (Render).
3. **Dashboard:** Exibir superfície de vol em tempo real quando item 5 for ativado.
4. **Curva ANBIMA (item 6 da análise anterior):** Taxa por vencimento, para opções de prazos muito diferentes.
