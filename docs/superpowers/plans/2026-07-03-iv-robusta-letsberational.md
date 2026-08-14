# IV Robusta com LetsBeRational (vollib) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir Newton-Raphson por LetsBeRational (vollib) para cálculo de IV implícita — mais rápido (10x), sem falha de convergência, fallback automático quando Newton-Raphson não converge.

**Architecture:** Nova função `implied_volatility_robust()` em [greeks.py](backend/domain/greeks.py) tenta LetsBeRational primeiro (via `vollib`), fallback para Newton-Raphson. A função original preservada para compatibilidade. Call sites passam a usar a versão robusta. Teste sem rede com mock do vollib.

**Tech Stack:** Python, vollib (nova dep), scipy, pytest.

---

## File Structure

- **Modify:** `backend/domain/greeks.py` — nova função `implied_volatility_robust()` + import vollib
- **Create:** `tests/test_iv_robust.py` — testes com mock, casos de convergência
- **Modify:** `requirements.txt` — adiciona `vollib`
- **Modify:** `backend/services/iv_history_service.py:25` — substitui `resolver_iv()` para usar IV robusta

---

## Task 1: Implementar fallback LetsBeRational

**Files:**
- Modify: `backend/domain/greeks.py`
- Modify: `requirements.txt`
- Create: `tests/test_iv_robust.py`

- [ ] **Step 1: Adicionar dependência**

```bash
echo "vollib" >> requirements.txt
```

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_iv_robust.py`:

```python
"""Testes de IV robusta com fallback LetsBeRational."""
from unittest.mock import patch

from backend.domain.greeks import implied_volatility, implied_volatility_robust


def test_letsberational_converge_rapido():
    S, K, T, market_price = 100.0, 100.0, 30/252, 2.5
    # vollib retorna IV exata
    with patch("backend.domain.greeks.black_scholes", return_value=0.25):
        iv = implied_volatility_robust(S, K, T, market_price, "CALL", sigma_init=0.5)
    assert 0.20 < iv < 0.30


def test_fallback_newton_quando_vollib_falha():
    S, K, T, market_price = 100.0, 100.0, 30/252, 2.5
    with patch("backend.domain.greeks.black_scholes", side_effect=RuntimeError("vollib erro")):
        iv = implied_volatility_robust(S, K, T, market_price, "CALL")
    # deve voltar pro Newton-Raphson e convergir
    assert 0.10 < iv < 0.50


def test_sem_vollib_nao_afeta_newton_original():
    # função original inalterada
    iv = implied_volatility(100.0, 100.0, 30/252, 2.5, "CALL")
    assert 0.10 < iv < 0.50
```

- [ ] **Step 3: Rodar e verificar que falha**

```bash
pytest tests/test_iv_robust.py -v
```

Expected: FAIL (`implied_volatility_robust` não existe)

- [ ] **Step 4: Implementar a função robusta em greeks.py**

Adicionar ao topo:

```python
from vollib.black_scholes.implied_volatility import implied_volatility as vollib_iv
```

E ao final do arquivo:

```python
def implied_volatility_robust(S: float, K: float, T: float, market_price: float,
                              opt_type: str = "CALL",
                              r: float = RISK_FREE_RATE_DEFAULT,
                              sigma_init: float = 0.5,
                              max_iter: int = 100, tol: float = 1e-6) -> float:
    """IV robusta: tenta LetsBeRational (vollib) primeiro, fallback Newton-Raphson."""
    if T <= 0 or market_price <= 0:
        return sigma_init
    
    try:
        sigma = vollib_iv(S, K, T, r, market_price, opt_type.upper())
        return float(sigma) if sigma else sigma_init
    except Exception:
        # Fallback: Newton-Raphson original
        return implied_volatility(S, K, T, market_price, opt_type, r, sigma_init, max_iter, tol)
```

- [ ] **Step 5: Rodar os testes e verificar que passam**

```bash
pytest tests/test_iv_robust.py -v
```

Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/domain/greeks.py tests/test_iv_robust.py requirements.txt
git commit -m "feat(iv): vollib LetsBeRational com fallback Newton-Raphson"
```

---

## Task 2: Substituir call sites de IV

**Files:**
- Modify: `backend/services/iv_history_service.py:25`

- [ ] **Step 1: Editar o call site**

Em `backend/services/iv_history_service.py`, encontrar a chamada a `implied_volatility` e substituir por `implied_volatility_robust`:

```python
from backend.domain.greeks import implied_volatility_robust

# linha ~25
iv_atm, fonte = resolver_iv(opcao["preco_tela"], preco, opcao["strike_real"], T, "CALL", hv_20d)
# ↓ muda para:
iv_atm = implied_volatility_robust(preco, opcao["strike_real"], T, opcao["preco_tela"], "CALL", r=get_selic_anual())
```

- [ ] **Step 2: Rodar os testes afetados**

```bash
pytest tests/test_iv_history_service.py -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/services/iv_history_service.py
git commit -m "feat(iv): usar LetsBeRational robusta na coleta de IV diária"
```

---

## Task 3: Regressão

- [ ] **Step 1: Suite completa**

```bash
pytest -q
```

Expected: PASS (sem regressão)

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "test(iv): regressão vollib LetsBeRational"
```
