# Git Strategy — Refactoring Plano v3

**Propósito:** Definir branches, commits, e PR workflow para execução do refactoring de 9 fases (F0-F8)

**Escopo:** Integra ECC compliance + RUFLO recommendations

---

## 🌳 Branching Strategy

### Main Branch Protections
```
main
├─ Status checks required (CI, type-check, tests, linters)
├─ PR review required (1 approval)
├─ Dismiss stale PR approvals (yes)
└─ No force push allowed
```

### Feature Branch Naming

**Pattern:** `f<N>-<description>`

```
PRÉ-F0 Hardening:
├─ pref0-security (deps pinning, detect-secrets)
├─ pref0-database (migrations, indices, backup)
└─ pref0-infrastructure (Render→Railway, graceful shutdown)

F0 Golden Master:
├─ f0-golden-master (fixtures, snapshots)
├─ f0-constants-pool (magic numbers)
└─ f0-linter (silent exception detection)

F1 Typed Signals:
├─ f1-pydantic-model (Signal domain model + validators)
├─ f1-motor-adapter (Motor integration)
├─ f1-ts-generator (TypeScript auto-generation)
├─ f1-contract-tests (Pydantic-based validation)
└─ f1-e2e-tests (3 critical flows)

F2-F8 (standard pattern):
├─ f<N>-<primary-feature>
├─ f<N>-<secondary-feature>
└─ (as needed)
```

### Merging Strategy

**Local:**
```bash
git checkout f0-golden-master
git rebase main  # Keep linear history
git push origin f0-golden-master
```

**On GitHub:**
- Create PR → request review
- CI must pass
- Squash merge for F0 (single unit)
- Regular merge for F1+ (preserve commit history)

---

## 📝 Commit Message Format

**Template:**
```
<type>(<scope>): <description>

<body (optional)>

<footer (optional)>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

**Scopes:**
- `golden-master` — F0 golden master fixtures/snapshots
- `pydantic` — F1 Pydantic Signal model
- `core-engine` — F2 core_engine decomposition
- `types` — TypeScript auto-generation
- `frontend` — F5-F6 frontend refactoring
- `infra` — F0.x, PRÉ-F0 infrastructure

### Examples

**Commit 1: Pin dependencies**
```
ci(deps): pin requirements.txt via pip freeze

Implements PRÉ-F0.0-S step 1.
Adds pip-audit to CI pipeline for CVE scanning.

Closes #ISSUE_ID
```

**Commit 2: Golden master setup**
```
test(golden-master): add 12 OHLCV fixtures and snapshots

F0.1: Establish regression detection baseline
- 12 deterministic fixtures (BRL daily, weekly, spot)
- Snapshots for 3 indicators per fixture
- Zero motor signal emissions (expected for fixture data)

Test suite: tests/test_golden_master.py
```

**Commit 3: Pydantic Signal model**
```
feat(pydantic): introduce Signal domain model with validators

F1.1a: Typed signal contract between motor and API

- IVBlock, LiquidityBlock, GreeksBlock (Pydantic BaseModel)
- Custom validators for NaN→None, numpy type coercion
- Motor adapter updated to return Signal instances
- Regression: golden master snapshots still match

Test suite: tests/test_signal_model.py
```

**Commit 4: TypeScript generator**
```
feat(types): auto-generate TypeScript Signal types from Pydantic

F1.2a: Keep frontend types in sync with backend

- JSON Schema + Jinja2 template (scripts/generate_signal_types.py)
- CI: runs on every commit, fails if types drift
- Output: src/types/generated/signal.ts

Test suite: tests/test_ts_generation.py
```

---

## 🔄 Pull Request Workflow

### Before Creating PR

**Checklist:**
```bash
# 1. Sync with main
git fetch origin
git rebase origin/main

# 2. Run tests locally
pytest -v --cov=backend
npm test -- --coverage

# 3. Type-check frontend
npm run type-check  # or: tsc --noEmit

# 4. Review your own diff
git diff origin/main

# 5. Check for secrets
git diff origin/main | grep -E "password|token|secret|key"

# 6. Lint backend + frontend
black --check backend/
flake8 backend/
npm run lint

# 7. Build frontend
npm run build
```

**If ANY check fails:** Fix locally, test again, THEN push.

### Creating PR

**GitHub CLI:**
```bash
gh pr create --title "f0: golden master setup" \
  --body "$(cat <<'EOF'
## Description
Establish regression detection baseline with 12 fixtures.

## What's included
- 12 deterministic OHLCV fixtures (daily, weekly, spot)
- Snapshots for 3 indicators per fixture
- Golden master validation in CI

## Test plan
- [ ] Run `pytest tests/test_golden_master.py -v`
- [ ] Verify snapshots match expected (zero emissions for fixtures)
- [ ] Confirm CI passes (pytest + tsc + linters)

## Checklist
- [x] Tests pass locally
- [x] No secrets in diff
- [x] Type-check passes
- [x] Commits follow conventional format
EOF
)"
```

### PR Template (GitHub)

Create `.github/PULL_REQUEST_TEMPLATE.md`:
```markdown
## Tipo
- [ ] F0: Golden Master
- [ ] F1: Tipos
- [ ] F2: Decomposição Core
- [ ] F3: Roteadores
- [ ] F4: Estado Global
- [ ] F5: Frontend Dados
- [ ] F6: UI
- [ ] F7: Observabilidade
- [ ] F8: Higiene

## O que foi feito
Descrição breve (2-3 linhas).

## Teste
- [ ] Testes passam: `pytest -v --cov`
- [ ] Frontend builds: `npm run build`
- [ ] Tipos check: `tsc --noEmit`
- [ ] Golden master valida (F0+)
- [ ] Nenhuma regressão observada

## Changelog
- [ ] Documentação atualizada (se aplicável)
- [ ] CHANGELOG.md atualizado (se feature)
- [ ] Nenhum secret commitado
```

### PR Review Criteria

**Must pass before merge:**
1. ✅ All CI checks green (pytest, tsc, ESLint, Prettier)
2. ✅ Type-check passes
3. ✅ Tests pass (unit + integration)
4. ✅ Code review approved (1+ reviewer)
5. ✅ No merge conflicts
6. ✅ Branch up to date with main

**Merge strategy:**
- PRÉ-F0 + F0: Squash (single unit)
- F1+: Regular merge (preserve history for revert ability)

---

## 🔐 Commit Hooks (Pre-Commit)

### .git/hooks/pre-commit

Executar antes de cada commit:

```bash
#!/bin/bash
set -e

# 1. Verify no secrets
if git diff --cached | grep -E "password|token|secret|API_KEY|TELEGRAM"; then
  echo "❌ Secrets detected in staged changes"
  exit 1
fi

# 2. Type-check TypeScript
npm run type-check

# 3. Lint staged files
npm run lint -- --fix

# 4. Run tests (backend)
pytest tests/ -q

echo "✅ Pre-commit checks passed"
```

**Install:**
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📊 Commit History Example (F0-F1)

```
* a1b2c3d (main) Merge branch 'f1-e2e-tests'
|\
| * e4f5g6h (f1-e2e-tests) test(e2e): add 3 critical user flows
| * h7i8j9k test(e2e): configure Playwright + fixtures
| * k0l1m2n feat(e2e): E2E test framework setup
|/
* n3o4p5q Merge branch 'f1-pydantic-model'
|\
| * q6r7s8t (f1-pydantic-model) feat(pydantic): validators for NaN coercion
| * t9u0v1w feat(pydantic): motor adapter returns Signal instances
| * w2x3y4z feat(pydantic): introduce Signal domain model
|/
* z5a6b7c Merge branch 'f0-golden-master'
|\
| * c8d9e0f (f0-golden-master) ci(linter): add silent exception detection
| * f1g2h3i test(golden-master): 12 fixtures + snapshots
| * i4j5k6l ci(deps): pin requirements.txt
|/
* l7m8n9o Initial commit (baseline for refactoring)
```

---

## 🚨 Emergency Rollback

**If a merged commit breaks production:**

```bash
# Identify bad commit
git log --oneline | head -20

# Create rollback branch
git checkout -b revert/<date>-<reason>
git revert <bad-commit-hash>
git push origin revert/<date>-<reason>

# Create PR with title: "revert: <reason>"
gh pr create --title "revert: [URGENT] <reason>" ...
```

**Communicate:** Slack #engineering + post-mortem within 24h

---

## 📋 Checklist — Por Fase

### PRÉ-F0
- [ ] All commits on `pref0-*` branches
- [ ] CI passing (deps, secrets, types)
- [ ] Merge to main after review

### F0
- [ ] All commits on `f0-*` branches
- [ ] Golden master snapshots validated
- [ ] CI passing (golden master must pass)
- [ ] Squash merge to main

### F1-F8
- [ ] All commits on `f<N>-*` branches
- [ ] Tests pass for each commit
- [ ] Regular merge to main (preserve history)

---

**Status:** ✅ Operacional para refactoring v3  
**Vigente de:** 2026-08-15  
**Próxima revisão:** Após PRÉ-F0 (2026-08-23)

