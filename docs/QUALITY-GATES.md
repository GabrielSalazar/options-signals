# Quality Gates — Refactoring Plano v3

**Propósito:** Definir CI/CD checkpoints obrigatórios para garantir qualidade durante refactoring

**Integra:** ECC compliance + RUFLO recommendations + development-workflow.md

---

## 🚦 CI Pipeline Gates

### Pre-Commit (Local)

**Executar antes de `git commit`:**

```bash
# 1. Type-check TypeScript
npm run type-check  # tsc --noEmit

# 2. Lint + format
npm run lint       # ESLint
npm run format     # Prettier (check mode)
black backend/     # Python formatter
flake8 backend/    # Python linter

# 3. No secrets in diff
git diff --cached | grep -iE "password|token|secret|api_key|telegram"

# 4. Backend tests (quick subset)
pytest tests/unit -q --tb=short

# 5. Golden master regression (F0+)
pytest tests/test_golden_master.py -q
```

**Hook Installation:**
```bash
# .git/hooks/pre-commit
cp scripts/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### CI Pipeline (GitHub Actions)

**Trigger:** Every push to `f*` or `pref*` branches, and PRs

**Jobs:**

#### 1. Lint & Type-Check (5 min)
```yaml
- Backend linting (flake8, black)
- Frontend type-check (tsc --noEmit)
- Markdown linting
- YAML validation
```

**Fail on:**
- ESLint errors
- Type errors
- Black format violations
- `console.log()` in production code (scan for patterns)

#### 2. Security Scanning (3 min)
```yaml
- detect-secrets (no hardcoded keys)
- pip-audit (CVE scanning)
- npm audit (JS dependencies)
- Bandit (Python security issues)
```

**Fail on:**
- HIGH severity secrets detected
- Known CVEs (>=7.0 CVSS)

#### 3. Unit Tests (10 min)
```yaml
Backend:
├─ pytest tests/unit -v --cov=backend --cov-fail-under=65%
├─ Coverage report
└─ Golden master regression (F0+)

Frontend:
├─ npm test -- --coverage --watchAll=false
├─ Coverage report
└─ Type checking integrated
```

**Fail on:**
- Test failures
- Coverage drop below baseline (F0: current%, F1+: 70%+)
- Golden master snapshots changed unexpectedly

#### 4. Integration Tests (15 min)
```yaml
Backend:
├─ pytest tests/integration -v -k "not slow"
├─ Database migrations (dry-run)
└─ API contract validation (Pydantic schemas)

Frontend:
├─ npm run build
└─ Build artifact analysis (size, warnings)
```

**Fail on:**
- Integration test failures
- Build warnings (unless whitelisted)
- Migration reversibility check fails

#### 5. E2E Tests (20 min, F1+ only)
```yaml
- Playwright e2e tests
- 3 critical user flows
- Screenshots on failure
- Video artifacts
```

**Fail on:**
- E2E test timeouts or failures
- Critical user flow broken

#### 6. Golden Master Validation (F0+)
```yaml
- Run golden master suite
- Compare snapshots (must match exactly)
- Zero unexpected signal emissions
```

**Fail on:**
- Snapshot mismatch (visual regression)
- Unexpected signals in fixture data

---

## 📊 Coverage Gates by Phase

| Phase | Backend | Frontend | Rule |
|-------|---------|----------|------|
| **PRÉ-F0** | Current baseline | Current baseline | Measure only, no fail gate |
| **F0** | Current% (locked) | Current% (locked) | Golden master must pass |
| **F1-F3** | 70%+ | 40%+ | Gradual improvement |
| **F4-F6** | 75%+ | 50%+ | Steady progress |
| **F7-F8** | 80%+ | 60%+ | Target reached |

**Rationale:** Coverage grows as tests are added (TDD approach), not backfilled.

---

## 🔍 Code Quality Gates

### Pre-Merge Checklist

**All of these must PASS before merge:**

- [ ] **Linting:** `npm run lint` + `flake8 backend/`
- [ ] **Type-check:** `npm run type-check`
- [ ] **Tests:** `pytest` + `npm test`
- [ ] **Coverage:** At or above threshold for phase
- [ ] **Secrets:** Zero secrets in diff
- [ ] **Build:** `npm run build` succeeds
- [ ] **Golden master:** Snapshots match (F0+)
- [ ] **No regressions:** E2E pass (F1+)

### Per-File Quality Rules

#### Python Files (backend/)

**Max complexity per function:** 12 (McCabe)
```bash
flake8 --max-complexity 12 backend/
```

**Max lines per function:** 50
- Exception: `core_engine.py` during F2 (up to 100 lines OK during decomposition)
- Checked via: `scripts/check_function_length.py`

**Max file size:** 400 lines
- Exception: `core_engine.py` (up to 959 before F2)
- Checked via: `wc -l` + validation script

#### TypeScript Files (src/)

**Max lines per component:** 300
```bash
scripts/check_component_size.ts
```

**No forbidden patterns:**
- ❌ `console.log()` in production (ESLint rule)
- ❌ `any` types without `// @ts-expect-error <reason>` comment
- ❌ `!` non-null assertions (use `Optional<T>` instead)

**Type coverage:** 95%+
```bash
npm run type-coverage
```

---

## 🧪 Test Coverage Requirements

### Backend (pytest)

**Minimum by phase:**
- F0: Baseline (measure current)
- F1-F3: 70%
- F4+: 75%
- F8: 80%+

**Measurement:**
```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
```

**Coverage report:** `htmlcov/index.html`

### Frontend (Vitest)

**Minimum by phase:**
- F0: Baseline (measure current)
- F1-F3: 40%
- F4+: 50%
- F8: 60%+

**Measurement:**
```bash
npm test -- --coverage --watchAll=false
```

**Report:** `coverage/index.html`

---

## 🚀 Deployment Gates

### Pre-Deployment Checklist

**Production deployment requires:**

1. ✅ **PR merged to main**
2. ✅ **All CI jobs PASS** (lint, test, security, E2E)
3. ✅ **Deployment branch protection** (require PR review)
4. ✅ **Manual sign-off** from code owner
5. ✅ **Rollback plan documented** (if needed)

### Deployment Phases

**F0-F1:** Staging only (Render free)
- Deploy to staging for manual validation
- No production traffic

**F2+:** Production ready (Railway)
- Blue-green deployment strategy
- Health checks pass
- Rollback on failure

---

## 🔴 Critical Failure Points

**Any of these will BLOCK merge:**

| Issue | Severity | Recovery |
|-------|----------|----------|
| Type errors (tsc) | 🔴 CRITICAL | Fix types locally, re-push |
| Test failures | 🔴 CRITICAL | Fix implementation or test |
| Secret in diff | 🔴 CRITICAL | `git reset`, remove secret, re-commit |
| Coverage drop (F1+) | 🔴 CRITICAL | Add tests or revert change |
| Golden master mismatch (F0+) | 🔴 CRITICAL | Investigate regression, fix |
| Known CVE (>=7.0) | 🔴 CRITICAL | Update package, re-run scan |
| ESLint errors | 🟠 HIGH | Run `npm run lint --fix` |
| Format violations | 🟠 HIGH | Run `npm run format` |
| Silent exceptions (PRÉ-F0+) | 🟠 HIGH | Add logging or re-raise |

---

## 📋 Sample GitHub Actions Workflow

**`.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main, 'f*', 'pref*']
  pull_request:
    branches: [main]

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm install
      - run: npm run type-check
      - run: npm run lint
      - run: pip install -e .
      - run: flake8 backend/
      - run: black --check backend/

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install detect-secrets pip-audit
      - run: detect-secrets scan --baseline .secrets.baseline
      - run: pip-audit
      - run: npm audit --audit-level=high

  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .[dev]
      - run: pytest -v --cov=backend --cov-fail-under=65%
      - run: pytest tests/test_golden_master.py -v

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm test -- --coverage --watchAll=false
      - run: npm run build

  e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install
      - run: npm run e2e
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## ✅ Pre-Release Checklist

**Before tagging a release (end of phase):**

- [ ] All CI passing
- [ ] Coverage meets phase target
- [ ] Golden master validated
- [ ] E2E tests pass
- [ ] Changelog updated
- [ ] No known issues in backlog
- [ ] Documentation current
- [ ] Performance baseline captured (F7+)

---

**Status:** ✅ Operacional  
**Vigente de:** 2026-08-15  
**Próxima revisão:** Após PRÉ-F0

