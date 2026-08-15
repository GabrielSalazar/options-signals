# Roadmap Executivo — Próximas 2 Semanas

**Período:** 15 Ago - 26 Ago 2026  
**Status:** 🚀 Pronto para começar  
**Aprovação:** Depende de você

---

## TL;DR

✅ **F0 (Golden Master) está 33% pronto**
- Passo 1 ✅ Fixtures + snapshots criados
- Passo 2 🟡 Medir cobertura (TODAY)
- Passo 3 🟡 Pin deps + tsc (TODAY)

✅ **Plano revisado reduz timeline de 34d → ~24d úteis**
- Otimizou paralelização (F3/F4 começam cedo)
- Estimativas reajustadas com riscos mitigados
- Próximas 2 semanas: 8 tarefas concretas

✅ **5 ADRs aprovadas para guiar design**
- Gerador TS (JSON Schema + Jinja2)
- CooldownRepository (abstração)
- Arquitetura em camadas (zero ciclos)
- SWR fetcher (4 caminhos → 1)

---

## Próximas 2 Semanas em Cards

### SEMANA 1: Ago 15-22 (Alicerce)

```
┌─────────────────────────────────────────────────────┐
│  SEMANA 1: Rede de Proteção + Types Tipados        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Thu 15  F0.2: Medir cobertura (2h)                │
│          ├─ pytest --cov=backend                   │
│          ├─ npm run test --coverage                │
│          └─ docs/COVERAGE-BASELINE.md              │
│                                                     │
│  Fri 16  F0.3: Pin deps + tsc (2h)                 │
│          ├─ pip freeze > requirements.txt          │
│          ├─ Add tsc --noEmit ao CI                 │
│          └─ ✅ CI passa com tsc                     │
│                                                     │
│  Mon 18  F1.1a: Pydantic model (1d)                │
│          ├─ backend/domain/signal.py               │
│          ├─ IVBlock, LiquidityBlock, GreeksBlock   │
│          ├─ Validators para NaN, numpy types       │
│          └─ pytest tests/test_signal_model.py      │
│                                                     │
│  Tue 19  F1.1b: Motor adapter (1d)                 │
│          ├─ core_engine._montar_sinal() → Signal   │
│          ├─ Validar vs golden master               │
│          └─ ✅ Zero regressão                       │
│                                                     │
│  Wed 20  F1.1b (cont): Finish (0.5d)               │
│          └─ Motor retorna Signal tipado            │
│                                                     │
│  Thu 21  F1.2a: Gerador TS (1d)                    │
│          ├─ scripts/generate_signal_types.py       │
│          ├─ Jinja2 template                        │
│          └─ tsc --noEmit passa                     │
│                                                     │
│  Fri 22  F1.2b + F1.3 (1d)                         │
│          ├─ CI integration                         │
│          ├─ Teste de contrato                      │
│          └─ ✅ F0+F1 completo                       │
│                                                     │
│  CHECKPOINT WEEK 1 ✅                              │
│  ✓ F0 100% (rede proteção ativa)                   │
│  ✓ F1 100% (types gerados, CI validando)           │
│  ✓ Golden master operacional                       │
│  ✓ Cobertura medida, gate definido                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Deliverables Semana 1:**
- `docs/COVERAGE-BASELINE.md` — baseline de cobertura medida
- `backend/domain/signal.py` — Modelo Pydantic completo
- `scripts/generate_signal_types.py` — Gerador TS automático
- `src/types/generated/signal.ts` — Types sincronizados
- `.github/workflows/ci.yml` — tsc + gerador no CI
- `tests/test_signal_contract.py` — Validação de contrato

---

### SEMANA 2: Ago 22-26 (Decomposição + Preparação)

```
┌─────────────────────────────────────────────────────┐
│  SEMANA 2: Decomposição Core + Preparação F3/F4    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Fri 22  F1.3 (cont): Finalizar (0.5d)             │
│          └─ CI teste de contrato                   │
│                                                     │
│  Mon 23  F2.1: ohlcv_loader + triggers (1d)        │
│          ├─ backend/domain/ohlcv_loader.py         │
│          ├─ backend/domain/triggers_v1.py          │
│          ├─ Testes isolados (Layer 0 → Layer 1)    │
│          └─ core_engine.py reduz ~100 linhas       │
│                                                     │
│  Tue 24  F2.2a: signal_builder (1d)                │
│          ├─ backend/domain/signal_builder.py       │
│          ├─ Monta Signal final (Layer 2)            │
│          ├─ Builder pattern, testes isolados       │
│          └─ Golden master valida                   │
│                                                     │
│  Wed 25  F2.2b: Redução core_engine (1d)           │
│          ├─ Refatorar analisar_ativo() → 60 linhas │
│          ├─ Early returns, exceções tipadas        │
│          ├─ core_engine.py: 959 → ~280 linhas      │
│          └─ Teste de import cycles passa           │
│                                                     │
│  Thu 26  F3.1: Roteadores (início) (1d)            │
│  Paralelo: F4.1: CooldownRepository (0.5d)         │
│          ├─ backend/repository/cooldown.py         │
│          ├─ InMemoryCooldownRepo                   │
│          ├─ RedisCooldownRepo (stub)               │
│          ├─ Factory pattern                        │
│          └─ Testes isolados                        │
│                                                     │
│  CHECKPOINT WEEK 2 ✅                              │
│  ✓ F2 ~50% (decomposição core em progress)        │
│  ✓ F3 iniciada (roteadores magros)                │
│  ✓ F4.1 Repository pronto                         │
│  ✓ Zero import cycles                             │
│  ✓ Golden master continua validando               │
│  ✓ Pronto para F5/F6 próxima semana                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Deliverables Semana 2:**
- `backend/domain/ohlcv_loader.py` — Data loading isolado
- `backend/domain/triggers_v1.py` — Gatilhos técnicos extraídos
- `backend/domain/signal_builder.py` — Builder de sinais
- `backend/repository/cooldown.py` — Interface + 2 implementações
- `tests/test_import_cycles.py` — Validação de arquitetura
- `core_engine.py` reduzido para ~280 linhas

---

## Matriz de Dependências Atualizadas

```
SEMANA 1
┌──────────────────────────────────────────┐
│ F0.2 Medir cobertura (2h)                │ ← Bloqueador: sem isso não muda F0.3
└────────┬─────────────────────────────────┘
         │
┌────────▼─────────────────────────────────┐
│ F0.3 Pin deps + tsc (2h)                 │ ← Gate de qualidade
└────────┬─────────────────────────────────┘
         │
┌────────▼─────────────────────────────────┐
│ F1.1 Pydantic model + adapter (2d)       │ ← Golden master valida
├────┬────────────────────────┬────────────┤
│    │                        │            │
│    │ (paralelo OK)          │ (paralelo) │
│    ▼                        ▼            ▼
└─ F1.2a: Gerador TS (1d)   F1.2b: CI (0.5d)
   │                         │
   └─────────┬────────────────┘
             │
             ▼
       F1.3: Contrato (0.5d) ← CI falha se types desatualizados

SEMANA 2
           ┌────────────────────────────────┐
           │ F1 completo (types gerados)    │
           └────┬──────────────┬────────────┘
                │              │
                │ (paralelo OK)│
                ▼              ▼
            F2: Core      F3: Roteadores
         decomposição    (começar logo!)
            (1.5d)          (1d)
              │
              │ (paralelo com F3)
              ▼
          F4.1: CooldownRepository
            (0.5d, rápido)
```

---

## Métricas de Sucesso

### Fim da Semana 1:

- [ ] **F0 = 100%** (Rede de proteção ativa)
  - Passo 1: ✅ Golden master
  - Passo 2: ✅ Coverage baseline medida
  - Passo 3: ✅ Deps pinadas, tsc no CI

- [ ] **F1 = 100%** (Types gerados + CI)
  - Pydantic model: ✅ Validadores funcionando
  - TS generator: ✅ Scripts rodando, tipos limpos
  - CI: ✅ Gera automaticamente, falha se desatualizado
  - Contract test: ✅ Detecção de drift

- [ ] **Golden Master operacional**
  - ✅ 12 fixtures congelados
  - ✅ Snapshots não mudaram
  - ✅ Zero regressão visual

- [ ] **Cobertura medida**
  - Backend: X% (baseline)
  - Frontend: Y% (baseline)
  - Gate: "usar baseline ou 60%?" (humano decide)

### Fim da Semana 2:

- [ ] **F2 ~50%** (Decomposição iniciada)
  - ✅ ohlcv_loader extraído
  - ✅ triggers_v1 isolado
  - ✅ signal_builder montado
  - core_engine: 959 → ~500 linhas (em progress)

- [ ] **F3 iniciada** (Roteadores magros)
  - ✅ market.py começou refactor
  - ✅ Handlers reduzidos a ~20 linhas

- [ ] **F4.1 pronto** (CooldownRepository)
  - ✅ Interface abstrata
  - ✅ 2 implementações (memory + redis stub)
  - ✅ Testes isolados passam

- [ ] **Zero import cycles**
  - ✅ Teste de arquitetura no CI
  - ✅ Layers validadas (0 → 1 → 2 → 3)

- [ ] **Próxima semana desbloqueada**
  - ✅ F5 Frontend pode começar (types prontos)
  - ✅ F6 UI pode planejar (F5 bloqueador)
  - ✅ F7 Observabilidade pode começar (F2 necessário)

---

## Documentação Criada

| Doc | Propósito | Link |
|-----|-----------|------|
| **REFACTORING-PLAN-REVIEW.md** | Revisão completa, timeline, tarefas concretas | `/docs/superpowers/plans/REFACTORING-PLAN-REVIEW.md` |
| **ARCHITECTURE-DECISIONS.md** | 5 ADRs com decisões de design, riscos, mitigações | `/docs/superpowers/plans/ARCHITECTURE-DECISIONS.md` |
| **ROADMAP-NEXT-2-WEEKS.md** | Este documento — ação, checkpoints, métricas | `/docs/superpowers/plans/ROADMAP-NEXT-2-WEEKS.md` |

---

## Como Usar Este Plano

### Semana 1

**Day 1 (Thu 15):**
1. Leia `/REFACTORING-PLAN-REVIEW.md` seção "Week 1"
2. Rode `pytest --cov=backend` → documenta em `docs/COVERAGE-BASELINE.md`
3. Rode `npm run test --coverage` → documenta
4. Commit: `docs: cobertura baseline (backend X%, frontend Y%)`

**Days 2-5 (Fri-Tue):**
1. Comece `F1.1a: Pydantic model`
2. Use `ARCHITECTURE-DECISIONS.md` ADR-001 como referência
3. Teste conforme descrito em task
4. Commit por subtask (`feat: pydantic signal model`, `feat: validators`, `feat: ts generator`, etc.)

**Semana 1 Checkpoint:**
- [ ] F0 + F1 ambas 100%
- [ ] Golden master continua validando
- [ ] Nenhuma regressão em snapshots
- [ ] CI passando (tsc + tipos gerados)

### Semana 2

**Days 1-4 (Mon-Thu):**
1. F2.1: Extrair ohlcv_loader
2. F2.2: signal_builder
3. F3.1: Roteadores (paralelo)
4. F4.1: CooldownRepository (paralelo)

**Semana 2 Checkpoint:**
- [ ] F2 ~50% (decomposição em andamento)
- [ ] F3/F4 iniciadas
- [ ] Import cycles test passando
- [ ] Pronto para week 3

---

## Riscos Críticos (Watch List)

| Risk | When | Action |
|------|------|--------|
| **F0.2 Baseline reprova gates** | Week 1 Day 1 | Use valor atual como temporary baseline |
| **Pydantic rejeita NaN** | Week 1 Day 2 | Validators custom já planejados, OK |
| **TS gerador com tipos complexos** | Week 1 Day 4 | Teste com `tsc --noEmit` antes de CI |
| **Import cycles em F2** | Week 2 Day 3 | Teste de arquitetura roda antes cada commit |
| **Core engine ainda > 280 linhas** | Week 2 Day 4 | OK se < 350, refine week 3 |

---

## Próximas Ações (Hoje)

1. **Aprovar este plano** — Você concorda com timeline?
2. **Ler ADRs** — Qualquer pergunta sobre design?
3. **Começar F0.2** — Medir cobertura agora (2h)
4. **Criar arquivo rastreamento** — Log diário de progresso

---

## Links Rápidos

- 🔧 [Plano Completo](2026-08-14-refactoring-plan-complete.md)
- 📋 [Revisão Detalhada](REFACTORING-PLAN-REVIEW.md)
- 🏗️ [Decisões Arquiteturais](ARCHITECTURE-DECISIONS.md)
- ✅ [F0 Checkpoint](F0-CHECKPOINT.md)
- 📊 [F0 Progress](F0-PROGRESS.md)

---

**Status:** 🚀 Pronto para começar — Aprovação pendente  
**Criado:** 2026-08-15  
**Próxima revisão:** 2026-08-22 (Checkpoint Semana 1)

