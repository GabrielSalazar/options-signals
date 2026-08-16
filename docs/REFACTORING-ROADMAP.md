# Option Pricing Refactoring Roadmap

**Project:** B3 Options Signals - Generic Pricing Architecture  
**Start Date:** 2026-08-16  
**Goal:** Build tier-agnostic, modular option pricing system from 31 best-in-class repositories  
**Principle:** All changes generic (work with ANY ticker), never ticker-specific

---

## 📍 Phases Overview

| Phase | Focus | Timeline | Status |
|-------|-------|----------|--------|
| **Phase 1** | Black-Scholes + Greeks | ✅ DONE | 320 LOC, 20 tests |
| **Phase 1.5** | Integration into core_engine | 1 week | ⏳ NEXT |
| **Phase 2** | Volatility surface + IV rank | 2-3 weeks | 📋 PLANNED |
| **Phase 3** | Multi-leg strategies | 1-2 weeks | 📋 PLANNED |
| **Phase 4** | Agentes multiagente | 2-3 weeks | 📋 PLANNED |
| **Phase 5** | Risk & performance | 1 week | 📋 PLANNED |

**Total Estimate:** 8-10 weeks  
**LOC Added:** ~3,500-4,000  
**Tests Added:** ~400-500  
**Target Coverage:** 92% → 96%

---

## ✅ Phase 1: COMPLETE

**Objective:** Generic Black-Scholes pricing engine

**Deliverables:**
- ✅ `backend/domain/option_pricing.py` (320 LOC)
- ✅ `tests/test_option_pricing.py` (20 tests)
- ✅ Documentation: `PHASE1-OPTION-PRICING.md`

**What works:**
- Vanilla option pricing (CALL/PUT)
- Greeks: Delta, Gamma, Vega, Theta, Rho
- Implied volatility solver
- Edge case handling (expiry, vol, dividends)

**Validation:** 20/20 tests passing ✅

**Next:** Phase 1.5 (integration)

---

## ⏳ Phase 1.5: INTEGRATION (Next)

**Objective:** Wire OptionPricer into existing core_engine

**Tasks:**

```python
# 1. Replace OptionBuilder with OptionPricer
# Before:
class OptionBuilder:
    def build(self, ticker, preco, tipo_sinal, ...):
        return {
            "premium_est": greeks.get("theta", 0.1),  # Dummy
        }

# After:
class OptionBuilder:
    def __init__(self):
        self.pricer = OptionPricer()
    
    def build(self, ticker_data, option_data, tipo_sinal):
        result = self.pricer.price(
            OptionInput(
                spot_price=ticker_data['price'],
                strike_price=option_data['strike'],
                time_to_expiry=self.time_to_expiry(option_data['dte']),
                volatility=option_data['iv'],
                risk_free_rate=self.get_risk_free_rate(),
                dividend_yield=ticker_data.get('div_yield', 0),
                option_type=OptionType.CALL if 'CALL' in tipo_sinal else OptionType.PUT,
            )
        )
        return {
            "premium": result.premium,
            "delta": result.delta,
            "gamma": result.gamma,
            "vega": result.vega,
            "theta": result.theta,
            "rho": result.rho,
            "strike": option_data['strike'],
            "dte": option_data['dte'],
        }
```

**Checklist:**
- [ ] Update OptionBuilder to use OptionPricer
- [ ] Add unit tests for integration
- [ ] Validate against PRIO3, RECV3, ITUB4 test cases
- [ ] Check no regression in existing 854 tests
- [ ] Commit: `feat(phase1.5): Integrate OptionPricer into core_engine`

**Timeline:** ~1 week  
**Tests added:** 10-15  
**LOC changed:** 200-300 (in OptionBuilder + tests)

---

## 📊 Phase 2: Volatility Surface (PLANNED)

**Objective:** Model volatility as variable across strikes and DTEs

**Modules to create:**
- `backend/domain/volatility_surface.py` (250 LOC)
- `backend/services/volatility_analyzer.py` (200 LOC)
- `tests/test_volatility_surface.py` (80 tests)

**Features:**
1. **Volatility Smile Detection**
   - Detect skew (OTM put vol vs call vol)
   - Detect smirk patterns
   - Interpolate IV for strikes not in chain

2. **IV Rank Calculation**
   - Historical IV percentile
   - IV context (is current IV high or low?)
   - Used in gatilho_evaluator scoring

3. **Heston Model (Optional)**
   - Stochastic volatility
   - Jump diffusion for events
   - Better American option pricing

4. **Surface Visualization**
   - 3D plot: Strike × DTE × IV
   - Detect anomalies

**Repositories used:**
- `jkirkby3/fypy` (calibration)
- `cantaro86/Financial-Models-Numerical-Methods` (Heston)
- `Open-Lemma/options-implied-probability` (distributions)

**Checklist:**
- [ ] Implement surface builder
- [ ] Add skew/smile detection
- [ ] Calculate IV Rank
- [ ] Add 80 tests
- [ ] Integrate into gatilho_evaluator

**Timeline:** 2-3 weeks  
**Tests added:** 80  
**LOC added:** 450

---

## 🎯 Phase 3: Multi-Leg Strategies (PLANNED)

**Objective:** Support spreads, straddles, iron condors, etc.

**Modules:**
- `backend/services/strategy_analyzer.py` (300 LOC)
- `tests/test_strategy_analyzer.py` (100 tests)

**Features:**
1. **Spread Analysis**
   - Call spread, put spread
   - Max profit/loss
   - Break-even points
   - Greeks of spread

2. **Structured Analysis**
   - Straddle (long call + put, same strike)
   - Strangle (call OTM + put OTM)
   - Butterfly (long + 2 short + long)
   - Iron Condor (sell call spread + sell put spread)

3. **Payoff Visualization**
   - Graph P&L vs spot price
   - Greeks evolution
   - Risk/reward display

4. **Backtesting Framework**
   - Historical P&L
   - Win rate
   - Max drawdown

**Repositories used:**
- `goldspanlabs/optopsy` (spread backtesting)
- `Viprasol-Tech/options-strategy-analyzer` (templates)

**Checklist:**
- [ ] Implement strategy analyzer
- [ ] Add 100 tests
- [ ] Integrate into painel
- [ ] Backtesting module

**Timeline:** 1-2 weeks  
**Tests added:** 100  
**LOC added:** 300

---

## 🤖 Phase 4: Agentes Multiagente (PLANNED)

**Objective:** LLM-orchestrated analysis and decision-making

**Agents:**
1. **Technical Analyst**
   - Trend analysis
   - Support/resistance
   - Confluence detection

2. **Risk Manager**
   - Greeks exposure
   - VaR calculation
   - Position limits

3. **Strategy Selector**
   - Match market view to structure
   - Optimize strikes/DTEs
   - Score structures

4. **Executor**
   - Final validation
   - Order sizing
   - Risk gates

**Repositories used:**
- `TauricResearch/TradingAgents` (multiagent framework)
- `The-Swarm-Corporation/AutoHedge` (execution)
- `dongzhuoyao/finance-option-skills` (skills)

**Checklist:**
- [ ] Implement agent framework
- [ ] Create 4 agent types
- [ ] Orchestrator
- [ ] LLM integration
- [ ] Consensus logic

**Timeline:** 2-3 weeks  
**Tests added:** 80  
**LOC added:** 600

---

## 🔧 Phase 5: Risk & Performance (PLANNED)

**Objective:** Production-ready risk management

**Modules:**
- `backend/services/risk_manager.py`
- `backend/services/performance_monitor.py`
- `backend/services/hedge_optimizer.py`

**Features:**
1. **Risk Metrics**
   - Portfolio delta/gamma/vega
   - Value-at-Risk (VaR)
   - Expected Shortfall
   - Stress testing

2. **Performance Monitoring**
   - Real-time Greeks tracking
   - P&L attribution
   - Slippage analysis

3. **Hedge Automation**
   - Delta neutral rebalancing
   - Gamma hedging
   - Vega hedging

**Repositories used:**
- `goldmansachs/gs-quant` (risk framework)
- `TechfaneTechnologies/QtsApp` (dashboard)

**Checklist:**
- [ ] Risk calculation engine
- [ ] Performance tracker
- [ ] Hedge algorithms
- [ ] Tests & validation

**Timeline:** 1 week  
**Tests added:** 60  
**LOC added:** 400

---

## 🚀 Backlog (Specific to Tickers)

**⚠️ DO NOT IMPLEMENT NOW — Defer to post-refactoring**

These are ticket-specific optimizations that go into backlog:
- PRIO3: Volume confirmation on reversal
- RECV3: Data source validation
- ITUB4: Downtrend momentum filters

All ticker-specific work AFTER generic framework is solid.

---

## 📊 Cumulative Progress

| Phase | LOC | Tests | Coverage | Status |
|-------|-----|-------|----------|--------|
| Phase 1 | 320 | 20 | - | ✅ DONE |
| Phase 1.5 | 200-300 | 10-15 | - | ⏳ NEXT |
| Phase 2 | 450 | 80 | - | 📋 PLANNED |
| Phase 3 | 300 | 100 | - | 📋 PLANNED |
| Phase 4 | 600 | 80 | - | 📋 PLANNED |
| Phase 5 | 400 | 60 | - | 📋 PLANNED |
| **Total** | **2,270-2,370** | **350-365** | **92% → 96%** | 📊 Tracked |

---

## 🎯 Quality Gates (All Phases)

Before each commit:
- [ ] 100% tests passing
- [ ] No ticket-specific code
- [ ] Works with ANY underlying
- [ ] Documented with examples
- [ ] Follows ECC coding standards

---

## 📋 Next Action

**Phase 1.5: Integration** (1 week)
- Wire OptionPricer into core_engine.py
- Update OptionBuilder class
- Add integration tests
- Validate no regressions

**After that:** Phase 2 (Volatility Surface)

---

**Created:** 2026-08-16  
**Last Updated:** 2026-08-16  
**Owner:** Autonomous Refactoring Loop  
**Commit:** 734e0ed
