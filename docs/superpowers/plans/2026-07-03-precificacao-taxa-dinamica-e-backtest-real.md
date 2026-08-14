# Melhorias de Precificação (Taxa Dinâmica + 252 dias + Backtest Real) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir três imprecisões de precificação do motor de sinais: taxa livre de risco fixa (`0.135`), Theta em base de 365 dias (deveria ser 252, como o T já usa) e backtest sem prêmios reais de opções.

**Architecture:** Camada de domínio (`greeks.py`) permanece pura — a taxa é injetada nos call sites. Um novo serviço `risk_free_service.py` busca a SELIC via `python-bcb` (série SGS 432) com cache de 24h e fallback offline. O backtest ganha uma fonte opcional de prêmios reais via COTAHIST (`rb3`).

**Tech Stack:** Python, FastAPI, scipy, `python-bcb` (nova dep), `rb3` (nova dep), pytest.

**Escopo:** Este plano cobre as 3 melhorias de prioridade ⭐⭐⭐ (itens 1–3 da análise). Os itens 4–7 (ffn, vollib, curva ANBIMA, superfície de vol) ficam em backlog e viram planos próprios.

---

## File Structure

- **Create:** `backend/services/risk_free_service.py` — busca/cacheia a SELIC anual do BCB, com fallback.
- **Create:** `tests/test_risk_free_service.py` — testes do serviço de taxa.
- **Modify:** `backend/domain/greeks.py` — adiciona `TRADING_DAYS_PER_YEAR`, corrige Theta para base 252.
- **Modify:** `tests/test_greeks.py` — ajusta expectativa do Theta.
- **Modify:** `backend/services/core_engine.py:594` — injeta a taxa dinâmica em `calculate_greeks`.
- **Modify:** `backend/domain/options_math.py:120-128` — aceita `r` como parâmetro em vez de constante fixa.
- **Modify:** `requirements.txt` — adiciona `python-bcb` e `rb3`.
- **Create:** `backend/services/cotahist_service.py` — carrega prêmios reais de opções via `rb3`.
- **Create:** `tests/test_cotahist_service.py` — testes do loader COTAHIST (com fixture, sem rede).

---

## Task 1: Serviço de taxa livre de risco dinâmica (SELIC via BCB)

**Files:**
- Create: `backend/services/risk_free_service.py`
- Test: `tests/test_risk_free_service.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Adicionar dependência**

Adicionar ao final de `requirements.txt`:

```
python-bcb
```

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_risk_free_service.py`:

```python
"""Testes do serviço de taxa livre de risco (SELIC via BCB) com cache e fallback."""
from unittest.mock import patch

import pandas as pd

from backend.domain.greeks import RISK_FREE_RATE_DEFAULT
from backend.services import risk_free_service


def _fake_sgs_df(valor_percent: float):
    # python-bcb.sgs.get retorna DataFrame indexado por data, coluna = série
    return pd.DataFrame({"selic": [valor_percent]},
                        index=pd.to_datetime(["2026-07-01"]))


def test_selic_convertida_para_decimal():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               return_value=_fake_sgs_df(15.0)) as mock_get:
        taxa = risk_free_service.get_selic_anual()
    assert abs(taxa - 0.15) < 1e-9
    mock_get.assert_called_once()


def test_fallback_quando_bcb_falha():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               side_effect=RuntimeError("bcb offline")):
        taxa = risk_free_service.get_selic_anual()
    assert taxa == RISK_FREE_RATE_DEFAULT


def test_cache_evita_segunda_chamada():
    risk_free_service._invalidate_cache()
    with patch("backend.services.risk_free_service.sgs.get",
               return_value=_fake_sgs_df(12.5)) as mock_get:
        primeira = risk_free_service.get_selic_anual()
        segunda = risk_free_service.get_selic_anual()
    assert primeira == segunda == 0.125
    mock_get.assert_called_once()
```

- [ ] **Step 3: Rodar o teste e verificar que falha**

Run: `pytest tests/test_risk_free_service.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'backend.services.risk_free_service'`

- [ ] **Step 4: Implementar o serviço**

Criar `backend/services/risk_free_service.py`:

```python
"""Taxa livre de risco (SELIC meta anual) via BCB/SGS com cache de 24h e fallback.

Série SGS 432 = meta Selic definida pelo Copom (% a.a.). Convertida para decimal.
Mantém a camada de domínio (greeks.py) pura: a taxa é injetada nos call sites.
"""
import logging
import time

from bcb import sgs

from backend.domain.greeks import RISK_FREE_RATE_DEFAULT

logger = logging.getLogger("b3_api")

_SGS_SELIC_META = 432
_TTL_SEGUNDOS = 24 * 3600

_cache_valor: float | None = None
_cache_ts: float = 0.0


def _invalidate_cache() -> None:
    """Uso em testes: zera o cache em memória."""
    global _cache_valor, _cache_ts
    _cache_valor = None
    _cache_ts = 0.0


def get_selic_anual() -> float:
    """Retorna a SELIC meta anual em decimal (ex.: 0.15). Fallback: RISK_FREE_RATE_DEFAULT."""
    global _cache_valor, _cache_ts
    agora = time.time()
    if _cache_valor is not None and (agora - _cache_ts) < _TTL_SEGUNDOS:
        return _cache_valor
    try:
        df = sgs.get({"selic": _SGS_SELIC_META}, last=1)
        valor_percent = float(df["selic"].iloc[-1])
        taxa = valor_percent / 100.0
        _cache_valor = taxa
        _cache_ts = agora
        return taxa
    except Exception as e:
        logger.warning(f"SELIC via BCB indisponível ({e}); usando fallback {RISK_FREE_RATE_DEFAULT}")
        return RISK_FREE_RATE_DEFAULT
```

- [ ] **Step 5: Rodar os testes e verificar que passam**

Run: `pytest tests/test_risk_free_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/services/risk_free_service.py tests/test_risk_free_service.py requirements.txt
git commit -m "feat(precificacao): serviço de taxa livre de risco dinâmica (SELIC via BCB)"
```

---

## Task 2: Injetar a taxa dinâmica nos call sites de precificação

**Files:**
- Modify: `backend/domain/options_math.py:118-128`
- Modify: `backend/services/core_engine.py:594`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_options_math.py`:

```python
from unittest.mock import patch

from backend.domain.options_math import precificar_bs


def test_precificar_bs_usa_taxa_injetada():
    # r maior encarece a call; comprova que o parâmetro r é respeitado
    barato = precificar_bs(preco=100.0, strike=100.0, dte=30, iv=0.30,
                           tipo="CALL", r=0.05)
    caro = precificar_bs(preco=100.0, strike=100.0, dte=30, iv=0.30,
                         tipo="CALL", r=0.20)
    assert caro > barato
```

> **Nota:** confira a assinatura real de `precificar_bs` em `backend/domain/options_math.py:118` antes de editar. Se o nome/args diferirem, ajuste o teste e o Step 3 para casar exatamente com a função existente.

- [ ] **Step 2: Rodar o teste e verificar que falha**

Run: `pytest tests/test_options_math.py::test_precificar_bs_usa_taxa_injetada -v`
Expected: FAIL com `TypeError: precificar_bs() got an unexpected keyword argument 'r'`

- [ ] **Step 3: Adicionar parâmetro `r` em `precificar_bs`**

Em `backend/domain/options_math.py`, na função em torno da linha 118, tornar `r` um parâmetro com default na constante (mantém compatibilidade):

```python
def precificar_bs(preco, strike, dte, iv, tipo="CALL", r=RISK_FREE_RATE_DEFAULT):
    """Precifica via Black-Scholes com taxa livre de risco, delegando a greeks."""
    t = max(dte, 1) / 252
    pricer = bs_call_price if tipo.upper() == "CALL" else bs_put_price
    premio = pricer(preco, strike, t, r=r, sigma=iv)
    return premio
```

- [ ] **Step 4: Rodar o teste e verificar que passa**

Run: `pytest tests/test_options_math.py::test_precificar_bs_usa_taxa_injetada -v`
Expected: PASS

- [ ] **Step 5: Injetar a taxa dinâmica no core_engine**

Em `backend/services/core_engine.py:594`, adicionar o import no topo do arquivo:

```python
from backend.services.risk_free_service import get_selic_anual
```

E alterar a chamada de `calculate_greeks`:

```python
    greeks = calculate_greeks(preco, strike_ref, T, iv_impl, tipo_sinal, r=get_selic_anual())
```

- [ ] **Step 6: Rodar a suíte afetada e verificar que passa**

Run: `pytest tests/test_options_math.py tests/test_core_engine.py -v`
Expected: PASS (nenhuma regressão)

- [ ] **Step 7: Commit**

```bash
git add backend/domain/options_math.py backend/services/core_engine.py tests/test_options_math.py
git commit -m "feat(precificacao): injetar SELIC dinâmica em greeks e precificar_bs"
```

---

## Task 3: Padronizar Theta na base de 252 dias úteis

**Files:**
- Modify: `backend/domain/greeks.py:15,62-70`
- Modify: `tests/test_greeks.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_greeks.py`:

```python
from backend.domain.greeks import TRADING_DAYS_PER_YEAR


def test_theta_usa_base_252():
    assert TRADING_DAYS_PER_YEAR == 252
    g = calculate_greeks(S, K, T, SIGMA, "CALL", r=R)
    # Theta anualizado sem a divisão por dias; deve bater com o valor/252
    d1, d2 = _d1_d2(S, K, T, R, SIGMA)
    theta_anual = (-(S * math.exp(-d1**2 / 2) / math.sqrt(2 * math.pi) * SIGMA)
                   / (2 * math.sqrt(T))
                   - R * K * math.exp(-R * T) *
                   (0.5 * (1 + math.erf(d2 / math.sqrt(2)))))
    assert abs(g["theta"] - round(theta_anual / 252, 6)) < 1e-4
```

- [ ] **Step 2: Rodar o teste e verificar que falha**

Run: `pytest tests/test_greeks.py::test_theta_usa_base_252 -v`
Expected: FAIL com `ImportError: cannot import name 'TRADING_DAYS_PER_YEAR'`

- [ ] **Step 3: Adicionar a constante e corrigir o Theta**

Em `backend/domain/greeks.py`, após a linha 15 adicionar:

```python
TRADING_DAYS_PER_YEAR = 252  # base B3; T do projeto é medido em dte/252
```

Substituir `/ 365` por `/ TRADING_DAYS_PER_YEAR` nas duas linhas do Theta (call e put):

```python
        theta = (-(S * pdf_d1 * sigma) / (2 * sqrt_T)
                 - r * K * math.exp(-r * T) * norm.cdf(d2)) / TRADING_DAYS_PER_YEAR
```

```python
        theta = (-(S * pdf_d1 * sigma) / (2 * sqrt_T)
                 + r * K * math.exp(-r * T) * norm.cdf(-d2)) / TRADING_DAYS_PER_YEAR
```

- [ ] **Step 4: Ajustar testes de Theta pré-existentes**

Rodar a suíte de greeks para localizar asserts de Theta que usavam base 365 e atualizar os valores esperados (o Theta ficará ~1,45× maior em módulo: 365/252).

Run: `pytest tests/test_greeks.py -v`
Expected: identificar falhas em asserts antigos de Theta; corrigir os valores esperados conforme a saída atual.

- [ ] **Step 5: Rodar os testes e verificar que passam**

Run: `pytest tests/test_greeks.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/domain/greeks.py tests/test_greeks.py
git commit -m "fix(greeks): padronizar Theta na base de 252 dias úteis (B3)"
```

---

## Task 4: Loader de prêmios reais de opções via COTAHIST (rb3)

**Files:**
- Create: `backend/services/cotahist_service.py`
- Test: `tests/test_cotahist_service.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Adicionar dependência**

Adicionar ao final de `requirements.txt`:

```
rb3
```

- [ ] **Step 2: Escrever o teste que falha (com fixture, sem rede)**

Criar `tests/test_cotahist_service.py`:

```python
"""Loader de prêmios reais de opções via COTAHIST. Usa DataFrame injetado (sem rede)."""
import pandas as pd

from backend.services.cotahist_service import filtrar_opcoes_do_ativo


def _df_cotahist():
    return pd.DataFrame({
        "cod_negociacao": ["PETRG100", "PETRG100", "VALEG60"],
        "tipo_mercado":   [70, 70, 70],   # 70 = opção de compra na B3
        "preco_ultimo":   [1.50, 1.55, 2.10],
        "data_referencia": pd.to_datetime(["2026-06-30", "2026-07-01", "2026-07-01"]),
    })


def test_filtra_series_do_ativo():
    out = filtrar_opcoes_do_ativo(_df_cotahist(), ativo_base="PETR")
    assert set(out["cod_negociacao"]) == {"PETRG100"}
    assert len(out) == 2  # duas datas da mesma série


def test_ativo_inexistente_retorna_vazio():
    out = filtrar_opcoes_do_ativo(_df_cotahist(), ativo_base="ITUB")
    assert out.empty
```

- [ ] **Step 3: Rodar o teste e verificar que falha**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'backend.services.cotahist_service'`

- [ ] **Step 4: Implementar o loader**

Criar `backend/services/cotahist_service.py`:

```python
"""Carrega e filtra prêmios reais de opções do arquivo COTAHIST da B3 via rb3.

Separa o download (rb3, com rede) do filtro (puro, testável) para permitir testes
sem rede e reuso no backtest (validação de hit-rate contra prêmios que ocorreram).
"""
import logging

import pandas as pd

logger = logging.getLogger("b3_api")

# Tipos de mercado B3 no COTAHIST: 70 = opção de compra, 80 = opção de venda.
_TIPOS_OPCAO = (70, 80)


def filtrar_opcoes_do_ativo(df: pd.DataFrame, ativo_base: str) -> pd.DataFrame:
    """Filtra o DataFrame COTAHIST para as séries de opção do ativo informado."""
    if df.empty:
        return df
    base = ativo_base.upper().strip()
    mask = (
        df["tipo_mercado"].isin(_TIPOS_OPCAO)
        & df["cod_negociacao"].str.upper().str.startswith(base)
    )
    return df.loc[mask].reset_index(drop=True)


def carregar_cotahist_diario(data_ref: str) -> pd.DataFrame:
    """Baixa o COTAHIST diário via rb3 e retorna DataFrame padronizado.

    data_ref: 'YYYY-MM-DD'. Requer rede; falha retorna DataFrame vazio.
    """
    try:
        import rb3  # import tardio: dep pesada, só quando há download real
        raw = rb3.cotahist(data_ref)  # ajuste conforme a API instalada do rb3
        return pd.DataFrame(raw)
    except Exception as e:
        logger.warning(f"COTAHIST indisponível para {data_ref}: {e}")
        return pd.DataFrame()
```

> **Nota de integração:** a API pública do `rb3` evolui — confirme o nome/args do downloader (`rb3.cotahist` ou equivalente) e os nomes de coluna reais após instalar. Ajuste `carregar_cotahist_diario` e as colunas de `_df_cotahist()` para casar. O filtro puro (`filtrar_opcoes_do_ativo`) é a peça estável.

- [ ] **Step 5: Rodar os testes e verificar que passam**

Run: `pytest tests/test_cotahist_service.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/services/cotahist_service.py tests/test_cotahist_service.py requirements.txt
git commit -m "feat(backtest): loader de prêmios reais de opções via COTAHIST (rb3)"
```

---

## Task 5: Regressão completa e documentação

**Files:**
- Modify: `docs/BACKLOG.md`

- [ ] **Step 1: Rodar a suíte completa do backend**

Run: `pytest -q`
Expected: PASS (sem regressões)

- [ ] **Step 2: Registrar itens não implementados no backlog**

Adicionar em `docs/BACKLOG.md` uma seção "Precificação — próximos passos" com os itens 4–7 da análise que ficaram fora deste plano:

```markdown
## Precificação — próximos passos (análise repositórios B3, jul/2026)
- [ ] Métricas de performance no backtest (Sharpe/Sortino/drawdown) — ref. ffn
- [ ] IV robusta com fallback LetsBeRational — ref. vollib
- [ ] Curva de juros por vencimento (estrutura a termo) — ref. brasa/ANBIMA
- [ ] Superfície de volatilidade / skew — ref. ysaporito/QuantLib
- [ ] Integrar COTAHIST no fluxo de backtest para medir hit-rate PUCK (Fase 4)
```

- [ ] **Step 3: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs(backlog): próximos passos de precificação (itens 4-7)"
```

---

## Self-Review

- **Cobertura:** itens 1 (taxa dinâmica → Tasks 1–2), 2 (252 dias → Task 3), 3 (backtest real → Task 4) cobertos; itens 4–7 explicitamente diferidos no backlog (Task 5).
- **Consistência de tipos:** `get_selic_anual()` retorna `float` decimal e é usado como `r=` em `calculate_greeks`/`precificar_bs`; `TRADING_DAYS_PER_YEAR` definido na Task 3 e importado no teste; `filtrar_opcoes_do_ativo(df, ativo_base)` mesma assinatura em serviço e testes.
- **Riscos conhecidos:** APIs de `python-bcb` (série 432, `sgs.get`) e `rb3` (downloader/colunas) podem variar por versão — sinalizado em notas nos Steps para o executor validar contra a versão instalada.
