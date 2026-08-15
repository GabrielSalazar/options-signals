# Agent Orchestration — Refactoring Plano v3

**Propósito:** Mapear quais agentes Claude executam cada fase do refactoring

**Integra:** ECC agents.md + skills system

---

## 🤖 Agentes Disponíveis e Atribuições

### Fase PRÉ-F0: Hardening (8 dias)

#### PRÉ-F0.0-S: Segurança (3 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Pin deps + pip-audit setup | **devops** ou **build-error-resolver** | Dependency management, CI/CD | `requirements.txt` pinned, `.github/workflows/security.yml` |
| detect-secrets setup | **security-reviewer** | Secret scanning, compliance | CI rule added, `.secrets.baseline` |
| Config imutável + error sanitization | **backend-architect** | Design patterns, API security | `backend/config.py` refactored, error handlers updated |

#### PRÉ-F0.0-D: Dados (2 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Migrations tooling + versioning | **database-reliability-engineer** | Migrations, rollback strategy | Alembic configured, rollback tests passing |
| Índices + backup + restore test | **database-optimizer** | Schema optimization, DR | Index added, backup script, restore validation |

#### PRÉ-F0.0-I: Infraestrutura (3 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Render→Railway migration | **devops-automator** ou **finops** | Cloud migration, cost optimization | Railway account setup, deployment configured |
| Graceful shutdown + readiness | **backend-architect** | Container orchestration, reliability | Shutdown handler, health check endpoint |

---

### Fase F0: Rede de Proteção (3+ dias)

#### F0.1: Golden Master + Fixtures

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| 12 fixtures + snapshots | **tdd-guide** | Test-driven setup, test data | `tests/fixtures/`, golden master snapshots |
| Investigate NULL snapshots | **code-explorer** | Code path analysis, debugging | Root cause documented, strategy for population |
| Populate with real data | **mle-reviewer** (dados) ou **tdd-guide** | Data quality, test data generation | Populated snapshots, zero unexpected emissions |

#### F0.2: Coverage Baseline

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Medir coverage (pytest + vitest) | **tdd-guide** | Test coverage analysis | `docs/COVERAGE-BASELINE.md` with metrics |
| Define coverage strategy | **code-reviewer** | Code quality standards | `QUALITY-GATES.md` section updated |
| E2E testing strategy decision | **e2e-runner** | E2E framework, test planning | `docs/E2E-STRATEGY.md` (Option A vs B choice) |

#### F0.3: Dependencies + Type-Check

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| `pip freeze` + pip-audit CI | **devops-automator** | CI/CD, dependency scanning | CI job added, requirements.txt pinned |
| `tsc --noEmit` in CI | **typescript-reviewer** | TypeScript compilation, CI gates | CI job added, no type errors |
| Contract tests setup | **tdd-guide** | Contract testing patterns | `tests/test_signal_contract.py` |

#### F0.x: Constants Pool (0.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Extract magic numbers | **code-simplifier** ou **refactor-cleaner** | Code reduction, constant pooling | `backend/const.py`, replaced in core_engine + market |
| Add linter for silent exceptions | **security-reviewer** ou **build-error-resolver** | Linter rules, security gates | ESLint/Flake8 rule added to CI |

---

### Fase F1: Contrato Tipado (6-7 dias)

#### F1.1a: Pydantic Signal Model (1.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Design Signal model (IV, Liquidity, Greeks blocks) | **architect** ou **backend-architect** | Domain modeling, API contracts | `backend/domain/signal.py` with 3 blocks |
| Validators para NaN + numpy coercion | **python-reviewer** | Pydantic patterns, type safety | Custom validators, test suite |
| Teste de regressão vs golden master | **tdd-guide** | Regression testing | Tests pass, golden master still matches |

#### F1.1b: Motor Adapter (1 dia)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Adapt core_engine to return Signal | **backend-architect** | Refactoring, contract updates | `core_engine._montar_sinal()` returns Signal |
| Validate vs golden master | **tdd-guide** | Regression validation | Zero signal emissions mismatch |

#### F1.2: TypeScript Generator (1 dia)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Design JSON Schema + Jinja2 template | **architect** | API contract automation | `scripts/generate_signal_types.py` |
| CI integration (auto-generate + fail if stale) | **devops-automator** | CI/CD automation | GitHub Action added |
| Type generation validation | **typescript-reviewer** | TypeScript types | `src/types/generated/signal.ts` clean |

#### F1.3: Contract Testing (0.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Pydantic-based contract tests | **tdd-guide** | Contract validation patterns | `tests/test_signal_contract.py` |
| CI enforcement (fail if types drift) | **devops-automator** | CI gates | CI job added, blocks merge on mismatch |

#### F1.5: E2E Tests (1.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Setup Playwright framework | **e2e-runner** | E2E test infrastructure | `tests/e2e/`, fixtures |
| 3 critical flows (motor→API, API→frontend, full) | **e2e-runner** | Critical path testing | 3 .spec.ts files, all passing |
| CI integration + artifacts | **e2e-runner** | CI/CD, artifact uploads | GitHub Action added |

---

### Fase F2: Decomposição Core (5-6 dias)

#### F2.1: OHLCV Loader + Triggers (1 dia)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Extract ohlcv_loader | **code-simplifier** | Code extraction, modularity | `backend/domain/ohlcv_loader.py` |
| Extract triggers_v1 | **code-simplifier** | Code extraction, business logic | `backend/domain/triggers_v1.py` |
| Tests isolados (Layer 0→1) | **tdd-guide** | Unit testing, architecture layers | Tests passing, core_engine 959→~850 LOC |

#### F2.2: Signal Builder (1.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Builder pattern for Signal assembly | **architect** | Design patterns, composition | `backend/domain/signal_builder.py` |
| Golden master validation | **tdd-guide** | Regression testing | Snapshots match, zero emissions mismatch |

#### F2.3: CooldownRepository Abstraction (0.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Abstract Repository pattern (Factory) | **backend-architect** | Design patterns, SOLID | `backend/repository/cooldown.py` interface |
| InMemoryCooldownRepo implementation | **python-reviewer** | Clean code, test doubles | In-memory implementation, tests |

#### F2.4: Import Cycles Detection (1.5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Design layer validation test | **architect** | Architecture testing, constraints | `tests/test_import_cycles.py` |
| Lazy-load options.net to break cycles | **code-simplifier** ou **backend-architect** | Performance, dependency management | Lazy import added, cycles broken |
| CI enforcement (fail if cycles detected) | **devops-automator** | CI gates, linting | CI job added |

#### F2.5: Core Engine Reduction (1 dia)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Refactor analisar_ativo() | **code-simplifier** | Early returns, exception handling | 959→~280 LOC, no behavior change |
| Golden master regression test | **tdd-guide** | Regression validation | Snapshots match, zero signal diff |

---

### Fase F3: Roteadores Magros (2-3 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| market.py decomposição | **code-simplifier** | HTTP handlers, router cleanup | Handlers <50 LOC each |
| Reduzir para ~120 linhas | **refactor-cleaner** | Dead code, consolidation | 516→~120 LOC |

---

### Fase F4: Estado Global (4-5 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| RedisCooldownRepo implementation | **backend-architect** | Cache patterns, Redis | Redis adapter with TTL |
| CONFIG imutável validation | **security-reviewer** | Immutable config, security | `MappingProxyType` in use |
| Redis TTL + fallback strategy | **performance-optimizer** | Caching, resilience | Fallback to memory if Redis down |

---

### Fase F5: Frontend Data Layer (3-4 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| SWR fetcher composition | **frontend-developer** | Data fetching, React patterns | `src/lib/fetchers.ts` |
| Remover 4 caminhos de dados | **code-simplifier** | Code consolidation | Single source of truth |
| Remove console.log | **refactor-cleaner** | Code cleanup, linting | No console.log in production |

---

### Fase F6: UI Decomposição (6-7 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Lazy-load Plotly charts | **performance-optimizer** | Bundle optimization, lazy loading | Dynamic imports, size reduction |
| Break 8 large components | **code-simplifier** | Component decomposition | 8 files >400 LOC → modular structure |

---

### Fase F7: Observabilidade (3 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Prometheus metrics | **devops-automator** | Monitoring, metrics collection | `/metrics` endpoint, dashboard |
| Structured logging | **devops-automator** | JSON logging, observability | Logs formatados JSON, sem secrets |
| Alertas + thresholds | **devops-automator** | Alert rules, incident response | Alert rules defined |

---

### Fase F8: Higiene (2 dias)

| Tarefa | Agente | Competência | Deliverable |
|--------|--------|-------------|------------|
| Dead code removal | **refactor-cleaner** | Dead code detection, cleanup | Unused imports, functions removed |
| Data retention policy | **database-reliability-engineer** | Data governance, cleanup scripts | Retention policy documented + script |
| Schema cleanup | **database-optimizer** | Schema optimization | Unused columns removed |

---

## 📋 Completion Criteria by Phase

### PRÉ-F0
- ✅ All 3 hardening phases (0-S, 0-D, 0-I) complete
- ✅ No secrets in codebase
- ✅ Backup tested + working
- ✅ Railway migration complete
- ✅ Graceful shutdown + health checks active

**Checkpoint:** Deployment ready, zero critical gaps

### F0
- ✅ Golden master running (12 fixtures)
- ✅ Coverage baseline measured and documented
- ✅ All CI gates passing (lint, type, security, tests)
- ✅ E2E strategy decided (Option A vs B)
- ✅ Constants pool extracted (F0.x)

**Checkpoint:** Safety net in place, ready for F1

### F1
- ✅ Pydantic Signal model complete + validators work
- ✅ Motor adapter returns Signal instances
- ✅ TypeScript types auto-generated + synced
- ✅ Contract tests passing
- ✅ 3 E2E flows automated + passing

**Checkpoint:** Typed contract established, regressions detected

### F2
- ✅ core_engine.py: 959→~280 LOC
- ✅ ohlcv_loader, triggers_v1, signal_builder extracted
- ✅ Import cycles broken + validated in CI
- ✅ CooldownRepository abstracted
- ✅ Golden master still validates

**Checkpoint:** Core decomposed, architecture validated

### F3-F8
- ✅ market.py: 516→~120 LOC
- ✅ Redis state management working
- ✅ Frontend data layer unified (SWR)
- ✅ UI components decomposed
- ✅ Observability metrics captured
- ✅ Dead code removed, schema cleaned

**Checkpoint:** Full refactoring complete, all phases validated

---

## 🔄 Inter-Phase Dependencies

```
PRÉ-F0 (all 3 in parallel)
    ↓
F0 (must complete before F1)
    ↓
F1 (must complete before F2)
    ↓
F2 (parallel: F3 can start after F2.1)
├─ F3 (parallel with F2)
├─ F4 (serial: needs F2 complete)
│   ↓
├─ F5 (needs F1 types + F4 state)
├─ F6 (parallel with F5)
├─ F7 (needs F2 core + F5 data)
└─ F8 (last phase, can be parallel F6-F7)
```

---

## 🎯 Agent Rotation Policy

**Goal:** Avoid context overload, balance expertise

**Rules:**
- 1 agent per major task (F0.1, F1.1a, etc.)
- Can re-use agent if task is sequential continuation (F1.1a→F1.1b)
- Switch agent for independent subtasks (F0.1 and F0.x can be parallel with different agents)
- Use **tdd-guide** for all test-related work (consistency)
- Use **devops-automator** for all CI/CD work (consistency)

**Coordination:**
- Each agent reports back status + deliverables
- Handoff: Previous agent documents state in `docs/F<N>-CHECKPOINT.md`
- Next agent reads checkpoint before starting

---

**Status:** ✅ Operacional  
**Vigente de:** 2026-08-15  
**Próxima revisão:** Após cada fase

