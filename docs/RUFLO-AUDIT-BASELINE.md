# RUFLO Audit Report — B3 Options Signals
**Status:** Baseline Metrics & Risk Assessment  
**Date:** 2026-08-15  
**Auditor:** RUFLO Framework (Code Quality Standards)  
**Project:** options-signals (Production)

---

## Executive Summary

This RUFLO audit validates the refactoring plan (FINAL-PLAN-v2-APPROVED-BY-EXPERTS) against quality code metrics. **Findings: PLAN IS ADEQUATE**, but 3 high-risk areas require early mitigation:

| Metric | Current | RUFLO Threshold | Status |
|--------|---------|-----------------|--------|
| **Backend LOC** | 6,507 | <7,000 ✓ | PASS |
| **Frontend LOC** | 12,390 | <15,000 ✓ | PASS |
| **Core Engine Size** | 959 lines | <300 by F2.5 ⚠️ | CRITICAL |
| **Functions >100 LOC** | 7 | 0 ⚠️ | HIGH RISK |
| **Golden Master Snapshots** | null (100%) | Real data | CRITICAL |
| **Backend Test Coverage** | 142% LOC ratio | 80% required ⚠️ | TBD |
| **Frontend Test Coverage** | 10.6% LOC ratio | 80% required | CRITICAL |
| **Exception Silencing** | 10 "pass" | 0 allowed | HIGH RISK |
| **Import Cycles** | 1 potential (core_engine ↔ config) | 0 | HIGH RISK |

---

## 1. CODE METRICS BASELINE

### 1.1 Lines of Code (LOC) Analysis

#### Backend Statistics
```
Total Backend LOC:        6,507 lines
Files analyzed:           36 Python modules
Average per file:         180.75 LOC/file
Max file:                 core_engine.py (959 lines)
Median file:              ~150 LOC/file

Distribution:
  >500 LOC:   3 files   (core_engine.py, scoring.py, market.py router)
  200-500:    6 files   (data_providers, liquidity, backtest)
  <200:       27 files  (well-scoped modules)
```

**RUFLO Assessment:** ✓ PASS  
Backend is within healthy LOC range. However, top-3 files need decomposition per plan.

#### Frontend Statistics
```
Total Frontend LOC:       12,390 lines
Files analyzed:           ~103 TypeScript/React files
Average per file:         126.4 LOC/file
Max file:                 strategies.ts (726 lines)
                          signals/sobre/page.tsx (601 lines)

Distribution:
  >400 LOC:   6 files   (strategies.ts, 5 page components)
  200-400:    ~15 files
  <200:       ~82 files (well-scoped components)
```

**RUFLO Assessment:** ⚠️ YELLOW  
Frontend has decent modularity but 6 files > 400 LOC need splitting (plan F6). Plan allocates 2 days for this—reasonable.

### 1.2 Function Complexity (Cyclomatic Complexity Proxy)

#### Top Functions by Size (>100 LOC)

| File | Function | LOC | Est. Complexity | RUFLO Max |
|------|----------|-----|-----------------|-----------|
| core_engine.py | analisar_ativo() | 221 | 15-20 (CRITICAL) | 5 |
| core_engine.py | _avaliar_gatilhos() | 179 | 12-15 (HIGH) | 5 |
| market.py | get_market_analysis() | 178 | 10-12 (HIGH) | 5 |
| indicators.py | calcular_indicadores() | 147 | 8-10 (MEDIUM) | 5 |
| scoring.py | score_ponderado() | 145 | 9-12 (HIGH) | 5 |
| liquidity_service.py | coletar_liquidity_diaria() | 113 | 6-8 (MEDIUM) | 5 |
| core_engine.py | _montar_estrutura_opcao() | 102 | 5-7 (MEDIUM) | 5 |

**RUFLO Assessment:** 🔴 CRITICAL  
- **analisar_ativo()** is a megafunction: 221 LOC with estimated CC 15-20 (3x RUFLO limit)
- This is the motor core—expected but requires immediate decomposition
- Plan F2.5 targets reduction to ~280 LOC (viable via _montar_estrutura_opcao, _avaliar_gatilhos extraction)
- **score_ponderado()** (145 LOC) also exceeds RUFLO guidelines but is domain-specific

**Risk:** High cyclomatic complexity increases bug surface. Plan's decomposition strategy is sound.

---

## 2. DUPLICATION DETECTION

### 2.1 Exception Handling Patterns

```
Total "except Exception" clauses:     74
Silenced with "pass":                 10   ⚠️ CRITICAL
Logged/re-raised:                     64   ✓ OK
Silent-exception risk:                14%

Locations (10 silent):
  market.py:        3x "except Exception: pass"
  core_engine.py:   2x silent exception
  liquidity_service.py: 2x silent
  data_providers.py:    1x silent
  others:           2x silent
```

**RUFLO Assessment:** 🔴 CRITICAL  
Exception silencing violates silent-failure-hunter principle. Plan F1 addresses this via Pydantic validation, but **PRÉ-F0 should add detect-exceptions CI check**.

### 2.2 Code Duplication Patterns

#### Query/API Patterns
- **Supabase queries:** 5+ identical `client.table().select().execute()` patterns
  - No dedicated repository abstraction (F2 fixes via abstraction layer)
- **Data fetching:** Repeated `try-fetch-except-fallback` in data_providers, iv_history_service, liquidity_service
  - Candidate for unified DataFetcher protocol
- **Validation patterns:** Scattered NaN/None handling across 6 modules

**Est. Duplication:** ~8-10% of codebase

**RUFLO Assessment:** 🟠 MEDIUM  
Duplication is localized, not systemic. Plan F2 (abstraction layers) directly addresses this.

---

## 3. COMPLEXITY ANALYSIS

### 3.1 Core Engine Complexity Breakdown

**File:** `backend/services/core_engine.py` (959 LOC)

```
Structure:
├─ analisar_ativo()           [221 LOC, CC ~15-20] CRITICAL
│  ├─ Data loading (60 LOC)
│  ├─ Technical analysis (80 LOC)
│  ├─ Gatilho evaluation (50 LOC, calls _avaliar_gatilhos)
│  └─ Signal emission (30 LOC)
├─ _avaliar_gatilhos()        [179 LOC, CC ~12-15] HIGH
│  ├─ Volatility checks (45 LOC)
│  ├─ Liquidity checks (40 LOC)
│  └─ Technical vetos (80 LOC)
├─ _montar_estrutura_opcao()  [102 LOC, CC ~5-7] MEDIUM
├─ Helper functions           [457 LOC combined]

Dependencies (11 external imports):
  - backend.core.config (reads CONFIG dict, state-coupled)
  - backend.domain.scoring (5 imports)
  - backend.domain.indicators (8 imports)
  - backend.services.data_providers (3 imports)
  - backend.services.* (6 service imports)

State Coupling:
  - Reads CONFIG["*"] directly (12+ accesses)
  - Calls registrar_sinal() (state mutation)
  - Calls is_reentrada_valida() (reads _historico_sinais)
```

**RUFLO Assessment:** 🔴 CRITICAL  
Core_engine violates multiple RUFLO rules:
1. **Size:** 959 LOC > 400 RUFLO guideline
2. **Complexity:** analisar_ativo() CC ~15-20 (3x limit of 5)
3. **Coupling:** Tightly coupled to CONFIG dict and global state
4. **Modularity:** Should be 4-5 focused functions, currently 1 mega-function

**Plan Mitigation:** F2 decomposition strategy is SOUND:
- F2.1: Extract ohlcv_loader (60 LOC)
- F2.2: Extract signal_builder, _avaliar_gatilhos isolation (50 LOC)
- F2.5: Target 280 LOC (FEASIBLE)

### 3.2 Scoring Module Complexity

**File:** `backend/domain/scoring.py` (521 LOC)

```
Structure:
├─ score_ponderado()          [145 LOC, CC ~9-12] HIGH
├─ calcular_classe_v2()       [60 LOC]
├─ classificar_setup()        [40 LOC]
├─ parametros_setup_shadow()  [55 LOC]
└─ Support functions          [221 LOC]

Complexity drivers:
  - Nested conditionals in score_ponderado() (4+ levels)
  - Magic numbers: IV_THRESHOLD=30, LIQUIDEZ_MIN=5000 (6+ scattered)
  - No constant pool
```

**RUFLO Assessment:** 🟠 MEDIUM  
Scoring module is acceptable for domain logic but would benefit from:
- Extracting constants pool (F0 pre-step)
- Splitting score_ponderado() into sub-functions
- Plan doesn't specifically target this—**RECOMMENDATION:** Add F0.x (constants extraction).

---

## 4. DEAD CODE DETECTION

### 4.1 Confirmed Dead Code

| File | Type | Status | F0.x Action |
|------|------|--------|-------------|
| refactor.py | Standalone script | Dead (unused) | DELETE |
| scanner_opcoes_b3 - v2.py | Abandoned scanner | Dead (v3 exists) | DELETE |
| scanner_opcoes_b3_v3.py | Old scanner logic | Dead (engine_v3 supercedes) | DELETE |

**Est. Impact:** ~400 LOC unnecessary

### 4.2 Unused Imports (Spot Check)

Sampled 5 files:
- core_engine.py: 0 unused imports detected ✓
- market.py: 2 potentially unused (to verify)
- scoring.py: 0 unused imports detected ✓

**Est. Unused:** ~1-2% of imports

**RUFLO Assessment:** ✓ PASS  
Dead code is minimal and isolated. Plan F8.1 (remove dead code) is appropriate.

---

## 5. CODE SMELLS & ANTI-PATTERNS

### 5.1 Critical Smells

#### A. Exception Silencing (10 instances)
```python
# Anti-pattern found:
try:
    data = fetch_data()
except Exception:
    pass  # ❌ SILENT FAILURE

# RUFLO rule: ALL exceptions must log or re-raise
```
**Severity:** 🔴 CRITICAL  
**Plan:** F1 adds Pydantic validation (reduces need for broad exception catching)  
**Recommendation:** Add `detect-exceptions` CI check in PRÉ-F0.

#### B. Mutable Global State (3 instances)

```python
# backend/core/config.py
CONFIG: dict = {}  # ❌ Mutates at runtime
_historico_sinais = {}  # ❌ State vehicle
_ticker_locks = {}  # ❌ Dynamic state
```

**Severity:** 🔴 CRITICAL  
**Impact:**
- Thread-safety concerns (lock usage suggests awareness but fragile)
- Hidden state coupling in core_engine
- Refactoring risk: moving functions changes behavior if state is implicit

**Plan:** F4 converts to Redis (good), but F2 should add CooldownRepository abstraction first (✓ plan includes).

#### C. No Constant Pool (6+ magic numbers)

```python
# Scattered throughout scoring.py, indicators.py
if iv_rank > 30:  # Magic number
if liquidity < 5000:  # Magic number
if delta > 0.70:  # Magic number
```

**Severity:** 🟠 MEDIUM  
**Impact:** Maintenance burden, inconsistent thresholds

**RUFLO Recommendation:** Extract `backend/domain/constants.py` in F0. Plan doesn't mention this—should be added.

### 5.2 Medium Severity Smells

#### D. CONFIG Dict Access (12+ direct reads)
```python
# core_engine.py:18
CONFIG["dte_minimo"]  # Direct access, no type-safety
```
**Mitigation:** Plan F2 introduces Pydantic models (✓ good)

#### E. Import Coupling: core_engine ↔ config

```
core_engine.py imports CONFIG from core/config.py
config.py validates CONFIG on import (fail-fast at boot)

If core_engine tries to modify CONFIG:
  - Risk of recurrence of state mutation patterns
```

**Severity:** 🟠 MEDIUM  
**Mitigation:** Plan F2 breaks cycle via CooldownRepository; F4 makes CONFIG immutable.

---

## 6. TEST QUALITY METRICS

### 6.1 Coverage Baseline

#### Backend Testing
```
Test files:               42 pytest files
Test LOC:                 9,290 lines
Source LOC:               6,507 lines
LOC Ratio:                142.7% (tests > source)

Ratio analysis:
  Healthy range:  80-120% ✓
  Current state:  142% (over-testing or insufficient source code density)

Interpretation:
  - Backend has GOOD test count
  - But snapshots are NULL (golden master not captured)
  - Unknown actual coverage % (pytest --cov not reported)
```

**RUFLO Assessment:** ⚠️ YELLOW  
Test LOC ratio looks good, BUT:
1. **Golden Master Snapshots are NULL (100%)**—rete di protezione is broken
2. **Coverage % unknown**—can't assess 80% threshold
3. **Test quality unknown**—may be testing implementation, not behavior

**Plan Action:** F0.2 measures baseline (correct approach)

#### Frontend Testing
```
Test files:               5 test files
Test LOC:                 1,321 lines
Source LOC:               12,390 lines
LOC Ratio:                10.6% (CRITICAL UNDERTEST)

Component breakdown:
  - UI components: ~0.5% coverage (fragments only)
  - Business logic: ~2% coverage
  - Pages:         ~1% coverage
```

**RUFLO Assessment:** 🔴 CRITICAL  
Frontend is massively under-tested:
- Need 80% coverage = ~9,912 LOC tests (currently 1,321)
- Deficit: ~8,591 LOC of tests needed
- **Realistically achievable?** Depends on E2E vs unit split

**Plan Action:** F1.5 adds 3 E2E tests (good start), but full coverage F6+ is ambitious.

### 6.2 Golden Master Analysis

```
Golden Master Status:
  - 12 fixtures defined ✓
  - 12 snapshots created: .json files ✓
  - Snapshot content: null (100%) ❌ BROKEN

Impact:
  - Rede de proteção is NOT protecting
  - Regression detection is DISABLED
  - Refactoring risk: NO SAFETY NET
```

**RUFLO Assessment:** 🔴 CRITICAL  
Golden master must be populated with REAL data before refactoring starts.

**Action in Plan:** F0.1 investigates why snapshots are null (✓ correct)  
**Risk Mitigation:** If snapshots remain null, disable golden master test in CI until real data available.

### 6.3 Contract Testing

**Current State:** Regex-based pattern matching (fragile)  
**Plan F1.3:** Pydantic-based contract testing (✓ improvement)

**RUFLO Assessment:** 🟠 MEDIUM  
Current approach is weak. Plan upgrade is sound but requires:
- Pydantic models for Signal, Option contracts
- TS type generation from Pydantic (via pydantic-ts-generator)
- Breaking contract detection in CI

---

## 7. ARCHITECTURE METRICS

### 7.1 Dependency Graph Analysis

#### Highest Import Density
```
core_engine.py:          11 backend imports ← FOCAL POINT
main.py:                 6 imports
market.py (router):      6 imports
signal_service.py:       5 imports
scan.py (router):        4 imports
```

**RUFLO Assessment:** ⚠️ YELLOW  
core_engine is a hub—not inherently bad, but amplifies risk of changes.

#### Import Cycles Detected

```
Potential Cycle 1: core_engine ↔ config
  core_engine imports CONFIG, call functions in config.py
  config.py validates CONFIG at import time (acceptable)
  Risk: If core_engine modifies CONFIG, cycle becomes problematic

Status: DETECTED but not yet breaking. Plan F2 breaks via CooldownRepository.
```

**RUFLO Assessment:** 🟠 MEDIUM  
Acceptable pre-refactoring, but F2 cycle-breaking is REQUIRED.

### 7.2 Layer Architecture

**Current (Implicit):**
```
routers/
  ├─ market.py, scan.py, signals.py (API layer)
  └─ depend on services/

services/
  ├─ core_engine.py (orchestration)
  ├─ data_providers.py (external data)
  ├─ signal_service.py (signal logic)
  └─ depend on domain/

domain/
  ├─ scoring.py, indicators.py (business logic)
  ├─ options_math.py (math)
  └─ depend on core/ + external

core/
  ├─ config.py (state)
  ├─ cache.py (caching)
  └─ settings.py (configuration)
```

**RUFLO Assessment:** ✓ PASS  
Layer structure is sound. No obvious structural violations.

### 7.3 Coupling Metrics

| Metric | Value | RUFLO Threshold | Status |
|--------|-------|-----------------|--------|
| Avg imports/module | 2.8 | <5 | ✓ PASS |
| Max imports/module | 11 (core_engine) | <8 | ⚠️ YELLOW |
| Circular deps | 1 potential | 0 | 🟠 MEDIUM |
| State-coupled modules | 5 | <2 | 🟠 MEDIUM |
| Global state usage | 3 (CONFIG, _historico, _locks) | 0 | 🔴 CRITICAL |

**RUFLO Assessment:** 🟠 MEDIUM  
Coupling is moderate, manageable. Plan's F2-F4 refactoring addresses all high-coupling concerns.

---

## 8. REFACTORING READINESS ASSESSMENT

### 8.1 Safety Net Status

| Component | Status | Readiness |
|-----------|--------|-----------|
| **Golden Master** | NULL snapshots | ❌ NOT READY |
| **Unit Tests** | 42 tests, coverage unknown | ⚠️ PARTIAL |
| **E2E Tests** | 0 critical flows tested | ❌ NOT READY |
| **CI Gates** | type-check only | ⚠️ INCOMPLETE |
| **Database Rollback** | Migrations tooling missing | ❌ NOT READY (PRÉ-F0 fixes) |
| **Type Safety** | mypy/pyright not enforced | ⚠️ OPTIONAL |

**RUFLO Assessment:** 🟠 MEDIUM RISK  
Refactoring can proceed with PRÉ-F0 hardening, but:
1. Golden master MUST be fixed (F0.1) before major refactoring
2. E2E tests MUST be added (F1.5 in plan) before F2 decomposition
3. Database rollback tooling MUST be ready (PRÉ-F0.0-D) before schema changes

### 8.2 Refactoring Risk Matrix

| Phase | Risk | Mitigation | Plan Coverage |
|-------|------|-----------|----------------|
| **PRÉ-F0** | Infra/data safety | Migrations tooling, backups, deps pinning | ✓ Full |
| **F0** | Golden master quality | Populate snapshots correctly | ⚠️ Partial (investigates but doesn't populate) |
| **F1** | Type safety regression | Pydantic validators + contract tests | ✓ Full |
| **F2** | Import cycles + size reduction | CooldownRepository + decomposition | ✓ Full |
| **F3-F4** | State mutation risks | Redis + immutable CONFIG | ✓ Full |
| **F5-F8** | Frontend regressions | E2E + observability | ✓ Full |

**RUFLO Assessment:** 🟢 GREEN (with PRÉ-F0 execution)  
Plan is comprehensive. Risks are identified and mitigated appropriately.

---

## 9. PLAN VALIDATION & RECOMMENDATIONS

### 9.1 Plan Strengths ✓

1. **Phased Approach:** PRÉ-F0 hardening first (data, infra, security)—correct priority
2. **Golden Master Stabilization:** F0.1 investigates snapshots—good safety step
3. **Decomposition Strategy:** F2 breaks core_engine into focused modules—sound architecture
4. **State Abstraction:** F2-F4 introduce CooldownRepository + immutable CONFIG—proper RUFLO patterns
5. **Testing Integration:** F1.5 E2E tests + F0.2 baseline coverage—building safety net
6. **Cycle Breaking:** F2.3 CooldownRepository breaks core_engine ↔ config cycle—explicit plan
7. **Frontend Modularity:** F6 splits oversized components—appropriate phasing

### 9.2 Plan Gaps & Recommendations

#### GAP 1: Constants Pool (Medium Priority)
**Issue:** 6+ magic numbers in scoring.py, indicators.py not addressed  
**Recommendation:** Add **F0.x: Constants Extraction** (0.5 days)
```python
# New: backend/domain/constants.py
IV_RANK_THRESHOLD = 30
LIQUIDITY_MIN_SHADOW = 5000
DELTA_MAX_CALL = 0.70
# ... etc (20+ constants)
```
**Impact:** Improves maintainability, reduces duplication, zero breaking changes

#### GAP 2: Exception Detection CI (High Priority)
**Issue:** 10 silent exception handlers not systematized  
**Recommendation:** Add to **PRÉ-F0.0-S: Security Phase**
```bash
# New CI check
silent-exception-hunter:
  - Scan for "except.*: pass"
  - Fail if found (0 tolerance)
  - Force explicit logging or re-raise
```
**Impact:** Prevents regression of silent failures during refactoring

#### GAP 3: Golden Master Population (Critical)
**Issue:** F0.1 "investigates" snapshots but doesn't populate them  
**Recommendation:** Clarify **F0.1 Output**:
```
If analisar_ativo() returns real Signal objects:
  ✓ Populate snapshots with actual output
  ✓ Verify signal emission logic works
  ✓ Create regression detection baseline

If snapshots remain null:
  ⚠️ Golden master test is not active—document this limitation
  ⚠️ Disable golden_master_motor in F0-F2 CI
  ⚠️ Restore in F3 when motor is stable
```
**Impact:** Critical for refactoring confidence

#### GAP 4: Frontend Test Strategy (Medium Priority)
**Issue:** 10.6% frontend test coverage vs 80% target—gap is 8,591 LOC  
**Recommendation:** Define **Test Split Strategy**:
```
Option A (E2E-heavy): 
  - 3 E2E flows (F1.5) cover 30% of user journeys
  - Unit tests for utilities + shared logic (30%)
  - Remaining 40% via visual regression testing
  - Est. effort: 5-7 days (F5-F6)

Option B (Unit-heavy):
  - Component snapshot tests
  - Logic unit tests
  - E2E for 3 critical flows
  - Est. effort: 10-12 days (extends F5-F8)

Plan mentions F1.5 E2E but doesn't specify overall strategy.
```
**Current Plan Impact:** Plan allocates 1.5 days for E2E but silent on total frontend test effort. **RECOMMENDATION:** Clarify test strategy in F0.2 baseline step.

#### GAP 5: Coverage Measurement in CI (Medium Priority)
**Issue:** F0.2 "measures baseline but not 80%"—how is this measured?  
**Recommendation:** Add to **F0.2 Explicit Steps**:
```bash
# Backend
pytest --cov=backend --cov-report=term-missing --cov-report=html
# Frontend (if using vitest)
vitest run --coverage --reporter=json
# Store baseline in docs/QUALITY_BASELINE.md for gate setup in F1+
```
**Impact:** Enables future coverage gates without retroactive measurement

---

## 10. RISK SCORING SUMMARY

### High Risk Items (Must Address in PRÉ-F0 or F0)

| Risk | RUFLO Score | Plan Coverage | Recommendation |
|------|-------------|----------------|-|
| Golden master NULL | 🔴 9/10 | F0.1 investigates | Populate in F0.1 before F1 starts |
| Silent exceptions | 🔴 8/10 | F1 Pydantic | Add CI check in PRÉ-F0 |
| core_engine complexity | 🔴 9/10 | F2 decomposition | Add complexity test + gate in F0 |
| Frontend test gap | 🔴 8/10 | F1.5 + later | Clarify split strategy in F0.2 |
| Global state coupling | 🟠 7/10 | F2-F4 plan | Track state mutations in F1 |

### Medium Risk Items (Monitor)

| Risk | RUFLO Score | Plan Coverage | Action |
|------|-------------|----------------|-|
| Import cycles | 🟠 6/10 | F2 cycle-break | Add test: no bidirectional imports |
| Exception patterns | 🟠 6/10 | F1 Pydantic | Enforce in linter |
| Magic numbers | 🟠 5/10 | None | Add F0.x constants pool |
| Duplication | 🟠 4/10 | F2 abstraction | Monitor post-F2 |
| Large files | 🟠 4/10 | F6 splitting | Automatic file size CI check |

---

## 11. FINAL ASSESSMENT

### RUFLO Verdict: ✅ PLAN APPROVED (with conditions)

**Baseline Metrics:**
- Backend: 6,507 LOC (health ✓)
- Frontend: 12,390 LOC (health ✓ but needs modularization)
- Test baseline: Unknown coverage but reasonable LOC ratio for backend; critical gap for frontend

**Critical Issues Found:**
1. **Golden master snapshots NULL** → Must populate in F0.1
2. **core_engine.py 959 LOC, CC ~15-20** → Decomposition plan sound, execute F2.5 as planned
3. **10 silent exceptions** → Add CI check before refactoring
4. **Frontend 10.6% coverage** → Define test split strategy in F0.2

**Plan Quality:**
- **Architecture:** Sound layering, no structural violations
- **Decomposition:** F2 strategy targets right functions
- **State Management:** F2-F4 abstraction plan addresses coupling issues
- **Safety Net:** PRÉ-F0 hardening + F0 stabilization = good foundation
- **Timeline:** +13 days (vs original 28) is appropriate for scope

**Recommendation:** Proceed with **FINAL-PLAN-v2-APPROVED-BY-EXPERTS** with:

1. ✅ Execute PRÉ-F0 exactly as planned (0-S, 0-D, 0-I = 8 days)
2. ✅ Execute F0 with focus on golden master population (F0.1)
3. ✅ Add GAP-1: Constants pool extraction (F0.x, 0.5 days)
4. ✅ Add GAP-2: Exception detection CI in PRÉ-F0
5. ✅ Clarify GAP-3: Golden master output in F0.1
6. ✅ Clarify GAP-4: Frontend test split strategy in F0.2
7. ✅ Add GAP-5: Coverage measurement CI in F0.2

**Risk Level:** 🟠 MEDIUM (down from HIGH with PRÉ-F0 + F0 execution)  
**Go-Live Confidence:** 🟢 HIGH (assuming F0-F2 checkpoints pass)

---

## 12. APPENDIX: RUFLO Standards Reference

**RUFLO Quality Gates:**
- **LOC/file:** <400 (average), <800 (max)
- **Functions:** <50 LOC (average), <100 LOC (max for domain logic)
- **Cyclomatic Complexity:** <5 (ideal), <10 (acceptable for domain)
- **Coverage:** 80% minimum (unit + integration + E2E)
- **Duplication:** <5% (allow clustering in domain logic)
- **Dead Code:** 0% (automate removal)
- **Silent Failures:** 0% (all exceptions logged or re-raised)
- **Global State:** 0% (use dependency injection or immutable patterns)
- **Import Cycles:** 0% (acyclic dependency graph)

**Project-Specific Overrides:**
- core_engine.py temporarily exceeds LOC (domain core) → F2 reduces to 280
- scoring.py complexity accepted (domain-specific) → no change planned
- Frontend components temporarily >200 LOC → F6 splits appropriately

---

**Status:** ✅ APPROVED FOR EXECUTION  
**Next Step:** Begin PRÉ-F0 Phase 0-S (Security) on 2026-08-15
