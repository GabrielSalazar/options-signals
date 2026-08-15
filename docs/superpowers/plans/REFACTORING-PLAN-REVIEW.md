# Revisão do Plano de Refatoração — B3 Options Signals

**Data:** 2026-08-15  
**Status:** ⚠️ Revisão Crítica  
**Revisor:** Skill planning-and-task-breakdown + code-review agents

---

## Executive Summary

O plano original de 9 fases é **conceitualmente sólido**, mas tem **3 críticas** que precisam atenção antes de prosseguir:

1. **Fase 0 está travada (33% completo)** — Passo 2 e 3 têm bloqueadores não explícitos
2. **Estimativas são otimistas** — F1 (5 dias) depende de validadores Pydantic customizados não explorados
3. **Paralelização é subutilizada** — F3/F4 podem começar em paralelo com F1, não F2

**Recomendação:** Replan as próximas 2 semanas com tarefas menores + risk mitigation clara.

---

## DIAGNÓSTICO CRÍTICO

### Estado Atual de Fase 0

| Passo | Status | Bloqueador | Estimativa |
|-------|--------|-----------|-----------|
| Passo 1: Golden Master | ✅ 100% | — | 3 dias ✓ |
| Passo 2: Gates de Cobertura | 🟡 0% | Baseline unknown | 1-2 horas |
| Passo 3: Pin Deps + tsc | 🟡 0% | Requires tsc audit | 1-2 horas |

**Problema:** Passo 2 não pode começar sem medir cobertura atual. Se backend está ~45% e frontend ~35%, gate de 80%/60% **vai falhar imediatamente**. Solução: usar valor atual como baseline.

**Ação urgente:** Medir cobertura real hoje.

```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
npm run test -- --coverage
```

---

### Dependências Revisadas

**Atual (do plano):**
```
F0 → F1 → F2 → (F3, F4) → F6 → F7 → F8
     ↓
     F5 ──────→ F6
```

**Problema:** F3 (Roteadores Magros) depende de F2, mas não precisa. F3 pode começar assim que F1 types são gerados (F1 semana 2).

**Revisado (otimizado):**
```
F0 ✓
  ↓
F1 (types gerados)
  ├─→ F2 (core_engine decomposição)
  │     ├─→ F3 (roteadores) [início semana 2]
  │     ├─→ F4 (estado global) [início semana 2]
  │     └─→ F7 (observabilidade)
  │
  └─→ F5 (frontend fetcher com novos types)
      └─→ F6 (UI decomposição)
```

**Ganho:** F3 + F4 começam 3 dias mais cedo (semana 2 vs semana 3).

---

### Estimativas: O Que Mudou

#### Fase 1 (Contrato Tipado) — 5 dias → **6-7 dias**

**Por quê:**
- Pydantic **rejeita `NaN` e `numpy.float64` por default** (descoberta do golden master)
- Validators customizados precisam ser testados isoladamente
- Gerador TS automático é novo, sem precedente no projeto

**Novas subtarefas:**
```
F1.1: Escrever modelo Pydantic com validators customizados (2 dias)
F1.2: Build gerador TS automático e testar (1.5 dias)
F1.3: Integrar teste de contrato ao CI (1.5 dias)
```

**Mitigação:** Começar F1.1 assim que F0 Passo 1 validar (podem rodar em paralelo).

#### Fase 2 (Decomposição) — 5 dias → **5-6 dias** (realista)

**Justificativa:** Golden master já vale comportamento, risco de regressão é baixo. Estimativa OK se refactor é feito por módulo.

#### Fase 3 (Roteadores) — 3 dias → **2-3 dias**

**Justificativa:** Menos acoplado que pensado. Auto-imports resolvem-se com dependency injection simples.

#### Fase 4 (Estado Global) — 3 dias → **4-5 dias** ⚠️

**Por quê:** Redis cooldown tem estado distribuído complexo. Precisa de:
- Setup Redis local + CI (nova dependência)
- TTL correctness em 3 cenários (normal, expira, timeout)
- Teste de integração com Render Redis (staging)

**Mitigação:** Deploy flag `COOLDOWN_BACKEND=memory|redis` permite rollback 5 minutos.

#### Fase 5 (Frontend camada) — 4 dias → **3-4 dias**

**Justificativa:** SWR já está instalado, é principalmente remoção de código.

#### Fase 6 (UI + CSS) — 5 dias → **6-7 dias** ⚠️

**Por quê:** Lazy-load Plotly é novo padrão, testes para finança (GreeksCalculator) são complexos.

---

## TIMELINE REVISADA: Próximas 2 Semanas

### SEMANA 1 (Ago 15-19)

```
Thu 15  Fri 16  Seg 18  Ter 19  Qua 20  Qui 21  Sex 22
  ─────────────────────────────────────────────────
  
  F0.2/3    F0.2/3  F1.1    F1.1    F1.1    F1.2    F1.2
  (2h)      (2h)    (1d)    (1d)    (0.5d)  (1d)    (0.5d)
  
  [Checkpoint: F0 + F1.1 Pydantic pronto]
```

**Tarefas concretas:**

#### Task: F0.2 — Medir Cobertura Baseline (2h)
- [ ] Rodar pytest com `--cov=backend --cov-report=html`
- [ ] Rodar vitest com `--coverage` 
- [ ] Documentar % backend e frontend atuais
- [ ] Definir gate: "baseline-atual ou 60%?" (decisão humana)
- Aceitação: arquivo `docs/COVERAGE-BASELINE.md` criado

#### Task: F0.3 — Pin Python Deps + tsc no CI (2h)
- [ ] Rodar `pip freeze > requirements-frozen.txt`
- [ ] Validar que projeto instala com requirements-frozen
- [ ] Adicionar `tsc --noEmit` ao `.github/workflows/ci.yml`
- [ ] Testar CI localmente com `act`
- Aceitação: CI passa, `tsc --noEmit` roda e passa

#### Task: F1.1a — Modelo Pydantic Signal (1 dia)
- [ ] Criar `backend/domain/signal.py` com modelo raiz
- [ ] Adicionar blocos aninhados: `IVBlock`, `LiquidityBlock`, `GreeksBlock`
- [ ] Escrever validators para: `NaN → None`, `numpy.float64 → float`
- [ ] Teste unitário: 3 casos (sinal válido, NaN em delta, incompletude de bloco)
- Aceitação: `pytest tests/test_signal_model.py -v` passa

#### Task: F1.1b — Adaptar Motor para Retornar Signal (1 dia)
- [ ] Refatorar `core_engine._montar_sinal()` para retornar `Signal` tipado
- [ ] Atualizar `core_engine.analisar_ativo()` para usar novo retorno
- [ ] Validar contra golden master: snapshots devem ser idênticos
- [ ] Teste: `pytest tests/test_golden_master_motor.py -v`
- Aceitação: Golden master valida, zero regressão

#### Task: F1.2a — Gerador TS Automático (1 dia)
- [ ] Criar script `scripts/generate_signal_types.py`
- [ ] Usar `pydantic.json_schema()` para introspection
- [ ] Escrever template Jinja2 para tipos TS
- [ ] Teste: rodas script, tipos TS são válidos (`tsc --noEmit`)
- Aceitação: tipos gerados podem ser importados, sem erros

#### Task: F1.2b — Integrar Gerador ao CI (0.5d)
- [ ] Adicionar job ao `.github/workflows/ci.yml`: `python scripts/generate_signal_types.py`
- [ ] Fail se tipos gerados estão desatualizados (check git status)
- [ ] Documentar: "tipos são auto-gerados, não editar à mão"
- Aceitação: CI falha se backend/domain/signal.py muda sem regenerar tipos

---

### SEMANA 2 (Ago 22-26)

```
Seg 22  Ter 23  Qua 24  Qui 25  Sex 26  Seg 29  Ter 30
─────────────────────────────────────────────────────

F1.3    F2.1    F2.1    F2.2    F2.2    F3.1    F3.1
(0.5d)  (1d)    (1d)    (1d)    (1d)    (1d)    (0.5d)

F4.1 (paralelo)
(0.5d)

[Checkpoint: F2 50%, F3 pronto para iniciar]
```

**Tarefas:**

#### Task: F1.3 — Teste de Contrato (0.5d)
- [ ] Criar `tests/test_signal_contract.py`
- [ ] Validar: modelo Pydantic + SQL persistência + TS types alinhados
- [ ] Teste: 14 campos faltantes do TS são capturados como erro no CI
- Aceitação: teste falha até TS estar em sync com modelo

#### Task: F2.1 — Extração `ohlcv_loader` + `triggers_v1` (1d)
- [ ] Criar `backend/domain/ohlcv_loader.py` (carregamento OHLCV limpo)
- [ ] Criar `backend/domain/triggers_v1.py` (gatilhos técnicos isolados)
- [ ] Mover testes para `tests/domain/`
- [ ] Validar golden master: snapshots idênticos
- Aceitação: `core_engine.py` reduz 100+ linhas, testes isolados passam

#### Task: F2.2 — Extração `signal_builder` + Redução `core_engine` (1-2d)
- [ ] Criar `backend/domain/signal_builder.py` (montagem da estrutura final)
- [ ] Refatorar `core_engine.analisar_ativo()` para 60 linhas com early returns
- [ ] Eliminar `try/except Exception` global, usar exceções tipadas
- [ ] Testar: pytest, golden master, sem regressão
- Aceitação: `core_engine.py` agora ~280 linhas (era 959)

#### Task: F4.1 — Setup CooldownRepository (0.5d, paralelo)
- [ ] Criar interface `backend/repository/cooldown_repository.py`
- [ ] Implementar `InMemoryCooldownRepo` (testes)
- [ ] Implementar stub `RedisCooldownRepo` (production, para depois)
- [ ] Teste: repositório em memória funciona, redis stub pronto
- Aceitação: repositório abstraído, sem estado módulo-level

---

## MATRIZ DE RISCO REVISADA

| Risk | Fase | Severidade | Probabilidade | Mitigação | Status |
|------|------|-----------|---------------|-----------|--------|
| **Pydantic rejeita `NaN`** | F1 | 🔴 ALTA | 100% | Validators custom + golden master valida | 🟡 In Progress |
| **F0.2 Baseline reprova gates** | F0 | 🔴 ALTA | 60% | Use valor atual como baseline temporário | 🟡 This week |
| **Redis cooldown + estado distribuído** | F4 | 🟠 MÉDIA | 70% | Deploy flag rollback (5 min), teste em staging | 🟡 Planned |
| **TS gerador com tipos complexos** | F1 | 🟠 MÉDIA | 50% | Teste gerado types com `tsc --noEmit` | 🟡 This week |
| **F3 Roteadores com import circular** | F3 | 🟢 BAIXA | 30% | Teste de arquitetura com `ast` | ✅ Mitigation ready |
| **F6 Lazy-load Plotly quebra visuais** | F6 | 🟠 MÉDIA | 40% | Teste visual após lazy-load, snapshots | ⏸️ Future |

---

## DEPENDÊNCIAS CORRIGIDAS

### Dependência (Antes)
```
F0 (3d)
  ↓
F1 (5d)
  ↓
F2 (5d)
  ├→ F3 (3d)
  ├→ F4 (3d)
  └→ F7 (3d)

F5 (4d) paralelo com F2
  ↓
F6 (5d)

F8 (2d) final
```

**Problema:** F3/F4 esperam F2 inteiro (5 dias). Na verdade, precisam apenas de F1 types.

### Dependência (Depois) ✅ OTIMIZADA

```
F0.1: Golden Master ✅ (Ago 14)
F0.2: Cobertura (Ago 15-16)
F0.3: Pin deps (Ago 15-16)

F1: Types Pydantic (Ago 18-22)
├─→ F1.1a Modelo (Ago 18-19)
├─→ F1.1b Motor adapter (Ago 19-20)
├─→ F1.2a Gerador TS (Ago 21-22)
├─→ F1.2b CI (Ago 22)
└─→ F1.3 Contrato (Ago 22)

Paralelo com F1:
├─ F2: Core decomposição (Ago 22-26) [bloqueia F3, F4]
└─ F4.1: Repository setup (Ago 22) [pode começar cedo]

Após F1:
├─ F3: Roteadores (Ago 26+)
├─ F5: Frontend (Ago 26+)
└─ F4: Redis (Ago 26+)

Após F2/F5:
└─ F6: UI decomposição (Ago 26+)

Final:
├─ F7: Observabilidade (Ago 26+)
└─ F8: Higiene (Ago 26+)
```

**Ganho:** F3/F4 começam **3 dias mais cedo** (Ago 26 vs Ago 29).

---

## PRÓXIMAS 2 SEMANAS: PLANO EXECUTÁVEL

### WEEK 1 (Ago 15-22)

**Meta:** Fase 0 completa + Pydantic model pronto

| Dia | Task | Responsável | Duração | Verificação |
|-----|------|-------------|---------|-----------|
| **Ago 15 (Thu)** | F0.2: Medir cobertura | você | 2h | `docs/COVERAGE-BASELINE.md` existe |
| **Ago 16 (Fri)** | F0.3: Pin deps + tsc | você | 2h | CI passa com tsc |
| **Ago 18 (Mon)** | F1.1a: Pydantic model | você | 1d | `pytest tests/test_signal_model.py` passa |
| **Ago 19 (Tue)** | F1.1b: Motor adapter | você | 1d | Golden master valida |
| **Ago 20 (Wed)** | F1.1b (cont) | você | 0.5d | Motor retorna Signal tipado |
| **Ago 21 (Thu)** | F1.2a: Gerador TS | você | 1d | Tipos gerados, `tsc --noEmit` limpo |
| **Ago 22 (Fri)** | F1.2b + F1.3 | você | 1d | CI rodar gerador, teste de contrato pronto |

**Checkpoint após Week 1:**
- [ ] F0 100% completo
- [ ] F1 types gerados e no CI
- [ ] Golden master validando tudo
- [ ] Cobertura medida, gate definido
- [ ] Pronto para F2 início semana 2

### WEEK 2 (Ago 22-26)

**Meta:** F2 decomposição iniciada, F3/F4 desbloqueadas

| Dia | Task | Duração | Verificação |
|-----|------|---------|-----------|
| **Ago 22 (Fri)** | F2.1: ohlcv_loader + triggers_v1 | 1d | `core_engine.py` reduz 100 linhas |
| **Ago 23 (Mon)** | F2.2a: signal_builder | 1d | Builder extraído, testes isolados |
| **Ago 24 (Tue)** | F2.2b: Redução core_engine | 1d | ~280 linhas, golden master valida |
| **Ago 25 (Wed)** | F3.1: Roteadores (início) | 1d | `market.py` reduz 200+ linhas |
| **Ago 26 (Thu)** | F3.1 (cont) + F4.1: Repository | 0.5d | Abstração pronta |

**Checkpoint após Week 2:**
- [ ] F2 ~50% (decomposição core)
- [ ] F3 iniciada (roteadores mágros)
- [ ] F4.1 Repository setup
- [ ] Golden master continua validando
- [ ] Pronto para F5/F4 Redis semana 3

---

## MUDANÇAS vs PLANO ORIGINAL

| Aspecto | Antes | Depois | Motivo |
|--------|-------|--------|--------|
| **Estimativa F1** | 5d | 6-7d | Validators customizados + gerador TS são novos |
| **Estimativa F4** | 3d | 4-5d | Redis é complexo, precisa TTL + integração |
| **Estimativa F6** | 5d | 6-7d | Lazy-load Plotly + testes de finanças |
| **Início F3** | Ago 29 | Ago 26 | Não precisa de F2 inteira, só de F1 types |
| **Início F4** | Ago 29 | Ago 22 | Repository pattern é independente |
| **F0 completion** | N/A | Ago 22 | Bloqueadores identificados + removidos |
| **Cobertura baseline** | "gate 80%" | "medido + decisão humana" | Risk mitigation |

---

## VERIFICAÇÃO FINAL

Antes de começar Week 1, confirme:

- [ ] **F0.1 Golden Master** completamente funcional (12 fixtures, snapshots, teste de contrato)
- [ ] **Plano é aprovado** por você (pode mudar, mas explícito)
- [ ] **Semana 1 tarefas** são claras e mensuráveis
- [ ] **Risk mitigation** foi discutida (especialmente F0.2 cobertura baseline)
- [ ] **Código pronto para revisão** (não esperar F0/F1 inteira, revisar por commits)

---

## Recursos e Escalação

Se bloqueador aparecer:
- **Pydantic validators complexos:** Escale para specialist, ~2h pair programming
- **Gerador TS falha:** Alternativa: escrever tipos à mão 1× (1h), depois automatizar
- **Redis + TTL bugs:** Deploy com flag `COOLDOWN_BACKEND=memory` (5 min rollback)

---

**Próximo passo:** Você aprova este plano revisado? Se sim, começamos **TODAY** com F0.2 (medir cobertura baseline).

