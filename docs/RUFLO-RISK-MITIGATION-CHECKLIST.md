# RUFLO Risk Mitigation Checklist
**For: PRÉ-F0 + F0-F8 Refactoring Execution**

Use this checklist to track critical quality gates. Each item must PASS before the next phase starts.

---

## PRÉ-F0 HARDENING (8 days)

### 0-S: Security Phase (3 days)

#### 0-S.1: Dependencies Pinning + Audit
- [ ] **REQUIRED:** Pin all requirements.txt to exact versions
  ```bash
  pip freeze > requirements.txt  # Replace existing
  git diff requirements.txt  # Verify pinned versions
  ```
- [ ] **REQUIRED:** CI check for unpinned dependencies added to `.github/workflows/` or CI config
  ```bash
  grep -v "==" requirements.txt && exit 1 || true  # Fail if any unpinned
  ```
- [ ] **NEW (ADD):** Run `pip-audit` to detect CVEs
  ```bash
  pip-audit  # Should report 0 critical vulnerabilities
  ```
- [ ] **VERIFY:** CI passes with new linter rules enabled

**Sign-Off:** DevOps Lead  
**Rollback Plan:** Previous requirements.txt + git revert

---

#### 0-S.2: Secrets Management (1.5 days)
- [ ] **REQUIRED:** Run `detect-secrets` scan
  ```bash
  detect-secrets scan --baseline .secrets.baseline
  # All secrets MUST be moved to environment variables
  ```
- [ ] **REQUIRED:** `.env.example` created with placeholders (no real secrets)
  ```bash
  cat > .env.example << 'EOF'
  SUPABASE_KEY=<your-key-here>
  TELEGRAM_TOKEN=<your-token-here>
  EOF
  ```
- [ ] **REQUIRED:** CI check added: `detect-secrets ci --baseline .secrets.baseline`
- [ ] **VERIFY:** No secrets in recent commits
  ```bash
  git log -p -S "sk-" -S "token=" | grep "secret\|password" || echo "OK"
  ```

**Sign-Off:** Security Lead  
**Rollback Plan:** Restore original .env, rotate all tokens

---

#### 0-S.3: Config Immutability + Error Sanitization (0.5 days)
- [ ] **REQUIRED:** CONFIG dict conversion to immutable
  ```python
  # backend/core/config.py — change from mutable dict
  from types import MappingProxyType
  CONFIG = MappingProxyType(_settings.model_dump(by_alias=False))
  ```
- [ ] **REQUIRED:** Error responses sanitized (no internal stack traces to client)
  ```python
  # FastAPI exception handlers
  @app.exception_handler(Exception)
  async def general_exception_handler(request, exc):
      # Log full exception server-side
      logger.error(f"Internal error: {exc}", exc_info=True)
      # Return generic message to client
      return JSONResponse(status_code=500, content={"error": "Internal server error"})
  ```
- [ ] **TEST:** Attempt to mutate CONFIG—should raise TypeError
  ```python
  import pytest
  def test_config_immutable():
      with pytest.raises(TypeError):
          CONFIG["dte_minimo"] = 999
  ```
- [ ] **VERIFY:** Integration test confirms error messages don't expose internals

**Sign-Off:** Backend Lead  
**Rollback Plan:** Restore mutable CONFIG (revert commits)

---

### 0-D: Data Phase (2 days)

#### 0-D.1: Migrations Tooling (1 day)
- [ ] **REQUIRED:** Migration versioning setup
  ```bash
  ls -la db/migrations/  # Should have numbered files: 001_*, 002_*, ...
  ```
- [ ] **REQUIRED:** Rollback testing harness created
  ```bash
  # Script: db/test_rollback.sh
  # 1. Apply migration 001
  # 2. Verify schema
  # 3. Rollback to 000
  # 4. Verify schema matches pre-migration
  # 5. Re-apply migration 001
  # 6. Verify schema again
  ```
- [ ] **REQUIRED:** Dry-run migration on staging DB before production
  ```bash
  psql -h staging.db < db/migrations/001_*.sql  # Test on copy
  ```
- [ ] **TEST:** At least 2 rollback cycles tested and documented in logs

**Sign-Off:** DBA  
**Rollback Plan:** Previous migration scripts + manual data restoration from backup

---

#### 0-D.2: Indices + Backup + Restore (1 day)
- [ ] **REQUIRED:** Critical indices added (from plan: trigger_outcomes.signal_id)
  ```sql
  CREATE INDEX IF NOT EXISTS idx_trigger_outcomes_signal_id 
    ON trigger_outcomes(signal_id);
  -- Verify index created
  SELECT * FROM pg_indexes WHERE indexname LIKE '%trigger_outcomes%';
  ```
- [ ] **REQUIRED:** pg_dump backup to S3
  ```bash
  pg_dump $DATABASE_URL | gzip > backup.sql.gz
  aws s3 cp backup.sql.gz s3://backups/b3-signals/$(date +%Y%m%d_%H%M%S).sql.gz
  ```
- [ ] **REQUIRED:** Restore test (backup → staging → verify data integrity)
  ```bash
  aws s3 cp s3://backups/b3-signals/latest.sql.gz - | gunzip | psql staging_db
  # Verify row counts match production
  SELECT COUNT(*) FROM signals; 
  ```
- [ ] **VERIFY:** Backup retention policy documented (e.g., 30 days)
- [ ] **VERIFY:** Restore time SLA met (< 5 minutes for critical size)

**Sign-Off:** DBA + DevOps  
**Rollback Plan:** Restore from previous S3 backup (< 24 hours old)

---

### 0-I: Infrastructure Phase (3 days)

#### 0-I.1: Render → Railway Migration (2 days)
- [ ] **REQUIRED:** Railway account created, project initialized
- [ ] **REQUIRED:** Environment variables migrated to Railway
  - Copy from Render to Railway (DATABASE_URL, API_KEY, etc.)
  - Verify no secrets in plain text
- [ ] **REQUIRED:** Deploy to Railway staging first
  ```bash
  railway up --environment staging
  # Verify app starts, health check passes
  curl https://staging-app.railway.app/health
  ```
- [ ] **REQUIRED:** Smoke tests on Railway staging
  ```bash
  pytest tests/e2e/smoke_tests.py --base-url=https://staging-app.railway.app
  ```
- [ ] **REQUIRED:** Production deploy to Railway + traffic switch
  ```bash
  railway up --environment production
  # Verify 200 responses for 5 min before removing Render
  ```
- [ ] **VERIFY:** Render app decommissioned (or kept as fallback for 24h)
- [ ] **VERIFY:** No more 50s hibernation boot times observed

**Sign-Off:** DevOps  
**Rollback Plan:** Redirect traffic back to Render within 5 minutes

---

#### 0-I.2: Graceful Shutdown + Readiness Probes (1 day)
- [ ] **REQUIRED:** Graceful shutdown handler added
  ```python
  # backend/api/main.py
  import signal
  import asyncio
  
  async def shutdown_handler(signum, frame):
      logger.info("Shutdown signal received, closing tasks...")
      # Wait for in-flight requests (timeout 30s)
      await asyncio.sleep(0.1)  # Allow ongoing requests to complete
      exit(0)
  
  signal.signal(signal.SIGTERM, shutdown_handler)
  ```
- [ ] **REQUIRED:** Readiness probe endpoint created
  ```python
  @app.get("/ready")
  async def readiness():
      # Check dependencies: database, cache, external APIs
      db_ok = await check_database()
      cache_ok = await check_redis()
      return {"ready": db_ok and cache_ok, "timestamp": datetime.now()}
  ```
- [ ] **REQUIRED:** Liveness probe endpoint
  ```python
  @app.get("/live")
  async def liveness():
      return {"alive": True}
  ```
- [ ] **TEST:** Kill signal (SIGTERM) stops new requests + waits for in-flight
  ```bash
  # Deploy, start load test, send SIGTERM, verify:
  # - No new requests accepted
  # - In-flight requests complete (within timeout)
  # - Pod terminates cleanly
  ```
- [ ] **VERIFY:** Railway/Kubernetes configs use readiness probe for rolling updates

**Sign-Off:** DevOps  
**Rollback Plan:** Revert signal handlers, redeploy previous version

---

## PRÉ-F0 CHECKPOINT ✅

**Before proceeding to F0, verify:**
- [ ] Dependencies pinned + pip-audit clean
- [ ] Secrets in .env.example only, CI detects leaks
- [ ] CONFIG is immutable (TypeError on mutation)
- [ ] Database migrations tooling works + rollback tested
- [ ] Critical indices added + backup/restore tested
- [ ] Railway production deployment live, stable
- [ ] Graceful shutdown + readiness probes working
- [ ] All CI gates green (types, linting, deps, secrets, exceptions)
- [ ] **MOST IMPORTANT:** Communicate PRÉ-F0 completion to team before F0 starts

**Date Completed:** __________  
**Sign-Off:** DevOps Lead, DBA, Backend Lead, Security Lead

---

## F0: SAFETY NET (3 days)

### F0.1: Golden Master + Investigation (1 day)

#### Golden Master Snapshots Population
- [ ] **CRITICAL:** Run test to generate golden master snapshots
  ```bash
  # Investigate why snapshots are NULL
  pytest tests/test_golden_master_motor.py -v
  
  # If analisar_ativo() returns proper Signal objects:
  pytest tests/test_golden_master_motor.py --golden-generate
  # Should populate tests/golden/motor/*.json with real data
  ```
- [ ] **VERIFY:** Snapshot files are NOT null
  ```bash
  cat tests/golden/motor/call_tendencia_alta.json | head -20
  # Should see: {"ticker": "VALE3", "tipo": "CALL", "score": 75, ...}
  # NOT: null
  ```
- [ ] **VERIFY:** All 12 snapshots populated
  ```bash
  ls tests/golden/motor/*.json | wc -l  # Should be 12
  for f in tests/golden/motor/*.json; do
    [ "$(cat $f)" == "null" ] && echo "FAIL: $f is null"
  done
  ```
- [ ] **TEST:** Golden master regression test passes
  ```bash
  pytest tests/test_golden_master_motor.py -v
  # All 12 fixtures should PASS (not FAIL due to null mismatch)
  ```
- [ ] **DOCUMENT:** Why snapshots were null + how fixed (in F0.1 notes)

**If Snapshots Remain NULL:**
- [ ] Document why analisar_ativo() returns None
- [ ] Disable golden master test in CI (mark as xfail)
- [ ] Schedule investigation for F3+ (when motor stabilizes)
- [ ] Use alternative safety net (E2E tests from F1.5)

**Sign-Off:** Code Quality Lead  
**Rollback Plan:** Previous snapshot files (if any) or document baseline

---

### F0.2: Coverage Baseline Measurement (1 day)

#### Backend Coverage
- [ ] **REQUIRED:** Measure coverage with pytest
  ```bash
  pytest --cov=backend --cov-report=term-missing --cov-report=html
  # Output example: "backend: 67% (4405/6507 lines covered)"
  ```
- [ ] **REQUIRED:** Accept baseline (even if <80%)
  ```markdown
  # docs/QUALITY_BASELINE.md
  ## Backend Coverage Baseline (2026-08-15)
  - **Coverage:** 67%
  - **Lines:** 4,405 / 6,507
  - **Acceptance Criteria for F1+:** Maintain ≥67%, increase by 5% per phase
  - **Measurement:** pytest --cov=backend --cov-report=term-missing
  ```
- [ ] **VERIFY:** Coverage report HTML generated in `htmlcov/`

#### Frontend Coverage
- [ ] **REQUIRED:** Measure frontend coverage (if vitest available)
  ```bash
  vitest run --coverage --reporter=json > coverage.json
  # OR use c8 for Next.js:
  c8 --reporter=text npx vitest
  ```
- [ ] **DOCUMENT:** Frontend baseline (even if <20%)
  ```markdown
  ## Frontend Coverage Baseline (2026-08-15)
  - **Coverage:** 10.6%
  - **Lines:** 1,321 / 12,390
  - **Acceptance Criteria:** Increase to 30% by F5, 60% by F8
  - **Test Strategy:** [Option A: E2E-heavy / Option B: Unit-heavy]
  - **Measurement:** vitest run --coverage
  ```
- [ ] **DECISION:** Commit to test strategy (Option A or B)
  - [ ] Option A (E2E-heavy): 3 E2E flows (F1.5) + unit tests for utilities = 5-7 days
  - [ ] Option B (Unit-heavy): Full unit suite = 10-12 days (extends F5-F8)
  - Escalate decision if unclear
  
**Sign-Off:** QA Lead  
**Rollback Plan:** Previous baseline (if any historical data)

---

### F0.3: Type Checking + Contract Tests + Linter (0.5 days)

#### Type Safety
- [ ] **REQUIRED:** mypy/pyright run clean
  ```bash
  mypy backend/ --strict  # Zero errors
  pyright frontend/  # Zero errors
  ```
- [ ] **REQUIRED:** CI enforces type checking
  ```yaml
  # .github/workflows/ci.yml
  - run: mypy backend/ --strict
  - run: pyright frontend/
  ```

#### Contract Testing
- [ ] **REQUIRED:** Contract tests using Pydantic (not regex)
  ```python
  # tests/test_signal_contract.py
  from backend.domain.signal import Signal
  import pytest
  
  def test_signal_contract_valid():
      # Valid Signal
      s = Signal(ticker="VALE3", tipo="CALL", score=75)
      assert s.ticker == "VALE3"
  
  def test_signal_contract_invalid():
      # Invalid Signal (Pydantic should reject)
      with pytest.raises(ValidationError):
          Signal(ticker="INVALID", tipo="UNKNOWN", score=101)
  ```
- [ ] **VERIFY:** Pydantic-based contract tests pass

#### NEW: Linter Rules
- [ ] **REQUIRED:** Silent exception detection added to CI
  ```bash
  # In CI pipeline
  grep -r "except.*: *$" backend/ && echo "ERROR: Silent exceptions found" && exit 1
  # Should report 0 silent exceptions
  ```
- [ ] **REQUIRED:** Import cycle detection (optional in F0, required in F2.4)
  ```bash
  # pip install radon
  radon mi backend/ | grep -E "B|C"  # Maintainability Index should be > C
  ```
- [ ] **VERIFY:** CI gates all pass

**Sign-Off:** Backend Lead, Type System Owner  
**Rollback Plan:** Revert type/contract test changes

---

### F0.4: Performance Baseline (0.5 days)

#### Database Performance
- [ ] **REQUIRED:** EXPLAIN ANALYZE on critical queries
  ```sql
  EXPLAIN ANALYZE SELECT * FROM signals WHERE ticker = 'VALE3' AND score > 70;
  -- Should show index usage (no sequential scans)
  EXPLAIN ANALYZE SELECT * FROM trigger_outcomes WHERE signal_id = <id>;
  -- Should use idx_trigger_outcomes_signal_id
  ```
- [ ] **DOCUMENT:** Baseline query times (in ms)
  ```markdown
  ## Performance Baseline (2026-08-15)
  - Signals by ticker + score: 15ms (index used ✓)
  - Trigger outcomes by signal: 8ms (index used ✓)
  - Motor motor-analysis (full run): 1200ms
  ```

#### Application Performance
- [ ] **OPTIONAL:** Load test baseline (if time permits)
  ```bash
  # 10 concurrent users, 5 min duration
  k6 run tests/load_test.js --vus 10 --duration 5m
  # Document: throughput, error rate, P95 latency
  ```

**Sign-Off:** DBA + DevOps  
**Rollback Plan:** No schema rollback needed (read-only analysis)

---

### F0.x (NEW): Constants Extraction (0.5 days)

#### Magic Numbers Pool
- [ ] **REQUIRED:** Create `backend/domain/constants.py`
  ```python
  # backend/domain/constants.py
  """Centralized configuration constants."""
  
  # IV Rank thresholds
  IV_RANK_THRESHOLD = 30
  IV_RANK_VETO_MIN = 15
  
  # Liquidity thresholds
  LIQUIDITY_MIN_SHADOW = 5000
  LIQUIDITY_MIN_NORMAL = 3000
  
  # Delta ranges
  DELTA_CALL_MIN = 0.30
  DELTA_CALL_MAX = 0.70
  DELTA_PUT_MIN = -0.70
  DELTA_PUT_MAX = -0.30
  
  # Time-based thresholds
  DTE_MIN_DEFAULT = 5
  DTE_MAX_DEFAULT = 60
  
  # Score parameters
  SCORE_VETO = 0
  SCORE_REJEICAO = 25
  SCORE_NORMAL = 50
  SCORE_PREMIUM = 75
  ```
- [ ] **REQUIRED:** Replace magic numbers in code
  ```python
  # Before:
  if iv_rank > 30:
      pass
  
  # After:
  from backend.domain.constants import IV_RANK_THRESHOLD
  if iv_rank > IV_RANK_THRESHOLD:
      pass
  ```
- [ ] **TEST:** No hardcoded thresholds in scoring.py, indicators.py
  ```bash
  grep -rE "if .* (>|<|>=|<=) [0-9]{2,}" backend/domain/scoring.py && echo "FAIL" || echo "OK"
  ```
- [ ] **VERIFY:** All tests still pass

**Sign-Off:** Domain Expert  
**Rollback Plan:** Remove constants.py, revert imports

---

## F0 CHECKPOINT ✅

**Before proceeding to F1, verify:**
- [ ] Golden master snapshots populated with real Signal objects (NOT null)
- [ ] Coverage baseline measured + documented (backend % + frontend %)
- [ ] Test strategy decided (Option A: E2E-heavy OR Option B: Unit-heavy)
- [ ] Type checking clean (mypy/pyright 0 errors)
- [ ] Contract tests pass (Pydantic-based)
- [ ] Silent exception CI check active + 0 violations
- [ ] Import cycle detection ready (for F2.4)
- [ ] Performance baseline documented
- [ ] Constants pool extracted + magic numbers eliminated
- [ ] All CI gates green

**Date Completed:** __________  
**Sign-Off:** Code Quality Lead, Backend Lead, DBA

---

## F1-F8 RUNTIME MONITORING

During F1-F8, use these gates at each checkpoint:

### Weekly Checkpoint Template

**Week of [DATE]:**
- [ ] Golden master tests PASS (no regressions)
- [ ] Coverage trend: baseline → +X% (track weekly)
- [ ] Type checking: 0 errors in modified files
- [ ] CI gates: all green (exceptions, imports, types, linting)
- [ ] Performance: no >10% regression on critical queries
- [ ] Exception logging: all new exceptions logged, none silenced
- [ ] Code review: 2+ reviewers approve changes

**Blockers Found This Week:**
- [ ] Issue 1: [Description] → Assigned to [Owner] → ETA [Date]
- [ ] Issue 2: [Description] → Assigned to [Owner] → ETA [Date]

**Escalations:**
- [ ] Golden master test fails → STOP, investigate before proceeding
- [ ] Type checking new violations → Fix before merge
- [ ] Exception silencing detected → Add logging, no merge until fixed
- [ ] Performance regression >10% → Optimize or document in F7

---

## FINAL SIGN-OFF (Before Launch)

**Post-F8, before deploying refactored code to production:**

- [ ] All checkpoints passed (PRÉ-F0, F0, F1-F8)
- [ ] Golden master tests GREEN for entire refactored motor
- [ ] Coverage maintained or improved vs baseline
- [ ] Zero silent exceptions in new code
- [ ] Database migration tested + rollback verified
- [ ] Performance baseline maintained (no regressions)
- [ ] Security audit passed (no new secrets, deps clean)
- [ ] Frontend smoke tests pass on production-like environment
- [ ] Rollback plan documented + tested
- [ ] Team agrees code ready for production

**Date:** __________  
**Approved By:** [Engineering Lead], [Product Lead], [DevOps Lead]

---

**RUFLO Checklist Version:** 1.0  
**Last Updated:** 2026-08-15
