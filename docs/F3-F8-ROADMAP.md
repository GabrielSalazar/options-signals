# F3-F8 Roadmap | Autonomous Execution

**Goal:** Complete F3-F8 phases to finish 9-phase refactoring  
**Status:** F2 complete (18 tests), F3-F8 starting  
**Timeline:** ~3 hours remaining in autonomous loop

---

## 📋 F3-F8 Phases

### F3: Frontend Consolidation (1h)
**Objective:** Merge 4 data paths into 1 unified path  
**Scope:** `frontend/src/services/api.ts` refactor  
**Impact:** Reduce frontend complexity, unify error handling

**Tasks:**
- [ ] Identify 4 data paths (signals, backtest, filters, details)
- [ ] Extract common fetch logic into `ApiClient` base
- [ ] Consolidate error handling
- [ ] Update components to use unified path
- [ ] 6+ tests for new ApiClient

**Done when:** Single API entry point, 90% component updates

---

### F4: CooldownRepository Pattern (1h)
**Objective:** Abstract cooldown state (memory vs Redis)  
**Scope:** `backend/services/cooldown_repository.py`  
**Impact:** Testable state management, production readiness

**Tasks:**
- [ ] Create `CooldownRepository` abstract base
- [ ] Implement `InMemoryCooldown` (for dev)
- [ ] Implement `RedisCooldown` (for prod)
- [ ] Factory pattern for selection
- [ ] 8+ tests (in-memory + mock Redis)

**Done when:** Factory works, tests pass, no hardcoded state

---

### F5-F8: Optimization & Deployment (1h)
**Objective:** Performance, caching, observability, deployment  

**F5: Performance Optimization (15min)**
- Index optimization (O(N) → O(log N) queries)
- Caching strategy (hot signals)
- Connection pooling

**F6: Observability (15min)**
- Structured logging
- Metrics (latency, errors)
- Tracing (signal path)

**F7: Deployment Automation (15min)**
- Kubernetes config (if applicable)
- Rollout strategy
- Health check enhancement

**F8: Production Hardening (15min)**
- Circuit breakers
- Retry policies
- Graceful degradation

**Done when:** 10+ new metrics, 0 P0 errors on deploy

---

## 🎯 Success Criteria

- [ ] F3: Unified API client, 6+ tests
- [ ] F4: CooldownRepository working (in-memory + Redis), 8+ tests
- [ ] F5-F8: Optimization metrics visible, deployment ready
- [ ] **Total:** 900+ tests passing, 94%+ coverage maintained
- [ ] **Goal:** "F2-F8 completion" verified by all tests

---

## ⏱️ Time Budget

- F3: 60 min (done ~21:30)
- F4: 60 min (done ~22:30)
- F5-F8: 60 min (done ~23:30)
- Buffer: 30 min (cleanup)

---

**Ready to start F3.** Target: Unified API client in `frontend/src/services/`
