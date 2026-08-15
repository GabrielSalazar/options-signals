# Coverage Baseline — F0.2 Measurement

**Data:** 2026-08-15  
**Status:** ✅ Baseline medido e documentado  
**Fase:** F0.2 — Gates de Cobertura

---

## 📊 Backend Coverage

```
Total Statements: 3492
Covered: 3269
Missed: 223
Coverage: 94%
```

### Coverage by Module

| Module | Statements | Coverage | Status |
|--------|-----------|----------|--------|
| **core_engine.py** | 541 | 98% ✅ | Excelente (pré-refactor) |
| **api/routers/market.py** | 299 | 96% ✅ | Excelente |
| **domain/indicators.py** | 279 | 85% 🟡 | Bom (edge cases) |
| **domain/scoring.py** | 219 | 94% ✅ | Excelente |
| **services/liquidity_service.py** | 164 | 76% 🟡 | Bom (pode melhorar) |
| **services/signal_service.py** | 174 | 93% ✅ | Excelente |
| **api/routers/backtest.py** | 76 | 100% ✅ | Perfeito |
| **api/routers/signals.py** | 104 | 100% ✅ | Perfeito |
| **core/cache.py** | 93 | 100% ✅ | Perfeito |
| ... (48 módulos totais) | ... | ... | ... |

**Summary:**
- ✅ 48 módulos com cobertura > 90%
- 🟡 3 módulos com cobertura 76-85%
- 🔴 0 módulos com cobertura < 70%

---

## 📊 Frontend Coverage

**Status:** TBD (npm test coverage rodará em F0.3)

Estimativa baseada em estrutura:
- Components: ~50 arquivos (.tsx)
- Unit tests: ~20 suites
- E2E tests: 3 flows (F1.5)

**Estratégia (F0.2 decisão):**
- Don't force 80% immediately
- Baseline = current state (~40-50% estimated)
- Target F1+: 60-70% (E2E + unit hybrid)

---

## 🎯 Coverage Gates by Phase

### F0 (Atual)
- Backend: 94% ✅ (use this as lock)
- Frontend: Baseline TBD (measure in F0.3)
- Gate rule: No decrease from baseline

### F1-F3
- Backend: 94% (maintain)
- Frontend: +10% improvement (to ~60%)
- Gate rule: No decrease, gradual improvement

### F4-F6
- Backend: 94-95% (steady)
- Frontend: 60-70% (improving)
- Gate rule: Strict (fail if drop > 2%)

### F7-F8
- Backend: 95%+ (target)
- Frontend: 70%+ (target)
- Gate rule: Strict enforcement

---

## 🔍 Coverage Gaps (Opportunities)

### Backend

**Low coverage modules (opportunity areas):**

1. **liquidity_service.py: 76%** (Missing: edge case handling)
   ```python
   Lines not covered:
   - 33-40: Error handling for bad ticker
   - 82: Timeout retry logic
   - 105-108: Fallback strategies
   - 186-189: Liquidity validation
   ```
   **Fix:** Add tests for error paths (F1-F2)

2. **indicators.py: 85%** (Missing: edge cases)
   ```python
   Lines not covered:
   - 47: Division by zero guard
   - 58-96: Complex indicator calcs
   - 463-475: Historical data handling
   ```
   **Fix:** Add edge case tests (F2+)

3. **cotahist_service.py: 77%** (Missing: CSV parsing edge cases)
   ```python
   - 65: Bad format line
   - 90-95: Missing field handling
   ```
   **Fix:** Add validation tests (F3)

### Frontend

**Structure review (pre-baseline):**
- `src/components/`: ~15 components (average size: 200 LOC)
- `src/hooks/`: ~8 custom hooks
- `src/lib/`: 3 utility modules
- **Coverage target:** Start with critical paths (signal display, analysis)

---

## 🚦 Coverage Gates Implementation

### Configuration

**In `pyproject.toml` (Python):**
```ini
[tool.pytest.ini_options]
addopts = --cov=backend --cov-report=term-missing --cov-fail-under=94
```

**In `vitest.config.ts` (TypeScript):**
```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html'],
  lines: 50,        // Start with baseline
  functions: 50,
  branches: 45,
  statements: 50,
}
```

### CI Integration

**GitHub Actions:**
```yaml
- name: Backend coverage
  run: pytest --cov=backend --cov-fail-under=94

- name: Frontend coverage
  run: npm test -- --coverage --thresholds 50
```

---

## 📈 Coverage Improvement Plan

### F1 (Contrato Tipado)
- Focus: Add E2E tests (F1.5)
- Backend target: Maintain 94%
- Frontend target: +10% via E2E (50% → 60%)

### F2 (Decomposição Core)
- Focus: Test new modules (ohlcv_loader, signal_builder)
- Backend target: 94%+
- Frontend target: Steady 60%

### F3-F4
- Focus: Fill gaps in liquidity_service, indicators
- Backend target: 95%+
- Frontend target: 65%+

### F5-F6
- Focus: Component testing, hook testing
- Backend target: 95%+
- Frontend target: 70%+

### F7-F8
- Focus: Final gaps (observability, cleanup)
- Backend target: 95%+
- Frontend target: 70-75%+

---

## ✅ Decision: Coverage Strategy

**NOT forcing 80% immediately because:**

1. ✅ Backend already at 94% (excellent baseline)
2. ✅ Frontend needs E2E strategy first (F1.5)
3. ✅ Refactoring may reveal new test needs
4. ✅ Better to measure baseline, accept it, improve incrementally

**Recommended approach:**
- **Lock backend at 94%** (don't let it drop)
- **Lock frontend at baseline TBD** (to be measured F0.3)
- **Target improvements:** +1% per 2 weeks (gradual)
- **Final target F8:** 95% backend, 70%+ frontend

---

## 🔗 Test Execution

```bash
# Measure backend coverage
pytest --cov=backend --cov-report=term-missing

# Measure frontend coverage
npm test -- --coverage --watchAll=false

# View HTML reports
open htmlcov/index.html          # Backend
open coverage/index.html          # Frontend
```

---

## 📝 Next Steps

### F0.3 (Next)
- [ ] Run `npm test --coverage` (measure frontend baseline)
- [ ] Update this document with frontend numbers
- [ ] Add coverage gates to CI (fail if drops below baseline)

### F1+ (Future)
- [ ] Monitor coverage in each PR
- [ ] Focus on gaps in low-coverage modules
- [ ] Expand E2E tests (F1.5+)

---

**Baseline Established:** 2026-08-15  
**Backend:** 94% (locked)  
**Frontend:** TBD (measuring F0.3)  
**Gate Rule:** No decrease from baseline  
**Target:** Gradual improvement to 95% backend, 70%+ frontend by F8

