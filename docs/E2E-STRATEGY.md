# E2E Testing Strategy — F0.2 Decisão

**Data:** 2026-08-15  
**Decisão:** Option A (E2E-heavy com fallback Unit-heavy)  
**Fase:** F1.5 — 3 critical flows

---

## 🎯 Opções Avaliadas

### Option A: E2E-Heavy (Recomendado ✅)

**Foco:** Testes de ponta a ponta via browser (Playwright)

```
Test Coverage:
├─ Flow 1: Motor → API → Frontend (completo)
├─ Flow 2: API dados vindos do motor
└─ Flow 3: Frontend renderiza signals corretamente

Estrutura:
└─ tests/e2e/
   ├─ motor-signal-flow.spec.ts (motor emite → API retorna → frontend exibe)
   ├─ api-data-consistency.spec.ts (API dados corretos, tipos validados)
   └─ ui-signal-rendering.spec.ts (UI exibe signal, atualiza em tempo real)

Ferramentas:
├─ Playwright (browser automation)
├─ Vitest (unit test integration)
└─ Docker (isolate tests)

Tempo de execução: ~20-30 min (CI)
Nível de confiança: 🟢 ALTA (testa integração real)
```

**Pros:**
- ✅ Testa integração de verdade (motor → API → frontend)
- ✅ Detecta bugs de interação entre camadas
- ✅ Pega erros de UI rendering que unit tests não pegam
- ✅ Simula comportamento real do usuário

**Cons:**
- ⚠️ Mais lento (20-30 min cada rodada)
- ⚠️ Frágil a mudanças de UI
- ⚠️ Precisa de infra (browser, DB)

---

### Option B: Unit-Heavy (Alternativa)

**Foco:** Testes unitários isolados de cada camada

```
Test Coverage:
├─ Motor tests (signal emission logic)
├─ API tests (endpoint contract, types)
└─ Frontend tests (component rendering, hooks)

Estrutura:
├─ tests/unit/motor.py (motor lógica isolada)
├─ tests/unit/api.py (endpoint mocks)
└─ tests/unit/frontend/ (React components + hooks)

Ferramentas:
├─ Pytest (backend)
├─ Vitest (frontend)
└─ Mock data (não precisa de browser)

Tempo de execução: ~5-10 min (CI)
Nível de confiança: 🟡 MÉDIA (testa camadas isoladas)
```

**Pros:**
- ✅ Rápido (5-10 min)
- ✅ Fácil de manter
- ✅ Simples de debugar (sem browser)

**Cons:**
- ⚠️ Não testa integração real
- ⚠️ Pode passar mesmo com bugs de integração
- ⚠️ Precisa mocks complexos (fácil divergir do real)

---

## ✅ Decisão: Option A (E2E-Heavy)

### Rationale

```
Prioridade: Confiança na refatoração > Velocidade do test
Fase F1-F8 é refactoring crítico
  → Precisa detectar bugs de integração
  → Unit tests sozinhos podem deixar passar

Golden Master já testa motor isoladamente
  → E2E testa a integração completa
  → Cobertura complementar
```

### Implementação (F1.5)

```
3 Flows Críticos:

1️⃣ Motor → API → Frontend (end-to-end)
   └─ User analisa ativo → motor emite sinal → API retorna → frontend exibe
   
2️⃣ API Data Consistency
   └─ Signal Schema validação (Pydantic) + frontend tipos (TS) sincronizados
   
3️⃣ Real-time Updates
   └─ Frontend recebe update → UI re-renderiza corretamente
```

---

## 📋 F1.5 Implementation Checklist

### Fase 1: Setup (1 dia)
- [ ] Instalar Playwright (`npm install -D @playwright/test`)
- [ ] Configurar `playwright.config.ts`
- [ ] Setup DB/fixtures para E2E (dados conhecidos)
- [ ] Mock do motor ou usar real (se possível)
- [ ] Criar base fixture page object

### Fase 2: 3 Critical Flows (1.5 dias)

#### Flow 1: motor-signal-flow.spec.ts
```typescript
test('Motor emits signal → API returns → Frontend displays', async ({ page }) => {
  // 1. Trigger motor (POST /analyze/{ativo})
  // 2. Wait for signal emission
  // 3. Verify API returns signal in correct format
  // 4. Verify frontend displays signal
  // 5. Check tooltip, styling, etc.
})
```

#### Flow 2: api-data-consistency.spec.ts
```typescript
test('API returns valid Signal (Pydantic schema)', async ({ page }) => {
  // 1. Make request to /api/signal/{id}
  // 2. Validate response schema (Pydantic-generated TS types)
  // 3. Verify no `undefined` fields
  // 4. Check enum values (`tipo_sinal`, etc.)
})

test('TypeScript types match API response', async () => {
  // 1. Fetch API schema
  // 2. Verify generated TS types match
  // 3. No missing fields, no extra fields
})
```

#### Flow 3: ui-signal-rendering.spec.ts
```typescript
test('Frontend correctly renders Signal in card/chart', async ({ page }) => {
  // 1. Load page with known signal data
  // 2. Verify all fields rendered correctly
  // 3. Check calculations (entry, stop loss, etc.)
  // 4. Verify styling (green for CALL, red for PUT)
})

test('Real-time update: signal refreshes without page reload', async ({ page }) => {
  // 1. Wait for initial load
  // 2. Trigger new signal (API update)
  // 3. Verify frontend updates (SWR refetch)
  // 4. No errors in console
})
```

### Fase 3: CI Integration (0.5 dia)
- [ ] Add GitHub Action job for E2E
- [ ] Run on every PR to `f*` branches
- [ ] Upload screenshots on failure
- [ ] Upload video trace
- [ ] Quarantine flaky tests

---

## 🔄 Fallback Strategy (Se E2E Quebrar)

**Se E2E levar muito tempo ou for muito frágil:**

```
Week 1-2: Rodar E2E (full)
Week 3+: Se problems:
  ├─ Reduce frequency (nightly, not every push)
  ├─ Quarantine flaky tests (don't block merge)
  └─ Combine with unit tests (hybrid)
```

---

## 📊 Success Criteria

| Item | Target | By When |
|------|--------|---------|
| **3 E2E flows passing** | 100% | End of F1.5 |
| **CI job duration** | < 30 min | F1.5 |
| **Flakiness** | < 5% flake rate | F2 |
| **Coverage** | 3 critical paths | F1.5 |

---

## 🎬 Timeline

```
F1.1a (Mon 18)  → Pydantic model + validators
F1.1b (Tue 19)  → Motor adapter
F1.2 (Wed 20)   → TS generator
F1.3 (Thu 21)   → Contract tests
F1.5 (Fri 22)   → E2E setup + 3 flows (THIS)

Start E2E: End of Week 1
Finish E2E: By end of F1.5
```

---

## 🔗 Related Documents

- [QUALITY-GATES.md](QUALITY-GATES.md) — Coverage gates (includes E2E)
- [AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md) — F1.5 agent assignment
- [tests/e2e/](../tests/e2e/) — E2E test fixtures (TBD F1.5)

---

**Decision:** ✅ **OPTION A — E2E-Heavy**  
**Approved:** 2026-08-15  
**Implementation:** F1.5  
**Confidence:** 90%+

