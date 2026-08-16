# Autonomous Execution Plan: Phases 1.5-5

**Authorization:** Full autonomy for file creation, editing, command execution  
**Scope:** Complete refactoring pipeline (option pricing → agentes)  
**Mode:** Loop-driven, no user interaction unless blockers  
**Target:** 8-10 weeks of work compressed into 1-2 weeks of execution

---

## 🎯 Execution Strategy

### Sequential Phases (Interdependent)

```
Phase 1.5 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
Integration   Surface     Strategies   Agentes     Risk/Perf
1 week        2-3 wks     1-2 wks      2-3 wks     1 week
```

### Per-Phase Template (TDD Loop)

```
For each phase:
  1. Create domain/service modules (skeleton)
  2. Create comprehensive test suite (RED)
  3. Implement logic (GREEN)
  4. Run tests (validation)
  5. Commit with documentation
  6. Move to next phase
```

### Autonomy Rules

**Can do without asking:**
- Create any .py files (modules, tests, services)
- Create any .md documentation
- Create directories (backend/*, tests/*)
- Edit existing files (refactor, integrate)
- Run pytest, git commands
- Commit to current branch
- Install pip packages (if needed)

**Must ask/pause if:**
- Blockers detected (import errors, circular deps)
- Merge conflicts
- Test failures after 2 fix attempts
- Need to change architecture decision
- Need new external dependencies

---

## 📊 Phase-by-Phase Plan

### Phase 1.5: Integration (1 week)

**Goal:** Wire OptionPricer into core_engine

**Tasks:**
1. Refactor OptionBuilder to use OptionPricer
2. Update GatilhoEvaluator to accept Greeks
3. Update SignalComposer to include Greeks
4. Add 15 integration tests
5. Validate no regression in 874 tests

**Modules to modify:**
- `backend/services/option_builder.py` (refactor)
- `backend/services/gatilho_evaluator.py` (optional Greeks)
- `backend/services/signal_composer.py` (add Greeks fields)
- `tests/test_integration_pricing.py` (NEW)

**Success Criteria:**
- ✅ 874 + 15 tests passing
- ✅ OptionPricer integrated seamlessly
- ✅ No performance regression
- ✅ Greeks data flows through pipeline

**Estimated Duration:** 3-4 days

---

### Phase 2: Volatility Surface (2-3 weeks)

**Goal:** Model volatility across strikes/DTEs

**Tasks:**
1. Create `backend/domain/volatility_surface.py`
   - Surface builder
   - Skew/smile detection
   - IV interpolation
   - IV rank calculation

2. Create `backend/services/volatility_analyzer.py`
   - Historical IV tracking
   - Surface caching
   - Real-time updates

3. Add 80 tests
4. Integrate into GatilhoEvaluator

**Modules:**
- `backend/domain/volatility_surface.py` (250 LOC)
- `backend/services/volatility_analyzer.py` (200 LOC)
- `tests/test_volatility_surface.py` (80 tests)

**Success Criteria:**
- ✅ Surface builds correctly from chain data
- ✅ Skew/smile detection works
- ✅ IV rank correlates with historical data
- ✅ 80 tests passing
- ✅ No regressions in 889 tests

**Estimated Duration:** 8-10 days

---

### Phase 3: Multi-Leg Strategies (1-2 weeks)

**Goal:** Support spreads, straddles, condors

**Tasks:**
1. Create `backend/services/strategy_analyzer.py`
   - Spread analysis (max P&L, break-even)
   - Structured analysis (straddle, strangle, butterfly, iron condor)
   - Payoff simulation
   - Greeks aggregation

2. Create `backend/services/backtester.py`
   - Historical strategy P&L
   - Win rate, max drawdown
   - Performance metrics

3. Add 100 tests
4. Create visualization helpers

**Modules:**
- `backend/services/strategy_analyzer.py` (300 LOC)
- `backend/services/backtester.py` (150 LOC)
- `tests/test_strategy_analyzer.py` (100 tests)

**Success Criteria:**
- ✅ All strategy types analyzed correctly
- ✅ Payoff calculations verified
- ✅ Backtesting results match manual calcs
- ✅ 100 tests passing
- ✅ No regressions in 989 tests

**Estimated Duration:** 5-7 days

---

### Phase 4: Multiagent Orchestration (2-3 weeks)

**Goal:** LLM-driven decision pipeline

**Tasks:**
1. Create `backend/agents/` folder structure
   - `technical_analyst.py`
   - `risk_manager.py`
   - `strategy_selector.py`
   - `executor.py`

2. Create `backend/agents/orchestrator.py`
   - Agent coordination
   - Consensus logic
   - Fallback strategies

3. Add 80 tests
4. Integrate with core_engine

**Modules:**
- `backend/agents/*.py` (600 LOC total)
- `tests/test_agents.py` (80 tests)

**Success Criteria:**
- ✅ Agents communicate correctly
- ✅ Consensus logic works (e.g., 3/4 agree on trade)
- ✅ Fallback to deterministic path if LLM unavailable
- ✅ 80 tests passing
- ✅ No regressions in 1069 tests

**Estimated Duration:** 8-10 days

---

### Phase 5: Risk & Performance (1 week)

**Goal:** Production-grade risk management

**Tasks:**
1. Create `backend/services/risk_manager.py`
   - Portfolio Greeks aggregation
   - VaR calculation
   - Stress testing

2. Create `backend/services/performance_monitor.py`
   - Real-time metrics
   - P&L attribution
   - Slippage tracking

3. Create `backend/services/hedge_optimizer.py`
   - Delta-neutral rebalancing
   - Gamma/vega hedging

4. Add 60 tests

**Modules:**
- `backend/services/risk_manager.py` (250 LOC)
- `backend/services/performance_monitor.py` (150 LOC)
- `backend/services/hedge_optimizer.py` (100 LOC)
- `tests/test_risk_management.py` (60 tests)

**Success Criteria:**
- ✅ Portfolio Greeks calculated accurately
- ✅ VaR matches industry-standard calcs
- ✅ Hedge trades reduce Greeks to target
- ✅ 60 tests passing
- ✅ No regressions in 1129 tests

**Estimated Duration:** 5-6 days

---

## 🔄 Execution Loop Template

```python
# For each phase:
while not phase_complete:
    # Step 1: Create modules (skeleton)
    create_module_skeleton()
    
    # Step 2: Create test suite (RED)
    create_comprehensive_tests()
    run_pytest()  # Should fail (RED)
    
    # Step 3: Implement logic (GREEN)
    implement_logic()
    run_pytest()  # Should pass (GREEN)
    
    if tests_pass():
        # Step 4: Refactor if needed (REFACTOR)
        refactor_for_clarity()
        run_pytest()  # Validate still passes
        
        # Step 5: Commit
        git_commit(f"feat(phase-X): module implementation")
        
        phase_complete = True
    else:
        # Debug failures
        debug_and_fix()
        run_pytest()
```

---

## 📈 Cumulative Progress Tracking

| Phase | Start | End | LOC | Tests | Total Tests | Est. Time |
|-------|-------|-----|-----|-------|-------------|-----------|
| 1.5 | Day 0 | Day 4 | 300 | 15 | 889 | 4 days |
| 2 | Day 4 | Day 14 | 450 | 80 | 969 | 10 days |
| 3 | Day 14 | Day 21 | 450 | 100 | 1069 | 7 days |
| 4 | Day 21 | Day 31 | 600 | 80 | 1149 | 10 days |
| 5 | Day 31 | Day 36 | 500 | 60 | 1209 | 5 days |
| **TOTAL** | | | **2,300** | **335** | **1,209** | **36 days** |

**Aggressive Timeline (parallel where possible):** 3-4 weeks  
**Conservative Timeline:** 4-5 weeks

---

## ⚠️ Blocker Handling

If any blocker occurs:

**Import/Circular Dependency Error:**
- Stop current task
- Debug the import chain
- Refactor to break cycle
- Resume after fix

**Test Failure (3+ failures):**
- Stop current implementation
- Review logic vs. test assumptions
- Either fix implementation or adjust tests
- Never force tests to pass

**Merge Conflict:**
- Resolve conflicts manually
- Ensure all tests pass after
- Commit resolution

**Performance Regression:**
- Profile the code
- Optimize hot paths
- Revert if can't optimize
- Document why

---

## 🚀 Quick Start (Now)

**Execution sequence:**

```bash
# Terminal: Start Phase 1.5
python -m pytest tests/test_option_pricing.py  # Validate Phase 1
python -m pytest tests/  # Full suite baseline

# Then: Loop through phases 1.5-5
# Each phase: create → test → implement → commit
```

**Parallel Opportunities:**
- Phase 4 and 5 could start after Phase 3 complete
- But safest: sequential (each phase may inform next)

---

## 📋 Checklist for Each Commit

Before every `git commit`:
- [ ] All tests passing (run full suite)
- [ ] No ticker-specific code
- [ ] Works with ANY underlying
- [ ] Docstrings on public methods
- [ ] No import errors
- [ ] No unused imports
- [ ] No hardcoded values (use constants)
- [ ] Code follows ECC standards
- [ ] Commit message follows conventional commits

---

## 🎯 Success Criteria (End State)

**After all 5 phases:**
- ✅ 1,209 tests passing (100%)
- ✅ Coverage: 92% → 96%
- ✅ 2,300+ LOC added (generic architecture)
- ✅ 0 ticket-specific code
- ✅ 5 production-ready services
- ✅ Multiagent orchestration working
- ✅ Risk management framework in place
- ✅ Full documentation
- ✅ Ready for Phase 6 (production hardening)

---

## 📝 Backlog (After Core Phases Complete)

**Defer to post-refactoring:**
- PRIO3: Volume profile optimization
- RECV3: Data source validation
- ITUB4: Downtrend momentum filters
- Frontend: New dashboard components
- Performance: Index optimization
- Deployment: K8s config

---

**Status:** Ready to execute Phase 1.5  
**Autonomy Level:** MAXIMUM (only pause on blockers)  
**Next Action:** Start Phase 1.5 integration

---

*Generated: 2026-08-16*  
*Authority: Autonomous execution with blocker checkpoints*
