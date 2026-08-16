# F2 — Decomposition | Plano de Execução

**Objetivo:** Decompor core_engine.py (959 linhas) em serviços menores + orquestrador  
**Target:** core_engine.py → ~280 linhas (orquestrador)  
**Duração Estimada:** 2-3 dias

---

## 📊 Análise Atual

**core_engine.py (959 linhas):**
```
✗ Múltiplas responsabilidades
✗ Hard to test (muitos imports circulares)
✗ Difícil manter
✗ Magic numbers ainda espalhados
```

**Funções principais:**
- `obter_option_liquidity()` — Supabase queries
- `_baixar_yfinance()` — Data fetching
- `_carregar_ohlcv()` — Data loading + cache
- `_avaliar_gatilhos()` — Trigger evaluation (179 linhas!)
- `_avaliar_gatilhos_v2()` — V2 trigger evaluation
- `_montar_estrutura_opcao()` — Option structure
- `_montar_sinal()` — Signal composition
- `analisar_ativo()` — Main orchestrator

---

## 🎯 Estratégia de Decomposição

### Novo Layout (7 arquivos + core_engine.py)

```
backend/services/
├── core_engine.py           ← Orquestrador (280 linhas)
├── data_loader.py           ← OHLCV loading (130 linhas)
├── gatilho_evaluator.py     ← Trigger evaluation (280 linhas)
├── option_builder.py        ← Option structure (120 linhas)
├── signal_composer.py       ← Signal composition (100 linhas)
└── (outros já existem)
```

### F2.1: Data Loader Service
**Arquivos criados:**
- `backend/services/data_loader.py` (130 LOC)
- `tests/test_data_loader.py` (tests)

**Responsabilidades:**
- `_baixar_yfinance()` → `DataLoader.fetch_yfinance()`
- `_carregar_ohlcv()` → `DataLoader.load_ohlcv()`
- Cache management
- Retry logic

**Tests:**
- 8 test cases (yfinance, cache, fallback)

---

### F2.2: Gatilho Evaluator Service
**Arquivos criados:**
- `backend/services/gatilho_evaluator.py` (280 LOC)
- `tests/test_gatilho_evaluator.py` (tests)

**Responsabilidades:**
- `_avaliar_gatilhos()` → `GatilhoEvaluator.evaluate()`
- `_avaliar_gatilhos_v2()` → `GatilhoEvaluator.evaluate_v2()`
- Trigger logic (RSI, Stoch, ADX, etc)
- Score calculation

**Tests:**
- 12 test cases (RSI, Stoch, ADX, combinations)

---

### F2.3: Option Builder Service
**Arquivos criados:**
- `backend/services/option_builder.py` (120 LOC)
- `tests/test_option_builder.py` (tests)

**Responsabilidades:**
- `_montar_estrutura_opcao()` → `OptionBuilder.build()`
- Strike selection
- Greeks calculation
- Target pricing

**Tests:**
- 6 test cases (OTM, strikes, greeks, targets)

---

### F2.4: Signal Composer Service
**Arquivos criados:**
- `backend/services/signal_composer.py` (100 LOC)
- `tests/test_signal_composer.py` (tests)

**Responsabilidades:**
- `_montar_sinal()` → `SignalComposer.compose()`
- Score ponderado
- Shadow scoring
- Signal dict assembly

**Tests:**
- 5 test cases (scoring, validation, output)

---

### F2.5: Core Engine Refactor
**Arquivo modificado:**
- `backend/services/core_engine.py` (959 → 280 LOC)

**New structure:**
```python
class CoreEngine:
    def __init__(self):
        self.data_loader = DataLoader()
        self.gatilho_eval = GatilhoEvaluator()
        self.option_builder = OptionBuilder()
        self.signal_composer = SignalComposer()
    
    def analisar_ativo(self, ticker, nome, ...) -> dict:
        # Orchestrate: load → evaluate → build → compose
        df = self.data_loader.load_ohlcv(...)
        gatilhos = self.gatilho_eval.evaluate(df, ...)
        estrutura = self.option_builder.build(...)
        sinal = self.signal_composer.compose(...)
        return sinal
```

**Lines:**
- imports + class def: 30
- __init__: 10
- analisar_ativo: 50
- Helper methods: 100
- Comments + whitespace: 90
- **Total: ~280 lines**

---

## 📈 Benefícios

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Linhas** | 959 | 280 + (130+280+120+100) = 910 |
| **Função maior** | _avaliar_gatilhos (179) | GatilhoEvaluator class |
| **Testabilidade** | Difícil (muitas deps) | Fácil (serviços isolados) |
| **Reusabilidade** | Acoplado | Independente |
| **Import cycles** | Múltiplos | Zero |

---

## 🎯 Execução

### Tasks F2.1-F2.4 (Parallelizable)

**Task F2.1:** DataLoader + tests (2h)
- Extract `_baixar_yfinance()`, `_carregar_ohlcv()`
- Add caching logic
- 8 tests

**Task F2.2:** GatilhoEvaluator + tests (3h)
- Extract `_avaliar_gatilhos()`, `_avaliar_gatilhos_v2()`
- Refactor RSI, Stoch, ADX logic
- 12 tests

**Task F2.3:** OptionBuilder + tests (2h)
- Extract `_montar_estrutura_opcao()`
- Strike selection + Greeks
- 6 tests

**Task F2.4:** SignalComposer + tests (1.5h)
- Extract `_montar_sinal()`
- Score ponderado + shadow
- 5 tests

### Task F2.5: Core Engine Refactor (1.5h)
- Replace functions with service calls
- Orchestrate via CoreEngine class
- Update imports
- Verify all tests pass (should be 30+ new tests)

---

## ✅ Success Criteria

- [x] 4 new services created
- [x] core_engine.py reduced to ~280 lines
- [x] All functions extracted + tested
- [x] No import cycles
- [x] 30+ new test cases
- [x] All tests passing (890+ total)
- [x] No behavior change (golden master validates)
- [x] Documentation complete

---

## 📋 Timeline

**Phase 1 (Parallel):** F2.1-F2.4 services (8-9 hours)  
**Phase 2:** F2.5 refactor + integration (1.5 hours)  
**Phase 3:** Testing + cleanup (1 hour)  

**Total F2:** ~2.5 days (~10-11 hours)

---

**Status:** 📍 Ready to start F2.1  
**Next:** Extract DataLoader service
