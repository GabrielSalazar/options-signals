# Camada 1 — Volatilidade Implícita Real — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o rótulo errado "IV" (na verdade HV 20d) por IV implícita real extraída do prêmio de tela, com fallback chain documentada, histórico/IV Rank persistido e um filtro de volatilidade na emissão de sinais operando em shadow mode.

**Architecture:** `backend/domain/options_math.py` ganha `resolver_iv` (fallback chain pura, sem I/O). `backend/services/data_providers.py` ganha dois helpers de leitura de chain (vizinhos de strike e opção ATM). `backend/services/core_engine.py` é atualizado para chamar esses helpers e parar de chamar HV de "IV". Um novo serviço `backend/services/iv_history_service.py` persiste IV ATM diária no Supabase (tabela nova `iv_history`) e calcula IV Rank. `backend/domain/scoring.py` ganha a função de decisão do filtro; o filtro roda em modo `shadow` (loga, não bloqueia) controlado por `CONFIG['iv_filter_mode']`.

**Tech Stack:** Python 3 / FastAPI, pandas/numpy/scipy (Black-Scholes existente), Supabase (Postgres), APScheduler, pytest, Next.js/TypeScript no frontend.

**Spec:** `docs/superpowers/specs/2026-06-26-camada-1-volatilidade-implicita-design.md`

**Pendência manual após o merge:** aplicar as migrações `004_camada1_iv_signals.sql` e `005_iv_history.sql` no Supabase ANTES do deploy (mesmo fluxo das pendentes `002`/`003` — `persist_signals`/`coletar_iv_diaria` logam erro mas não derrubam o processo se as colunas/tabela não existirem).

---

### Task 1: Fallback chain de IV (`resolver_iv`)

**Files:**
- Modify: `backend/domain/options_math.py`
- Test: `tests/test_options_math.py` (criar)

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Testes para resolver_iv — fallback chain de IV implícita (Camada 1.1)."""
import pytest
from backend.domain.options_math import resolver_iv
from backend.domain.greeks import bs_call_price

S, K, T, R, SIGMA = 100.0, 105.0, 30 / 365, 0.135, 0.30


def test_resolver_iv_usa_tela_quando_premio_real_e_valido():
    preco_tela = bs_call_price(S, K, T, R, SIGMA)
    iv, fonte = resolver_iv(preco_tela, S, K, T, "CALL", hv_20d=0.25)
    assert fonte == "tela"
    assert iv == pytest.approx(SIGMA, abs=0.01)


def test_resolver_iv_rejeita_premio_abaixo_do_intrinsico():
    """Prêmio < valor intrínseco é violação de no-arbitrage — cai pro próximo nível."""
    preco_abaixo_intrinsico = 0.01  # CALL ITM (S>K) com prêmio absurdamente baixo
    iv, fonte = resolver_iv(preco_abaixo_intrinsico, S=110, K=100, T=T, tipo="CALL", hv_20d=0.25)
    assert fonte != "tela"


def test_resolver_iv_usa_mediana_dos_vizinhos_sem_preco_de_tela():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25,
                            ivs_strikes_vizinhos=[0.28, 0.32, 0.30])
    assert fonte == "strikes_vizinhos"
    assert iv == pytest.approx(0.30)


def test_resolver_iv_ignora_vizinhos_fora_da_faixa_valida():
    """IVs fora de [0.05, 3.0] (erro de cálculo) são descartadas da mediana."""
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25,
                            ivs_strikes_vizinhos=[0.28, 10.0, 0.32])
    assert fonte == "strikes_vizinhos"
    assert iv == pytest.approx(0.30)  # mediana de [0.28, 0.32], 10.0 descartado


def test_resolver_iv_cai_para_hv_proxy_sem_tela_nem_vizinhos():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25)
    assert fonte == "hv_proxy"
    assert iv == pytest.approx(0.25 * 1.1)


def test_resolver_iv_usa_default_sem_nenhum_dado():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.0)
    assert fonte == "default"
    assert iv == pytest.approx(0.40)
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_options_math.py -v`
Expected: FAIL com `ImportError: cannot import name 'resolver_iv'`

- [ ] **Step 3: Implementar `resolver_iv`**

No topo de `backend/domain/options_math.py`, adicionar o import (a função `implied_volatility` já existe em `greeks.py`):

```python
from backend.domain.greeks import implied_volatility
```

No final do arquivo, adicionar:

```python
def resolver_iv(preco_tela: float | None, S: float, K: float, T: float, tipo: str,
                 hv_20d: float, ivs_strikes_vizinhos: list[float] | None = None) -> tuple[float, str]:
    """
    Fallback chain de IV implícita (Camada 1.1):
      1. tela            — IV implícita do prêmio real, validada contra no-arbitrage.
      2. strikes_vizinhos — mediana da IV implícita dos strikes líquidos vizinhos.
      3. hv_proxy         — HV 20d × 1.1 (prêmio de risco típico).
      4. default          — 0.40 (último recurso).
    Retorna (iv, fonte).
    """
    ivs_strikes_vizinhos = ivs_strikes_vizinhos or []

    if preco_tela and T > 0:
        intrinsico = max(S - K, 0.0) if tipo.upper() == "CALL" else max(K - S, 0.0)
        if preco_tela > intrinsico:
            iv = implied_volatility(S, K, T, preco_tela, tipo, sigma_init=hv_20d or 0.5)
            if 0.05 <= iv <= 3.0:
                return iv, "tela"

    validos = [v for v in ivs_strikes_vizinhos if v and 0.05 <= v <= 3.0]
    if validos:
        return float(np.median(validos)), "strikes_vizinhos"

    if hv_20d and hv_20d > 0:
        return float(hv_20d * 1.1), "hv_proxy"

    return 0.40, "default"
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_options_math.py -v`
Expected: PASS (6 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/options_math.py tests/test_options_math.py
git commit -m "feat(iv): adiciona fallback chain de IV implicita (resolver_iv)"
```

---

### Task 2: Helpers de chain — strikes vizinhos e opção ATM

**Files:**
- Modify: `backend/services/data_providers.py`
- Test: `tests/test_data_providers.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/test_data_providers.py`:

```python
from backend.services import data_providers as dp


def _op(ticker_opcao, tipo, strike, preco, negocios=50):
    # Layout da chain bruta: [ticker, _, tipo, _, _, strike, _, _, preco, negocios]
    return [ticker_opcao, None, tipo, None, None, strike, None, None, preco, negocios]


def test_obter_opcoes_vizinhas_filtra_tipo_vencimento_e_exclui_strike(monkeypatch):
    chain = [
        _op("PETRC405", "CALL", 40.5, 1.20),   # mesmo venc (F=jun), vizinho
        _op("PETRC410", "CALL", 41.0, 1.00),   # strike excluído
        _op("PETRC395", "CALL", 39.5, 1.50),   # mesmo venc, vizinho
        _op("PETRP405", "PUT",  40.5, 0.80),   # tipo errado
        _op("PETRC505", "CALL", 50.5, 0.10),   # outro vencimento (G=jul)
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    vizinhos = dp.obter_opcoes_vizinhas("PETR4", "CALL", strike_alvo=41.0,
                                        mes_v=6, ano_v=2026, excluir_strike=41.0)
    strikes = sorted(v["strike_real"] for v in vizinhos)
    assert strikes == [39.5, 40.5]


def test_obter_opcoes_vizinhas_respeita_limite_n(monkeypatch):
    chain = [_op(f"PETRC{400+i}", "CALL", 40.0 + i, 1.0) for i in range(10)]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    vizinhos = dp.obter_opcoes_vizinhas("PETR4", "CALL", strike_alvo=45.0,
                                        mes_v=6, ano_v=2026, excluir_strike=999.0, n=3)
    assert len(vizinhos) == 3


def test_obter_opcao_atm_acha_strike_mais_proximo_do_spot(monkeypatch):
    chain = [
        _op("PETRC400", "CALL", 40.0, 2.00),
        _op("PETRC410", "CALL", 41.0, 1.50),
        _op("PETRC420", "CALL", 42.0, 1.00),
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    atm = dp.obter_opcao_atm("PETR4", preco_spot=41.2, mes_v=6, ano_v=2026, tipo_alvo="CALL")
    assert atm["strike_real"] == 41.0


def test_obter_opcao_atm_retorna_none_sem_chain(monkeypatch):
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: [])
    assert dp.obter_opcao_atm("PETR4", preco_spot=41.2, mes_v=6, ano_v=2026) is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_data_providers.py -v -k "vizinhas or opcao_atm"`
Expected: FAIL com `AttributeError: module ... has no attribute 'obter_opcoes_vizinhas'`

- [ ] **Step 3: Implementar os helpers**

Em `backend/services/data_providers.py`, adicionar o import no topo (junto dos demais imports do módulo):

```python
from backend.domain.options_math import decodificar_opcao_b3
```

E, após `get_real_options_from_opcoes_net`, adicionar:

```python
def obter_opcoes_vizinhas(ticker: str, tipo_alvo: str, strike_alvo: float,
                           mes_v: int, ano_v: int, excluir_strike: float,
                           n: int = 4) -> List[Dict]:
    """
    Busca até `n` opções líquidas do mesmo tipo e vencimento, mais próximas de
    strike_alvo (excluindo o próprio strike). Usado no fallback chain de IV
    (Camada 1.1) quando não há prêmio de tela para o strike de referência.
    """
    from backend.core.config import CONFIG
    min_neg = CONFIG.get("min_negocios_opcao", 0)

    chain = _fetch_chain(ticker)
    candidatos = []

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo != tipo_alvo:
            continue
        if op_negocios is None or op_preco is None or op_preco <= 0.01:
            continue
        if op_negocios < min_neg:
            continue
        if abs(op_strike - excluir_strike) < 0.001:
            continue

        decoded = decodificar_opcao_b3(op_ticker)
        if not decoded or decoded.get("mes_venc") != mes_v or decoded.get("ano_venc") != ano_v:
            continue

        candidatos.append({
            "ticker_opcao": op_ticker,
            "strike_real":  op_strike,
            "preco_tela":   op_preco,
        })

    candidatos.sort(key=lambda c: abs(c["strike_real"] - strike_alvo))
    return candidatos[:n]


def obter_opcao_atm(ticker: str, preco_spot: float, mes_v: int, ano_v: int,
                     tipo_alvo: str = "CALL") -> Optional[Dict]:
    """
    Busca a opção líquida mais próxima do spot (ATM) do tipo/vencimento dados.
    Usado pelo job diário de histórico de IV (Camada 1.2).
    """
    from backend.core.config import CONFIG
    min_neg = CONFIG.get("min_negocios_opcao", 0)

    chain = _fetch_chain(ticker)
    melhor = None
    menor_distancia = float("inf")

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo != tipo_alvo:
            continue
        if op_negocios is None or op_preco is None or op_preco <= 0.01:
            continue
        if op_negocios < min_neg:
            continue

        decoded = decodificar_opcao_b3(op_ticker)
        if not decoded or decoded.get("mes_venc") != mes_v or decoded.get("ano_venc") != ano_v:
            continue

        distancia = abs(op_strike - preco_spot)
        if distancia < menor_distancia:
            menor_distancia = distancia
            melhor = {"ticker_opcao": op_ticker, "strike_real": op_strike, "preco_tela": op_preco}

    return melhor
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_data_providers.py -v -k "vizinhas or opcao_atm"`
Expected: PASS (4 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/services/data_providers.py tests/test_data_providers.py
git commit -m "feat(iv): adiciona helpers de chain para strikes vizinhos e opcao ATM"
```

---

### Task 3: Rename `iv_hist`→`hv_20d` e integração do `resolver_iv` no core_engine

**Files:**
- Modify: `backend/services/core_engine.py:16-19` (imports), `:215-287` (`_montar_estrutura_opcao`), `:317-330` (`_montar_sinal`)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/test_core_engine.py` (ajustar o import conforme o padrão já usado no arquivo, tipicamente `from backend.services import core_engine as ce`):

```python
def test_montar_estrutura_opcao_expoe_hv_20d_iv_impl_e_fonte(monkeypatch):
    import pandas as pd
    from backend.services import core_engine as ce

    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net", lambda *a, **k: None)
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas", lambda *a, **k: [])

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", 100.0, "CALL", df, "1d", verbose=False)

    assert estrutura is not None
    assert "hv_20d" in estrutura
    assert "iv" not in estrutura          # chave antiga não deve mais existir
    assert estrutura["iv_source"] == "hv_proxy"   # sem preço de tela nem vizinhos
    assert estrutura["iv_impl"] == pytest.approx(estrutura["hv_20d"] * 1.1)


def test_montar_estrutura_opcao_usa_iv_de_tela_quando_disponivel(monkeypatch):
    import pandas as pd
    from backend.services import core_engine as ce
    from backend.domain.greeks import bs_call_price

    preco, strike, dte = 100.0, 105.0, 20
    T = dte / 252
    preco_tela_real = bs_call_price(preco, strike, T, sigma=0.35)

    monkeypatch.setattr(ce, "mes_vencimento_ideal", lambda: (6, 2026, dte))
    monkeypatch.setattr(ce, "get_real_options_from_opcoes_net",
                        lambda *a, **k: {"strike_real": strike, "preco_tela": preco_tela_real,
                                         "ticker_opcao": "PETRC405"})
    monkeypatch.setattr(ce, "obter_opcoes_vizinhas", lambda *a, **k: [])

    df = pd.DataFrame({"Close": [100.0] * 25})
    estrutura = ce._montar_estrutura_opcao("PETR4", preco, "CALL", df, "1d", verbose=False)

    assert estrutura["iv_source"] == "tela"
    assert estrutura["iv_impl"] == pytest.approx(0.35, abs=0.01)
    assert estrutura["iv_mercado"] == pytest.approx(0.35, abs=0.01)
```

(Adicionar `import pytest` no topo do arquivo de teste, se ainda não houver.)

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_core_engine.py -v -k "hv_20d or iv_de_tela"`
Expected: FAIL — `estrutura["hv_20d"]` levanta `KeyError` (a chave ainda se chama `"iv"`)

- [ ] **Step 3: Atualizar imports e `_montar_estrutura_opcao`**

Em `backend/services/core_engine.py:16-17`, trocar:

```python
from backend.domain.options_math import mes_vencimento_ideal, estimar_iv_historica, estimar_premio_otm
from backend.services.data_providers import get_real_options_from_opcoes_net, fetch_brapi_historical
```

por:

```python
from backend.domain.options_math import mes_vencimento_ideal, estimar_iv_historica, estimar_premio_otm, resolver_iv
from backend.services.data_providers import get_real_options_from_opcoes_net, fetch_brapi_historical, obter_opcoes_vizinhas
```

Em `_montar_estrutura_opcao` (linhas ~225-287), substituir o trecho atual:

```python
    mes_v, ano_v, dte = mes_vencimento_ideal()
    iv           = estimar_iv_historica(df, interval=interval)
    premio_est   = estimar_premio_otm(preco, strike_ref, dte, iv, tipo_sinal)

    # --- INTEGRAÇÃO COM DADOS REAIS (opcoes.net.br) ---
    opcao_real = get_real_options_from_opcoes_net(ticker_base, tipo_sinal, strike_ref)
    if opcao_real:
        strike_ref = opcao_real["strike_real"]
        preco_tela = opcao_real["preco_tela"]
        ticker_opcao = opcao_real["ticker_opcao"]
    else:
        preco_tela = None
        ticker_opcao = "N/A (S/ Liquidez)"

    # Greeks: se há preço REAL de tela, derivamos IV de mercado e usamos no BS
    T = max(dte, 1) / 252
    iv_mercado = None
    sigma_para_greeks = iv
    if preco_tela:
        try:
            iv_mercado = implied_volatility(
                preco, strike_ref, T, preco_tela, tipo_sinal, sigma_init=iv,
            )
            if 0.05 <= iv_mercado <= 3.0:
                sigma_para_greeks = iv_mercado
        except Exception:
            iv_mercado = None
    greeks = calculate_greeks(preco, strike_ref, T, sigma_para_greeks, tipo_sinal)
```

por:

```python
    mes_v, ano_v, dte = mes_vencimento_ideal()
    hv_20d       = estimar_iv_historica(df, interval=interval)
    premio_est   = estimar_premio_otm(preco, strike_ref, dte, hv_20d, tipo_sinal)

    # --- INTEGRAÇÃO COM DADOS REAIS (opcoes.net.br) ---
    opcao_real = get_real_options_from_opcoes_net(ticker_base, tipo_sinal, strike_ref)
    if opcao_real:
        strike_ref = opcao_real["strike_real"]
        preco_tela = opcao_real["preco_tela"]
        ticker_opcao = opcao_real["ticker_opcao"]
    else:
        preco_tela = None
        ticker_opcao = "N/A (S/ Liquidez)"

    T = max(dte, 1) / 252

    # Fallback chain de IV implícita (Camada 1.1): tela -> strikes vizinhos -> HV proxy -> default
    ivs_vizinhos = []
    if preco_tela:
        for vizinho in obter_opcoes_vizinhas(ticker_base, tipo_sinal, strike_ref, mes_v, ano_v, strike_ref):
            intrinsico = (max(preco - vizinho["strike_real"], 0.0) if tipo_sinal == "CALL"
                         else max(vizinho["strike_real"] - preco, 0.0))
            if vizinho["preco_tela"] > intrinsico:
                try:
                    ivs_vizinhos.append(implied_volatility(
                        preco, vizinho["strike_real"], T, vizinho["preco_tela"],
                        tipo_sinal, sigma_init=hv_20d,
                    ))
                except Exception:
                    pass

    iv_impl, iv_source = resolver_iv(preco_tela, preco, strike_ref, T, tipo_sinal, hv_20d, ivs_vizinhos)
    iv_mercado = iv_impl if iv_source == "tela" else None
    greeks = calculate_greeks(preco, strike_ref, T, iv_impl, tipo_sinal)
```

E no `return` da função (linhas ~278-287), trocar:

```python
    return {
        "dist_otm": dist_otm, "strike_ref": strike_ref, "iv": iv, "iv_mercado": iv_mercado,
        "dte": dte, "mes_v": mes_v, "ano_v": ano_v, "premio_est": premio_est,
```

por:

```python
    return {
        "dist_otm": dist_otm, "strike_ref": strike_ref, "hv_20d": hv_20d,
        "iv_impl": iv_impl, "iv_source": iv_source, "iv_mercado": iv_mercado,
        "dte": dte, "mes_v": mes_v, "ano_v": ano_v, "premio_est": premio_est,
```

- [ ] **Step 4: Atualizar `_montar_sinal`**

Em `_montar_sinal` (linhas ~317-330), trocar:

```python
    iv = estrutura["iv"]
    iv_mercado = estrutura["iv_mercado"]
    return {
        "emoji":        emoji,
        "ticker":       ticker_base,
        "nome":         nome,
        "tipo_sinal":   tipo_sinal,
        "direcao":      direcao_label,
        "preco_acao":   preco,
        "ticker_opcao": estrutura["ticker_opcao"],
        "strike_ref":   estrutura["strike_ref"],
        "dist_otm_pct": estrutura["dist_otm"] * 100,
        "iv_hist":      round(iv * 100, 1),
        "iv_mercado":   round(iv_mercado * 100, 1) if iv_mercado else None,
```

por:

```python
    hv_20d = estrutura["hv_20d"]
    iv_mercado = estrutura["iv_mercado"]
    return {
        "emoji":        emoji,
        "ticker":       ticker_base,
        "nome":         nome,
        "tipo_sinal":   tipo_sinal,
        "direcao":      direcao_label,
        "preco_acao":   preco,
        "ticker_opcao": estrutura["ticker_opcao"],
        "strike_ref":   estrutura["strike_ref"],
        "dist_otm_pct": estrutura["dist_otm"] * 100,
        "hv_20d":       round(hv_20d * 100, 1),
        "iv_mercado":   round(iv_mercado * 100, 1) if iv_mercado else None,
        "iv_impl":      round(estrutura["iv_impl"] * 100, 1),
        "iv_source":    estrutura["iv_source"],
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_core_engine.py -v -k "hv_20d or iv_de_tela"`
Expected: PASS (2 testes)

- [ ] **Step 6: Rodar a suíte completa de core_engine (garantir que nada quebrou)**

Run: `pytest tests/test_core_engine.py -v`
Expected: PASS em todos os testes

- [ ] **Step 7: Commit**

```bash
git add backend/services/core_engine.py tests/test_core_engine.py
git commit -m "refactor(iv): renomeia iv_hist para hv_20d e integra fallback chain no core_engine"
```

---

### Task 4: Propagar o rename para persistência, outcome e Telegram

**Files:**
- Modify: `backend/services/signal_service.py:97`, `backend/services/outcome_service.py:21`, `backend/domain/outcome.py:33`, `backend/services/telegram_service.py:94`
- Test: `tests/test_outcome.py:15`, `tests/test_outcome_service.py:38`, `tests/test_telegram.py:30`

- [ ] **Step 1: Atualizar os testes existentes (eles devem passar a usar `hv_20d`)**

Em `tests/test_outcome.py:15` e `tests/test_outcome_service.py:38`, trocar:

```python
"iv_hist": 40.0, "iv_mercado": None, "dte": 20, "preco_acao": 100.0,
```

por:

```python
"hv_20d": 40.0, "iv_mercado": None, "dte": 20, "preco_acao": 100.0,
```

Em `tests/test_telegram.py:30`, trocar:

```python
"iv_hist": 35.0, "dte": 30, "entrada_min": 0.5, "entrada_max": 0.6,
```

por:

```python
"hv_20d": 35.0, "dte": 30, "entrada_min": 0.5, "entrada_max": 0.6,
```

- [ ] **Step 2: Rodar os testes e confirmar que falham (asserts ainda batem na string antiga)**

Run: `pytest tests/test_telegram.py::test_formatter_separa_score_tecnico_e_bonus -v`
Expected: PASS (este teste não afirma sobre IV) — mas a etapa seguinte vai expor a inconsistência no `telegram_service.py`. Confirme com:

Run: `pytest tests/test_outcome.py tests/test_outcome_service.py tests/test_telegram.py -v`
Expected: os testes que dependem de `iv_hist` no código de produção (outcome.py, outcome_service.py, telegram_service.py) ainda funcionam porque o dict de teste tinha as duas formas antes — após a troca acima, **PASS continua** (o código de produção ainda lê `iv_hist`, que não existe mais no dict de teste) **deve gerar comportamento de fallback (`40.0` default)** nos testes de outcome. Rode e confirme visualmente que `iv_pct` cai no default 40.0 antes de seguir.

- [ ] **Step 3: Atualizar o código de produção**

Em `backend/services/signal_service.py:97`, trocar:

```python
            "iv_hist":       s.get("iv_hist"),
```

por:

```python
            "hv_20d":        s.get("hv_20d"),
            "iv_impl":       s.get("iv_impl"),
            "iv_source":     s.get("iv_source"),
```

Em `backend/services/outcome_service.py:21`, trocar:

```python
           "alvo_final, stop, iv_hist, iv_mercado, dte, preco_acao, score, "
```

por:

```python
           "alvo_final, stop, hv_20d, iv_mercado, dte, preco_acao, score, "
```

Em `backend/domain/outcome.py:33`, trocar:

```python
    iv_pct = sinal.get("iv_mercado") or sinal.get("iv_hist") or 40.0
```

por:

```python
    iv_pct = sinal.get("iv_mercado") or sinal.get("hv_20d") or 40.0
```

Em `backend/services/telegram_service.py:94`, trocar:

```python
        f"*IV Hist:* {sinal.get('iv_hist')}% | *DTE:* {sinal.get('dte')} du\n\n"
```

por:

```python
        f"*HV 20d:* {sinal.get('hv_20d')}% | *DTE:* {sinal.get('dte')} du\n\n"
```

- [ ] **Step 4: Rodar a suíte completa relacionada e confirmar que passa**

Run: `pytest tests/test_outcome.py tests/test_outcome_service.py tests/test_telegram.py tests/test_signal_service.py -v`
Expected: PASS em todos

- [ ] **Step 5: Commit**

```bash
git add backend/services/signal_service.py backend/services/outcome_service.py backend/domain/outcome.py backend/services/telegram_service.py tests/test_outcome.py tests/test_outcome_service.py tests/test_telegram.py
git commit -m "refactor(iv): propaga rename iv_hist->hv_20d para persistencia, outcome e telegram"
```

---

### Task 5: Migration 004 — colunas de IV na tabela `signals`

**Files:**
- Create: `supabase/migrations/004_camada1_iv_signals.sql`

- [ ] **Step 1: Criar o arquivo da migração**

```sql
-- ============================================================
-- Migration 004: Camada 1 (IV) — rename + novas colunas em `signals`
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d;

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS iv_impl          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_source        TEXT,
  ADD COLUMN IF NOT EXISTS iv_rank          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_premium       NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_filter_decisao TEXT;
```

- [ ] **Step 2: Não aplicar agora — só ao final do plano**

Esta migração só deve ser aplicada manualmente no Supabase Dashboard **depois** que todo o código desta Camada 1 estiver mergeado (mesma disciplina das migrações 002/003 pendentes). Não há teste automatizado de schema; o teste de regressão é a suíte pytest completa passando com o rename já feito no Task 3/4.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/004_camada1_iv_signals.sql
git commit -m "chore(db): adiciona migration 004 (rename iv_hist + colunas de IV)"
```

---

### Task 6: Frontend — rename `iv_hist`→`hv_20d`

**Files:**
- Modify: `src/types/signals.ts:11`, `src/components/SignalCard.tsx:137`

- [ ] **Step 1: Atualizar o tipo**

Em `src/types/signals.ts:11`, trocar:

```typescript
  iv_hist: number
```

por:

```typescript
  hv_20d: number
```

- [ ] **Step 2: Atualizar o componente**

Em `src/components/SignalCard.tsx:137`, localizar o bloco que renderiza o label (contexto: procurar por `iv_hist` no arquivo) e trocar a referência `signal.iv_hist` por `signal.hv_20d`, e o texto do label de "IV Hist" (ou equivalente) para "HV 20d".

- [ ] **Step 3: Verificar tipos e build do frontend**

Run: `npm run build` (ou `npx tsc --noEmit`, conforme o script disponível no `package.json`)
Expected: sem erros de tipo relacionados a `iv_hist`/`hv_20d`

- [ ] **Step 4: Commit**

```bash
git add src/types/signals.ts src/components/SignalCard.tsx
git commit -m "refactor(frontend): renomeia iv_hist para hv_20d no SignalCard"
```

---

### Task 7: Migration 005 — tabela `iv_history`

**Files:**
- Create: `supabase/migrations/005_iv_history.sql`

- [ ] **Step 1: Criar o arquivo da migração**

```sql
-- ============================================================
-- Migration 005: Camada 1.2 — histórico diário de IV / IV Rank
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS iv_history (
    id          BIGSERIAL PRIMARY KEY,
    ticker      TEXT NOT NULL,
    data        DATE NOT NULL,
    iv_atm      NUMERIC,
    hv_20d      NUMERIC,
    iv_premium  NUMERIC,
    fonte       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (ticker, data)
);

CREATE INDEX IF NOT EXISTS idx_iv_history_ticker_data
  ON iv_history (ticker, data DESC);
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/005_iv_history.sql
git commit -m "chore(db): adiciona migration 005 (tabela iv_history)"
```

---

### Task 8: `iv_history_service.py` — coleta diária e IV Rank

**Files:**
- Create: `backend/services/iv_history_service.py`
- Test: `tests/test_iv_history_service.py`

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Testes do iv_history_service — coleta diária de IV ATM e cálculo de IV Rank."""
import pandas as pd
from backend.services import iv_history_service as ihs


class _FakeQuery:
    def __init__(self, store, table_name):
        self._store = store
        self._table = table_name
        self._filtros = {}

    def select(self, *a, **k): return self
    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self
    def order(self, *a, **k): return self
    def limit(self, n):
        self._n = n
        return self
    def upsert(self, row, on_conflict=None):
        self._store.append(row)
        return self
    def execute(self):
        if self._table == "iv_history" and self._filtros:
            linhas = [r for r in self._store if r.get("ticker") == self._filtros.get("ticker")]
            linhas = sorted(linhas, key=lambda r: r["data"], reverse=True)
            return type("R", (), {"data": linhas[: getattr(self, "_n", len(linhas))]})()
        return type("R", (), {"data": list(self._store)})()


class _FakeSupabase:
    def __init__(self):
        self.store = []

    def table(self, nome):
        return _FakeQuery(self.store, nome)


def _df_constante(preco: float, n: int = 25) -> pd.DataFrame:
    return pd.DataFrame({"Close": [preco] * n})


def test_coletar_iv_diaria_sem_supabase_retorna_zero(monkeypatch):
    monkeypatch.setattr(ihs, "get_supabase", lambda: None)
    assert ihs.coletar_iv_diaria({"PETR4.SA": "Petrobras"}) == 0


def test_coletar_iv_diaria_persiste_quando_ha_opcao_atm(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(ihs, "get_supabase", lambda: fake)
    monkeypatch.setattr(ihs, "fetch_brapi_historical", lambda *a, **k: _df_constante(40.0))
    monkeypatch.setattr(ihs, "obter_opcao_atm",
                        lambda *a, **k: {"strike_real": 40.0, "preco_tela": 1.50,
                                         "ticker_opcao": "PETRC400"})
    persistidos = ihs.coletar_iv_diaria({"PETR4.SA": "Petrobras"})
    assert persistidos == 1
    assert fake.store[0]["ticker"] == "PETR4"
    assert fake.store[0]["fonte"] == "tela"


def test_coletar_iv_diaria_pula_ticker_sem_opcao_atm(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(ihs, "get_supabase", lambda: fake)
    monkeypatch.setattr(ihs, "fetch_brapi_historical", lambda *a, **k: _df_constante(40.0))
    monkeypatch.setattr(ihs, "obter_opcao_atm", lambda *a, **k: None)
    persistidos = ihs.coletar_iv_diaria({"PETR4.SA": "Petrobras"})
    assert persistidos == 0
    assert fake.store == []


def test_coletar_iv_diaria_pula_ticker_com_erro_sem_derrubar_job(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(ihs, "get_supabase", lambda: fake)

    def _fetch_com_erro(ticker, *a, **k):
        if ticker == "QUEBRA4.SA":
            raise RuntimeError("falha de rede")
        return _df_constante(40.0)

    monkeypatch.setattr(ihs, "fetch_brapi_historical", _fetch_com_erro)
    monkeypatch.setattr(ihs, "obter_opcao_atm",
                        lambda *a, **k: {"strike_real": 40.0, "preco_tela": 1.50,
                                         "ticker_opcao": "PETRC400"})
    persistidos = ihs.coletar_iv_diaria({"QUEBRA4.SA": "Quebra", "PETR4.SA": "Petrobras"})
    assert persistidos == 1  # só PETR4 foi persistido; QUEBRA4 não derrubou o job


def test_iv_rank_retorna_nao_confiavel_sem_supabase(monkeypatch):
    monkeypatch.setattr(ihs, "get_supabase", lambda: None)
    r = ihs.iv_rank("PETR4")
    assert r == {"iv_rank": None, "iv_premium": None, "confiavel": False}


def test_iv_rank_usa_proxy_com_historico_curto(monkeypatch):
    fake = _FakeSupabase()
    fake.store = [
        {"ticker": "PETR4", "data": "2026-06-20", "iv_atm": 0.30, "iv_premium": 1.1},
        {"ticker": "PETR4", "data": "2026-06-19", "iv_atm": 0.28, "iv_premium": 1.0},
    ]
    monkeypatch.setattr(ihs, "get_supabase", lambda: fake)
    r = ihs.iv_rank("PETR4")
    assert r["confiavel"] is False
    assert r["iv_rank"] is None
    assert r["iv_premium"] == 1.1


def test_iv_rank_calcula_percentil_com_historico_suficiente(monkeypatch):
    fake = _FakeSupabase()
    fake.store = [
        {"ticker": "PETR4", "data": f"2026-04-{i:02d}" if i <= 30 else f"2026-05-{i-30:02d}",
         "iv_atm": 0.20 + (i * 0.01), "iv_premium": 1.0}
        for i in range(1, 61)
    ]
    monkeypatch.setattr(ihs, "get_supabase", lambda: fake)
    r = ihs.iv_rank("PETR4")
    assert r["confiavel"] is True
    assert r["iv_rank"] == 100.0  # a linha mais recente (i=60) tem a maior iv_atm
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_iv_history_service.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'backend.services.iv_history_service'`

- [ ] **Step 3: Implementar o serviço**

Criar `backend/services/iv_history_service.py`:

```python
"""Histórico diário de IV ATM e cálculo de IV Rank (Camada 1.2)."""
import logging
from datetime import datetime, timezone

from backend.domain.options_math import mes_vencimento_ideal, estimar_iv_historica, resolver_iv
from backend.services.data_providers import fetch_brapi_historical, obter_opcao_atm
from backend.services.ticker_loader import carregar_tickers_b3
from backend.services.supabase_client import get_supabase

logger = logging.getLogger("b3_api")


def _iv_atm_do_ticker(ticker_base: str, df) -> tuple:
    """Retorna (iv_atm | None, hv_20d, fonte) para um ticker."""
    hv_20d = estimar_iv_historica(df)
    preco = float(df["Close"].iloc[-1])
    mes_v, ano_v, dte = mes_vencimento_ideal()
    T = max(dte, 1) / 252

    opcao = obter_opcao_atm(ticker_base, preco, mes_v, ano_v, tipo_alvo="CALL")
    if not opcao:
        return None, hv_20d, "sem_dado"

    iv_atm, fonte = resolver_iv(opcao["preco_tela"], preco, opcao["strike_real"], T, "CALL", hv_20d)
    if fonte != "tela":
        return None, hv_20d, "sem_dado"
    return iv_atm, hv_20d, "tela"


def coletar_iv_diaria(tickers: dict | None = None) -> int:
    """
    Job diário (pós-fechamento): persiste iv_atm/hv_20d/iv_premium por ticker
    do universo líquido em `iv_history`. Falha de um ticker não derruba o job.
    Retorna o nº de tickers persistidos com sucesso.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — histórico de IV não coletado")
        return 0

    if tickers is None:
        tickers = carregar_tickers_b3()

    hoje = datetime.now(timezone.utc).date().isoformat()
    persistidos = 0
    for ticker, _nome in tickers.items():
        ticker_base = ticker.replace(".SA", "")
        try:
            df = fetch_brapi_historical(ticker, range_="3mo", interval="1d")
            if df is None or df.empty:
                continue
            iv_atm, hv_20d, fonte = _iv_atm_do_ticker(ticker_base, df)
            if iv_atm is None:
                continue
            iv_premium = (iv_atm / hv_20d) if hv_20d > 0 else None
            supabase.table("iv_history").upsert({
                "ticker": ticker_base,
                "data": hoje,
                "iv_atm": round(iv_atm, 4),
                "hv_20d": round(hv_20d, 4),
                "iv_premium": round(iv_premium, 4) if iv_premium else None,
                "fonte": fonte,
            }, on_conflict="ticker,data").execute()
            persistidos += 1
        except Exception as e:
            logger.warning(f"Erro ao coletar IV de {ticker_base}: {e}")

    logger.info(f"Histórico de IV coletado — {persistidos}/{len(tickers)} tickers")
    return persistidos


def iv_rank(ticker_base: str) -> dict:
    """Retorna {'iv_rank': float|None, 'iv_premium': float|None, 'confiavel': bool}.
    'confiavel' exige >=60 dias úteis de histórico; caso contrário usa o proxy iv_premium."""
    supabase = get_supabase()
    if not supabase:
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    try:
        res = (supabase.table("iv_history")
               .select("iv_atm, iv_premium, data")
               .eq("ticker", ticker_base)
               .order("data", desc=True)
               .limit(252)
               .execute())
        rows = res.data or []
    except Exception as e:
        logger.warning(f"Erro ao consultar iv_history de {ticker_base}: {e}")
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    if not rows:
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    atual = rows[0]
    ivs = [r["iv_atm"] for r in rows if r.get("iv_atm") is not None]
    confiavel = len(ivs) >= 60

    if confiavel and atual.get("iv_atm") is not None:
        menor, maior = min(ivs), max(ivs)
        rank = ((atual["iv_atm"] - menor) / (maior - menor) * 100) if maior > menor else 50.0
        return {"iv_rank": round(rank, 1), "iv_premium": atual.get("iv_premium"), "confiavel": True}

    return {"iv_rank": None, "iv_premium": atual.get("iv_premium"), "confiavel": False}
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_iv_history_service.py -v`
Expected: PASS (7 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/services/iv_history_service.py tests/test_iv_history_service.py
git commit -m "feat(iv): adiciona iv_history_service (coleta diaria e IV Rank)"
```

---

### Task 9: Job no scheduler

**Files:**
- Modify: `backend/services/scheduler.py`
- Test: `tests/test_scheduler.py` (criar)

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Teste de wiring do scheduler — confirma que o job de IV está registrado."""
from backend.services import scheduler as sch


def test_start_registra_job_iv_history(monkeypatch):
    monkeypatch.setattr(sch.scheduler, "start", lambda: None)
    ids_antes = {j.id for j in sch.scheduler.get_jobs()}
    sch.start()
    ids_depois = {j.id for j in sch.scheduler.get_jobs()}
    assert "iv_history_job" in ids_depois - ids_antes or "iv_history_job" in ids_depois
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL — `"iv_history_job" not in ids_depois`

- [ ] **Step 3: Registrar o job**

Em `backend/services/scheduler.py`, atualizar o import:

```python
from backend.services.signal_service import run_scan, cleanup_old_signals
from backend.services.iv_history_service import coletar_iv_diaria
```

E em `start()`, após o `cleanup_job`, adicionar:

```python
    scheduler.add_job(
        coletar_iv_diaria,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
        id="iv_history_job",
        name="Coleta diaria de IV ATM (pos-fechamento)",
        replace_existing=True,
        max_instances=1,
    )
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/scheduler.py tests/test_scheduler.py
git commit -m "feat(iv): agenda job diario de coleta de IV (pos-fechamento, 18h BRT)"
```

---

### Task 10: Filtro de volatilidade — decisão (`avaliar_filtro_iv`)

**Files:**
- Modify: `backend/domain/scoring.py`, `backend/core/config.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/test_scoring.py`:

```python
from backend.domain.scoring import avaliar_filtro_iv


def test_avaliar_filtro_iv_normal_com_rank_baixo():
    r = avaliar_filtro_iv(iv_rank=30, iv_premium=None, iv_rank_confiavel=True, score_tecnico=5)
    assert r["decisao"] == "normal"


def test_avaliar_filtro_iv_exige_score_alto_na_faixa_media():
    r = avaliar_filtro_iv(iv_rank=60, iv_premium=None, iv_rank_confiavel=True, score_tecnico=5)
    assert r["decisao"] == "exige_score_7"


def test_avaliar_filtro_iv_normal_na_faixa_media_se_score_compensa():
    r = avaliar_filtro_iv(iv_rank=60, iv_premium=None, iv_rank_confiavel=True, score_tecnico=8)
    assert r["decisao"] == "normal"


def test_avaliar_filtro_iv_bloqueia_rank_alto():
    r = avaliar_filtro_iv(iv_rank=80, iv_premium=None, iv_rank_confiavel=True, score_tecnico=9)
    assert r["decisao"] == "bloquear"


def test_avaliar_filtro_iv_usa_proxy_premium_sem_rank_confiavel():
    r = avaliar_filtro_iv(iv_rank=None, iv_premium=1.6, iv_rank_confiavel=False, score_tecnico=9)
    assert r["decisao"] == "bloquear"


def test_avaliar_filtro_iv_normal_sem_nenhum_dado():
    r = avaliar_filtro_iv(iv_rank=None, iv_premium=None, iv_rank_confiavel=False, score_tecnico=5)
    assert r["decisao"] == "normal"
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_scoring.py -v -k avaliar_filtro_iv`
Expected: FAIL com `ImportError: cannot import name 'avaliar_filtro_iv'`

- [ ] **Step 3: Implementar a função**

Em `backend/domain/scoring.py`, adicionar ao final do arquivo:

```python
def avaliar_filtro_iv(iv_rank: float | None, iv_premium: float | None,
                       iv_rank_confiavel: bool, score_tecnico: int) -> dict:
    """
    Decide o filtro de volatilidade da Camada 1.3:
      IV Rank < 50 (ou premium < 1.2)  -> normal
      IV Rank 50-75 (ou premium 1.2-1.5) -> exige score_tecnico >= 7
      IV Rank > 75 (ou premium > 1.5)  -> bloquear
    Usa iv_rank quando confiável (>=60 du de histórico); senão cai no proxy iv_premium.
    Retorna {"decisao": str, "motivo": str}.
    """
    if iv_rank_confiavel and iv_rank is not None:
        cara, media = iv_rank > 75, iv_rank > 50
    elif iv_premium is not None:
        cara, media = iv_premium > 1.5, iv_premium > 1.2
    else:
        return {"decisao": "normal", "motivo": "sem dado de IV — filtro inerte"}

    if cara:
        return {"decisao": "bloquear", "motivo": "IV cara — compra a seco bloqueada"}
    if media:
        if score_tecnico >= 7:
            return {"decisao": "normal", "motivo": "IV moderada, mas score tecnico compensa"}
        return {"decisao": "exige_score_7", "motivo": "IV moderada — exige score tecnico >= 7"}
    return {"decisao": "normal", "motivo": "IV normal"}
```

Em `backend/core/config.py`, no `CONFIG`, adicionar logo após `"min_score_ponderado": 60,`:

```python
    "iv_filter_mode":       "shadow",   # "shadow" (loga decisao sem filtrar) | "ativo" (filtra de fato) — Camada 1.3
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_scoring.py -v -k avaliar_filtro_iv`
Expected: PASS (6 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/scoring.py backend/core/config.py tests/test_scoring.py
git commit -m "feat(iv): adiciona avaliar_filtro_iv e flag iv_filter_mode (shadow por padrao)"
```

---

### Task 11: Wiring do filtro de IV em `analisar_ativo` (shadow mode)

**Files:**
- Modify: `backend/services/core_engine.py:19` (import), `:418-428` (`analisar_ativo`), `:330-357` (`_montar_sinal` — campos novos)
- Test: `tests/test_core_engine.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar a `tests/test_core_engine.py`, reaproveitando `_make_df` e `_relax_and_mock` já definidos no topo do arquivo:

```python
def test_analisar_ativo_shadow_mode_nao_bloqueia_mesmo_com_filtro_indicando_bloqueio(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "shadow")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is not None
    assert s["iv_filter_decisao"] == "bloquear"


def test_analisar_ativo_modo_ativo_bloqueia_quando_filtro_indica_bloqueio(monkeypatch):
    _relax_and_mock(monkeypatch)
    monkeypatch.setitem(core_engine.CONFIG, "iv_filter_mode", "ativo")
    monkeypatch.setattr(core_engine, "obter_iv_rank",
                        lambda ticker_base: {"iv_rank": 90, "iv_premium": None, "confiavel": True})
    df = _make_df(0)

    s = core_engine.analisar_ativo("TESTE3", "Teste SA", df_provided=df, indicators_calculated=True)

    assert s is None
```

(`_relax_and_mock` já mocka `get_real_options_from_opcoes_net` para retornar `None`, então não há `preco_tela` e `obter_opcoes_vizinhas` nem chega a ser chamado nesse caminho — coerente com o Task 3.)

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_core_engine.py -v -k "shadow_mode or modo_ativo"`
Expected: FAIL com `AttributeError: module ... has no attribute 'obter_iv_rank'`

- [ ] **Step 3: Implementar o wiring**

Em `backend/services/core_engine.py:19`, trocar:

```python
from backend.domain.scoring import score_ponderado
```

por:

```python
from backend.domain.scoring import score_ponderado, avaliar_filtro_iv
from backend.services.iv_history_service import iv_rank as obter_iv_rank
```

Em `analisar_ativo` (linhas ~418-428), após o bloco que monta a `estrutura` e antes do `return _montar_sinal(...)`:

```python
        # ── ESTRUTURA DA OPÇÃO ────────────────────────────────────────────
        estrutura = _montar_estrutura_opcao(ticker_base, preco, tipo_sinal, df, interval, verbose)
        if estrutura is None:
            return None

        # ── FILTRO DE VOLATILIDADE (Camada 1.3 — shadow mode por padrão) ──
        rank_info = obter_iv_rank(ticker_base)
        filtro = avaliar_filtro_iv(rank_info["iv_rank"], rank_info["iv_premium"],
                                   rank_info["confiavel"], score)
        estrutura["iv_rank"] = rank_info["iv_rank"]
        estrutura["iv_premium"] = rank_info["iv_premium"]
        estrutura["iv_filter_decisao"] = filtro["decisao"]

        if CONFIG.get("iv_filter_mode") == "ativo":
            if filtro["decisao"] == "bloquear":
                if verbose:
                    logger.info(f"🚫 {ticker_base}: filtro IV bloqueou emissão ({filtro['motivo']})")
                return None
            if filtro["decisao"] == "exige_score_7" and score < 7:
                if verbose:
                    logger.info(f"🚫 {ticker_base}: filtro IV exige score>=7, atual={score} ({filtro['motivo']})")
                return None
        elif filtro["decisao"] != "normal" and verbose:
            logger.info(f"ℹ {ticker_base}: filtro IV (shadow) indicaria '{filtro['decisao']}' — {filtro['motivo']}")

        if df_provided is None:
            registrar_sinal(ticker_base, tipo_sinal, score)
```

E em `_montar_sinal` (linhas ~330-357), no dict de retorno, adicionar (junto dos demais campos de `estrutura`):

```python
        "iv_rank":      estrutura.get("iv_rank"),
        "iv_premium":   estrutura.get("iv_premium"),
        "iv_filter_decisao": estrutura.get("iv_filter_decisao"),
```

- [ ] **Step 4: Persistir os novos campos no Supabase**

Em `backend/services/signal_service.py:97` (já editado no Task 4), adicionar mais 3 chaves ao dict `rows.append({...})`:

```python
            "iv_rank":       s.get("iv_rank"),
            "iv_premium":    s.get("iv_premium"),
            "iv_filter_decisao": s.get("iv_filter_decisao"),
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_core_engine.py -v -k "shadow_mode or modo_ativo"`
Expected: PASS (2 testes)

- [ ] **Step 6: Rodar a suíte completa do projeto**

Run: `pytest tests/ -v`
Expected: PASS em todos os testes (exceto a falha pré-existente e não relacionada já documentada em [[melhorias-motor-sinais-v3]]: `test_market_analysis::test_analysis_dados_insuficientes_retorna_422`)

- [ ] **Step 7: Commit**

```bash
git add backend/services/core_engine.py backend/services/signal_service.py tests/test_core_engine.py
git commit -m "feat(iv): liga filtro de volatilidade em shadow mode na emissao de sinais"
```

---

## Pendências manuais finais (antes do deploy)

- [ ] Aplicar `supabase/migrations/004_camada1_iv_signals.sql` no Supabase Dashboard.
- [ ] Aplicar `supabase/migrations/005_iv_history.sql` no Supabase Dashboard.
- [ ] Confirmar que `CONFIG['iv_filter_mode']` permanece `"shadow"` em produção até `iv_history` acumular >=60 dias úteis de cobertura para a maioria do universo líquido (acompanhar via `iv_rank(...)["confiavel"]`).
- [ ] Atualizar `docs/CHANGELOG.md` registrando a Camada 1 (seguir o padrão das entradas da Camada 0).
