# Plano de Refatoração Completo — B3 Options Signals

**Data:** 2026-08-14  
**Status:** 📋 Planejamento  
**Prioridade:** Alta  
**Esforço total:** ~34 dias úteis (com paralelização)

---

## Sumário Executivo

O projeto está **funcional e em produção**, mas acumula acoplamento em três pontos críticos que bloqueiam a próxima escala:

1. **Contrato do sinal é um `dict` não tipado** replicado 4× sem validação (motor → persistência → SQL → TS). Drift comprovado: 14 campos gravados não existem no tipo TS.
2. **`core_engine.py` tem 959 linhas**, com orquestrador de 219 linhas envolvido por um `try/except Exception` único que engole qualquer falha.
3. **Frontend tem 4 caminhos de dados coexistindo** (axios, fetch+LRU, Supabase direto, route handlers), e 8 arquivos acima de 400 linhas com lógica embutida.

Este plano tem **9 fases**, desenhadas para que **nenhuma fase altere o comportamento de emissão de sinais** (golden master em F0 valida tudo). Ganho esperado: arquivo maior 959→280 linhas, função maior 219→60 linhas, drift de contrato passa a ser erro de compilação.

---

## Métricas Atuais (Medidas)

| Métrica | Backend | Frontend |
|---------|---------|----------|
| Arquivos de produção | 36 `.py` | 103 arquivos |
| LOC produção | 6.507 | 13.432 |
| Arquivos > 800 linhas | 1 (core_engine.py: 959) | 1 (globals.css: 1.042) |
| Arquivos > 400 linhas | 4 | 8 |
| Funções > 100 linhas | 5 | — |
| `except Exception` (silenciosos) | 74 (16 silenciam) | — |
| `console.*` em produção | — | 17 |
| Cobertura medida no CI | **não medida** | **não medida** |

---

## Fases de Refatoração

### FASE 0 — Rede de Proteção (3 dias)

**Objetivo:** Tornar toda mudança posterior verificável mecanicamente.

**O que faz:**
- Fixtures determinísticas de OHLCV (12 casos de borda)
- Golden master: testa que o motor não muda comportamento
- Teste de contrato: valida campos persistidos
- Pin de dependências Python (22 packages)
- Gates de cobertura no CI (80% backend, 60% frontend)
- `tsc --noEmit` no CI

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Cobertura medida | não | sim, gate 80% |
| Deps Python pinadas | 14/22 | 22/22 |
| Testes em quarentena | 1 arquivo + 1 teste | 0 |

**Riscos:** Gate reprova hoje (mitiga: usar valor atual como baseline)

---

### FASE 1 — Contrato Tipado do Sinal (5 dias)

**Depende de:** Fase 0  
**Bloqueia:** Fases 2, 5

**Objetivo:** Uma única fonte de verdade para a estrutura do sinal.

**O que faz:**
- Modelo Pydantic `Signal` com blocos aninhados (`IVBlock`, `LiquidityBlock`, `PuckBlock`, `GreeksBlock`)
- `core_engine._montar_sinal` retorna `Signal` tipado
- Gerador TS automático a partir do schema Pydantic
- Teste de validação de contrato (modelo × SQL × TS)
- CI falha se tipos gerados estão desatualizados

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Fontes de verdade | 4 (motor, persist, SQL, TS) | 1 (modelo Pydantic) |
| Campos faltantes no TS | 14 | 0 |
| Linhas manuais de mapeamento | 72 | ~3 |

**Riscos:** Pydantic rejeita `NaN`/`numpy.float64` (mitiga: validators customizados, golden master pega divergência)

---

### FASE 2 — Decomposição do `core_engine` (5 dias)

**Depende de:** Fases 0, 1  
**Bloqueia:** Fases 3, 4, 7

**Objetivo:** Quebrar 959 linhas em módulos coesos, cada um testável isoladamente.

**O que faz:**
- Extrai `ohlcv_loader`, `triggers_v1`, `triggers_v2`, `puck_filters`, `levels`, `option_structure`, `signal_builder`
- `core_engine` reduzido a orquestrador puro (~280 linhas)
- `analisar_ativo` quebrada em 7 etapas nomeadas com early returns (max ~60 linhas)
- Substitui `except Exception` global por exceções tipadas (`DadosInsuficientesError`, `ProviderIndisponivelError`, etc)
- Reduz escopo do lock de ticker de 140 linhas com I/O para ~5 linhas puras
- Divide `tests/test_core_engine.py` (1.195 linhas) em 5 arquivos

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Maior arquivo | 959 | ~280 |
| Maior função | 219 | ~60 |
| Funções > 100 linhas | 5 | 0 |
| Exceções inesperadas visíveis | não | sim (log + métrica) |

**Riscos:** Regressão silenciosa (mitiga: golden master em cada commit), import circular (mitiga: teste de arquitetura com `ast`)

---

### FASE 3 — Roteadores Magros (3 dias)

**Depende de:** Fase 2  
**Paralelizável com:** Fases 4, 6

**Objetivo:** Tirar cálculo financeiro de dentro de handlers HTTP.

**O que faz:**
- Extrai `market_analysis_service`, `fundamentals_service`, `indicators_service`
- Remove auto-import `_self` (sintoma de dependência não injetada)
- Divide `market.py` de 516 linhas para ~120
- Resolve a causa da quarentena de `test_market_analysis.py`

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| market.py LOC | 516 | ~120 |
| Maior handler | ~178 | ~20 |
| Auto-imports de módulo | 1 | 0 |
| `except: pass` em market | 5 | 0 |

---

### FASE 4 — Estado Global e Configuração (3 dias)

**Depende de:** Fase 2  
**Paralelizável com:** Fases 3, 6

**Objetivo:** Eliminar estado mutável de processo que impede scale-out.

**O que faz:**
- `CooldownRepository` com implementações: `InMemoryCooldownRepo` (testes) e `RedisCooldownRepo` (produção)
- Cooldown distribuído via Redis com TTL curto
- `CONFIG` imutável (`frozen=True`, `MappingProxyType`)
- Context manager `override_settings()` para testes e backtest
- Fixture autouse para resetar repositório entre testes

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Estado mutável módulo-level | 3 | 0 |
| Imports de símbolo privado | 2 | 0 |
| Cooldown correto com N instâncias | apenas N=1 | qualquer N |

**Riscos:** **Impacto direto no usuário** se cooldown quebra (mitiga: deploy com `COOLDOWN_BACKEND=memory`, validar em staging vs redis por 3 pregões)

---

### FASE 5 — Camada de Dados Única no Frontend (4 dias)

**Depende de:** Fase 1 (tipos gerados)  
**Bloqueia:** Fase 6  
**Paralelizável com:** Fase 2

**Objetivo:** Um caminho de dados, não quatro.

**O que faz:**
- Fetcher único tipado com `swr` (já instalado)
- Elimina `useCachedFetch` (119 linhas LRU caseiro)
- Usa SWR com `dedupingInterval` equivalente ao TTL atual
- Extrai `useSSE` e `useBackendWakeup` de `scanner/page.tsx`
- Remove 17 `console.*` de produção
- Adiciona `import 'server-only'` em `supabase-admin.ts`

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Caminhos de dados | 4 | 1 (+ SSE documentado) |
| Definições de BACKEND_URL | 2 | 1 |
| Cache caseiro | 119 linhas | 0 |
| `eslint-disable` | 6 | ≤2 |
| `console.*` | 17 | 0 |
| scanner/page.tsx LOC | 513 | ~200 |

---

### FASE 6 — Decomposição de UI e CSS (5 dias)

**Depende de:** Fase 5  
**Paralelizável com:** Fases 3, 4, 7

**Objetivo:** Nenhum componente/página acima de 250 linhas.

**Alvo de redução:**
| Arquivo | Atual | Alvo | Plano |
|---------|-------|------|-------|
| globals.css | 1.042 | ≤300 | dividir em tokens/base/components |
| strategies.ts | 726 | ≤200 | dividir por família |
| signals/sobre/page.tsx | 601 | ≤250 | conteúdo estático → MDX |
| alerts/page.tsx | 488 | ≤250 | extrair hooks e componentes |
| StrategiesBuilder.tsx | 413 | ≤250 | extrair useStrategyBuilder |
| analytics/page.tsx | 414 | ≤250 | lazy-load Plotly |
| estrategias/page.tsx | 400 | ≤250 | mesma decomposição |
| OptionAnalyzer.tsx | 388 | ≤250 | extrair cálculo em lib/ |
| SignalCard.tsx | 370 | ≤200 | já sinalizado no BACKLOG (4 sub-componentes) |

**O que faz:**
- Lazy-load Plotly com `next/dynamic` (maior dependência do bundle)
- Tokens de design em CSS custom properties
- Cobertura frontend sobe para 80% (14 arquivos → ~35)
- Testes para lógica financeira: `SignalCard`, `PayoffChart`, `GreeksCalculator`, etc.

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| Arquivos > 400 linhas | 8 | 0 |
| Arquivos > 250 linhas | ~14 | ≤3 |
| Cobertura frontend | ~40% est. | 80% |
| Arquivos de teste | 14 | ~35 |

---

### FASE 7 — Erros e Observabilidade (3 dias)

**Depende de:** Fase 2  
**Paralelizável com:** Fase 6

**Objetivo:** Nenhuma falha invisível.

**O que faz:**
- Zero `except Exception` genéricos (74 hoje → ≤15 justificados)
- Lint com `BLE` + `S110` (flake8-blind-except, try-except-pass)
- 6 métricas Prometheus: `signals_emitted_total`, `scan_duration_seconds`, `provider_errors_total`, `cache_hit_ratio`, `telegram_send_failures_total`, `motor_unexpected_errors_total`
- Logging estruturado em JSON (ticker, request_id, duration_ms)

**Antes/Depois:**
| Métrica | Antes | Depois |
|---------|-------|--------|
| `except Exception` genéricos | 74 | ≤15 |
| Blocos silenciosos | 16 | 0 |
| Métricas expostas | 0 | 6 |
| Regra de lint | não | sim |

---

### FASE 8 — Higiene e Documentação (2 dias)

**Depende de:** Todas

**Objetivo:** Fechar débito residual.

**O que faz:**
- Remove código morto: `scanner_opcoes_b3_v{2,3}.py`, `refactor.py`
- Zera baseline de ruff (remove `E501`, `E701`, `E702`, `E741` do ignore)
- Migrações reversíveis (adiciona `-- DOWN` comentado)
- `.env.example` completo
- Atualiza `docs/ESTADO_ATUAL.md` e `docs/ARQUITETURA_PRODUCAO.md`

---

## Timeline e Dependências

```
Semana 1         Semana 2          Semana 3         Semana 4         Semana 5
├─ F0 (3d) ─────┐
                ├─ F1 (5d) ──────┐
                                 ├─ F2 (5d) ────┐
                                                ├─ F3 (3d) ──┐
                                                ├─ F4 (3d) ──┤
                ├─ F5 (4d) ──────────┐              │
                                     ├─ F6 (5d) ────┘
                                                    ├─ F7 (3d) ─┐
                                                                ├─ F8 (2d)
```

| Fase | Dias | Caminho crítico | Paralelizável com |
|------|------|-----------------|------------------|
| F0 | 3 | sim | — |
| F1 | 5 | sim | — |
| F2 | 5 | sim | F5 |
| F3 | 3 | não | F4, F6 |
| F4 | 3 | não | F3, F6 |
| F5 | 4 | não | F2 |
| F6 | 5 | não | F3, F4 |
| F7 | 3 | não | F6 |
| F8 | 2 | não | — |

**Caminho crítico:** F0 → F1 → F2 → F3/F4 → F7 → F8 = **24 dias úteis**  
**Total sequencial:** 33 dias · **Com paralelização:** ~28 dias · **Com 2 devs:** ~19 dias

---

## Matriz de Priorização

| Fase | Item | Impacto | Urgência | Score | Ordem |
|------|------|---------|----------|-------|-------|
| F0 | Rede de proteção | Alto | Alta | 9 | 1 |
| F1 | Contrato tipado | Alto | Alta | 9 | 2 |
| F2 | Decomposição motor | Alto | Média | 7 | 3 |
| F3 | Roteadores magros | Médio | Média | 6 | 4 |
| F4 | Estado global | Alto | Baixa* | 6 | 5 |
| F5 | Dados frontend único | Médio | Média | 6 | 6 |
| F6 | UI/CSS | Médio | Baixa | 4 | 7 |
| F7 | Erros/observabilidade | Médio | Média | 5 | 8 |
| F8 | Higiene | Baixo | Baixa | 2 | 9 |

\* Urgência sobe para Alta no dia do primeiro scale-out (2+ workers/instâncias)

---

## Plano de Rollback

**Princípios:**
1. Uma fase = uma branch = um PR squash → revertível com `git revert`
2. Migrações apenas aditivas (nunca dropar/renomear coluna)
3. Cada migração tem `-- DOWN` comentado
4. Flags de config para mudanças de comportamento (ex: `COOLDOWN_BACKEND=memory` → `redis`)
5. Janela de validação: 3 pregões em produção antes da próxima fase

**Gatilhos de rollback imediato:**
- Scan completo retorna 0 sinais em pregão normal
- Taxa de erro > 5%
- Alerta Telegram duplicado
- Divergência no golden master
- Tempo do scan > 150% do baseline

---

## Métricas de Sucesso Globais

| Métrica | Baseline | Alvo | Fase |
|---------|----------|------|------|
| Maior arquivo Python | 959 | ≤400 | F2 |
| Maior arquivo TS/TSX | 726 | ≤250 | F6 |
| Maior arquivo CSS | 1.042 | ≤300 | F6 |
| Maior função Python | 219 | ≤60 | F2 |
| Arquivos > 400 linhas | 12 | 0 | F2, F6 |
| Fontes de verdade (contrato) | 4 | 1 | F1 |
| Campos com drift | 14 | 0 | F1 |
| Caminhos de dados frontend | 4 | 1 | F5 |
| `except Exception` genéricos | 74 | ≤15 | F7 |
| `except` silenciosos | 16 | 0 | F7 |
| `console.*` em produção | 17 | 0 | F5 |
| Cobertura backend | ❌ não medida | ✅ 80% com gate | F0 |
| Cobertura frontend | ❌ não medida | ✅ 80% com gate | F0, F6 |
| Regressões de sinal | — | **0** | todas |

---

## Recomendação de Início

**Comece por Fase 0, passo 1-2 (1,5 dia):**
1. Fixtures determinísticas de OHLCV (12 casos)
2. Golden master que compara sinal inteiro contra JSON congelado

Isso transforma todas as ~30 jornadas seguintes de "esperança" em "verificação mecanizada".

**Antes disso (15 minutos):**
- Pinar `requirements.txt` (build não é reprodutível hoje)
- Adicionar `tsc --noEmit` ao CI

---

## Tracking

- [ ] F0 — Rede de proteção
- [ ] F1 — Contrato tipado
- [ ] F2 — Decomposição do core_engine
- [ ] F3 — Roteadores magros
- [ ] F4 — Estado global
- [ ] F5 — Camada de dados frontend
- [ ] F6 — UI e CSS
- [ ] F7 — Erros e observabilidade
- [ ] F8 — Higiene e documentação

**Status:** 📋 Planejamento → 🚀 Implementação (Fase 0)
