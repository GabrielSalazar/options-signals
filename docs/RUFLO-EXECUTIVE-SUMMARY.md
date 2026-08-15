# RUFLO Audit — Executive Summary
**B3 Options Signals | Refactoring Plan v2 Assessment**

---

## ✅ Plan is APPROVED for Execution

FINAL-PLAN-v2-APPROVED-BY-EXPERTS is **architecturally sound** and adequately mitigates refactoring risk. Proceed with PRÉ-F0 hardening immediately.

---

## 🔴 CRITICAL BLOCKERS (Fix Before Refactoring Starts)

### 1. Golden Master Snapshots Are NULL (100%)
**Status:** Tests/golden/motor/*.json all contain `null` instead of real signal data

**Why This Matters:**  
The golden master is your regression safety net. Without real snapshots, you have **zero protection** against accidentally breaking the motor during F2-F4 decomposition.

**Fix Required (in F0.1):**
```bash
# Populate golden master with REAL signal data
pytest tests/test_golden_master_motor.py --golden-generate
# Verify snapshots contain Signal objects, not null
```

**Impact if Not Fixed:**  
- F2 refactoring proceeds blind
- Motor changes undetected until production
- Rollback cannot verify "same behavior as before"

**Timeline Cost:** 1-2 hours investigation (already in F0.1)

---

### 2. Silent Exception Handlers (10 instances)
**Status:** Found "except Exception: pass" in market.py (3x), core_engine (2x), liquidity_service (2x), others (3x)

**Why This Matters:**  
Silent exceptions hide bugs. During refactoring, a silent exception might mask a breaking change.

**Fix Required (in PRÉ-F0.0-S):**
```bash
# Add CI check that fails on silent exceptions
grep -r "except.*: pass$" backend/ && exit 1
# Document exceptions to be added in F0
```

**Impact if Not Fixed:**  
- Regressions during refactoring go undetected
- Production bugs from "swallowed" exceptions

**Timeline Cost:** 0.5 days (add linter rule)

---

### 3. core_engine.py Complexity (959 LOC, CC ~15-20)
**Status:** analisar_ativo() is 221 LOC with 15-20 cyclomatic complexity (3x RUFLO max)

**Why This Matters:**  
High complexity = high bug risk during refactoring. Small edits can unintentionally break behavior.

**Status of Fix:**  
✓ Plan F2.5 targets reduction to 280 LOC (good)  
✓ Decomposition strategy is sound  
⚠️ But must pass complexity test BEFORE F2 starts

**Recommended Action (add to F0.3):**
```python
# Test: ensure no function > 5 cyclomatic complexity post-refactor
# Add to CI gates for F3+
import radon.complexity
cc = radon.cc_visit('backend/services/core_engine.py')
assert all(m.complexity <= 5 for m in cc), "Motor functions too complex"
```

**Timeline Cost:** Included in F2 (already budgeted)

---

### 4. Frontend Test Gap (10.6% coverage)
**Status:** 1,321 LOC tests vs 12,390 LOC source = only 10.6% coverage

**Why This Matters:**  
F6 refactoring (splitting 6 oversized components) has minimal test safety. Changes can regress silently.

**Fix Required (clarify in F0.2):**
Define test split strategy:
- **Option A (Recommended):** E2E-heavy (F1.5 3 flows) + unit tests for 30% of logic + visual regression = viable in 5-7 days
- **Option B (Thorough):** Full unit test suite (10-12 days, extends F5-F8)

Plan mentions F1.5 E2E but doesn't specify total effort. **Clarify before F0 ends.**

**Timeline Cost:** 0.5 days clarity (F0.2) + 5-7 days test writing (F5-F6)

---

## 🟠 HIGH-RISK GAPS (Address in PRÉ-F0 or F0)

### 5. Import Cycle Detection Not Automated
**Status:** Manually detected potential cycle: core_engine ↔ config (but not breaking yet)

**Recommended:** Add to F0.3 or F2.4:
```bash
# CI check: no bidirectional imports
import networkx as nx
# Build dependency graph, verify DAG
```

**Timeline Cost:** Included in F2.4 (already planned)

---

### 6. Magic Numbers Not Pooled (6+ constants)
**Status:** Threshold values (IV=30, liquidity=5000, delta=0.70) scattered across scoring.py, indicators.py

**Recommended:** Add **F0.x: Constants Extraction** (0.5 days)
```python
# New: backend/domain/constants.py
IV_RANK_THRESHOLD = 30
LIQUIDITY_MIN_SHADOW = 5000
DELTA_CALL_MAX = 0.70
# ... consolidate 20+ magic numbers
```

**Impact:**  
- Improves maintainability
- Enables safe threshold tuning
- Reduces duplication

**Timeline Cost:** 0.5 days (fits in F0)

---

### 7. Coverage Measurement Not Defined
**Status:** Plan F0.2 says "measure baseline" but doesn't specify HOW or WHAT constitutes success

**Recommended:** Explicit CI step (add to F0.2):
```bash
# Backend baseline
pytest --cov=backend --cov-report=term-missing
# Store in docs/QUALITY_BASELINE.md

# Frontend baseline (if using vitest)
vitest run --coverage --reporter=json
# Store in docs/QUALITY_BASELINE_FRONTEND.md

# Document: "X% backend, Y% frontend baseline accepted as floor"
# Gates for F1+ will track improvement
```

**Timeline Cost:** 0.5 days (F0.2)

---

## 📊 RUFLO BASELINE METRICS (GOOD NEWS ✓)

| Metric | Current | Status |
|--------|---------|--------|
| Backend LOC | 6,507 | ✓ Healthy (target <7k) |
| Frontend LOC | 12,390 | ✓ Acceptable (target <15k) |
| File sizes | Avg 180 LOC backend, 126 LOC frontend | ✓ Good modularity |
| Dead code | ~400 LOC (refactor.py, scanner_v2/v3) | ✓ Minimal (F8.1 removes) |
| Duplication | ~8-10% (query patterns, data fetching) | ✓ Localized (F2 abstracts) |
| Exceptions | 64 logged/re-raised, 10 silent | ⚠️ Silent is problem (fix with CI check) |
| Global state | 3 instances (CONFIG, _historico, _locks) | ⚠️ Acceptable pre-refactor; F2-F4 fixes |
| Import cycles | 1 potential (core ↔ config) | ⚠️ Non-breaking; F2 breaks formally |

**Verdict:** Backend quality is **SOLID**. Frontend needs refactoring (planned F6). Both are within RUFLO guidelines with refactoring plan in place.

---

## 🎯 PRÉ-F0 + F0 CHECKLIST

Execute in order:

### PRÉ-F0 (8 days) — Foundation
- [ ] **0-S.1** (1d): Pin dependencies + pip-audit CI
- [ ] **0-S.2** (1.5d): Secrets management
- [ ] **0-S.3** (0.5d): Config immutable + error sanitization
  - **ADD:** Linter rule for "except ... : pass" detection
- [ ] **0-D.1** (1d): Migrations tooling (rollback testing)
- [ ] **0-D.2** (1d): Index critical columns + backup to S3 + restore test
- [ ] **0-I.1** (2d): Render → Railway (production stability)
- [ ] **0-I.2** (1d): Graceful shutdown + readiness probes

### F0 (3 days) — Safety Net
- [ ] **F0.1** (1d): Golden master investigation + POPULATE snapshots with real data
- [ ] **F0.2** (1d): Coverage baseline measurement + acceptance criteria documented
  - **ADD:** Explicit pytest commands + storage location (docs/QUALITY_BASELINE.md)
- [ ] **F0.3** (0.5d): Type checking + contract tests
  - **ADD:** Import cycle detection test
- [ ] **F0.4** (0.5d): Performance baseline (EXPLAIN ANALYZE)
- [ ] **F0.x (NEW)** (0.5d): Constants extraction pool (backend/domain/constants.py)

**Checkpoint Before F1 Starts:**
- ✅ Golden master populated with real Signal objects (not null)
- ✅ Coverage baseline measured and documented
- ✅ Silent exception CI check active (0 allowed)
- ✅ Database backups working + restore tested
- ✅ Backend running on Railway (no Render hibernation)
- ✅ All CI gates green (types, linting, deps, exceptions)

---

## ⏱️ TIMELINE IMPACT

```
PRÉ-F0:  8 days (mandatory hardening)
F0:      3 days (safety net + baselines)
F0.x:    0.5 days (constants pool) — ADD THIS
TOTAL:   11.5 days (vs 11 in plan + 0.5 new)

Then F1-F8:  28-30 days (as planned)

GRAND TOTAL: ~39-42 days (slight buffer for discovery, very reasonable)
```

---

## 🚦 GO/NO-GO DECISION

**RECOMMENDATION: GO** 🟢

**Conditions:**
1. ✅ Execute PRÉ-F0.0-S with linter rule for silent exceptions
2. ✅ Populate golden master snapshots in F0.1 with REAL data
3. ✅ Document coverage criteria in F0.2 (pytest commands + acceptance %)
4. ✅ Add F0.x constants extraction (0.5 days, minimal impact)
5. ✅ Add import cycle detection to F2.4

**Risk Level if Conditions Met:** 🟢 LOW  
**Confidence in Plan Execution:** 🟢 HIGH (90%+)

**If Conditions NOT Met:** 🔴 DO NOT PROCEED (too much blind refactoring risk)

---

## 📌 Next Actions (TODAY)

1. **Review this RUFLO audit** with the team (15 min)
2. **Populate golden master** — run F0.1 investigation to populate snapshots (1-2 hours)
3. **Add exception linter** — 1 grep rule in CI (30 min)
4. **Define test split** — decide Option A or B for frontend tests (30 min)
5. **Begin PRÉ-F0** — start with 0-S (pin deps + linter) tomorrow

---

**RUFLO Auditor Report**  
Status: ✅ APPROVED  
Date: 2026-08-15
