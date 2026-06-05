# Carregador dinâmico de tickers da B3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o universo estático de scan por um universo líquido dinâmico (curados + API oficial da B3 + brapi → pré-filtro de volume em R$ → top_n), corrigindo de passagem os pontos que a mudança expõe (camadas, rate-limit, Telegram, naming).

**Architecture:** Fetchers brutos em `data_providers.py`; orquestração + cache TTL em processo num novo serviço `ticker_loader.py`; `run_scan` passa a varrer o universo líquido por padrão. Camadas respeitadas: `routers → services → domain/core` (o core deixa de importar services). Spec: [docs/superpowers/specs/2026-06-04-carregador-tickers-b3-design.md](../specs/2026-06-04-carregador-tickers-b3-design.md).

**Tech Stack:** Python, FastAPI, pandas, yfinance, requests, pytest (`unittest.mock`/`monkeypatch`). Rodar testes da raiz do projeto: `python -m pytest`.

**Convenções:** commits em pt-BR, **sem** trailer de co-autoria (hook `.githooks/commit-msg` bloqueia). Branch atual: `feat/carregador-tickers-b3`.

---

## File Structure

**Criar:**
- `backend/services/ticker_loader.py` — `carregar_tickers_b3()`, `get_all_b3_assets()`, cache em processo
- `tests/test_data_providers.py`, `tests/test_ticker_loader.py`, `tests/test_signal_service.py`, `tests/test_telegram.py`

**Modificar:**
- `backend/core/config.py` — knobs novos; rename `min_volume_diario→min_volume_acoes`; remover `get_all_b3_assets` (A1)
- `backend/services/data_providers.py` — `fetch_b3_official_tickers()`, `filtrar_por_volume()`
- `backend/services/core_engine.py:82` — rename da chave
- `backend/services/telegram_service.py` — `notificar_lote()`, fix `\n`, `requests`/`time` no topo
- `backend/services/signal_service.py` — `run_scan(universe=...)`, workers, Telegram em lote, log de duração, imports (A1)
- `backend/api/routers/signals.py:8` — importar `get_all_b3_assets` do loader (A1)
- `backend/api/routers/scan.py` — endpoints usam `universe=`; Telegram em lote
- `tests/test_config.py:27` — `REQUIRED_KEYS`

---

## Task 1: A5 — rename `min_volume_diario` → `min_volume_acoes`

**Files:**
- Modify: `tests/test_config.py:27`
- Modify: `backend/core/config.py:28`
- Modify: `backend/services/core_engine.py:82`

- [ ] **Step 1: Atualizar o teste para exigir a nova chave (falha primeiro)**

Em `tests/test_config.py`, na lista `REQUIRED_KEYS` (linha ~27), trocar `"min_volume_diario"` por `"min_volume_acoes"`:

```python
        "rr_minimo", "min_volume_acoes", "min_score",
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `python -m pytest tests/test_config.py::TestConfigDefaults -q`
Expected: FAIL — `CONFIG missing key: min_volume_acoes`

- [ ] **Step 3: Renomear a chave no config**

Em `backend/core/config.py` (linha 28):

```python
    "min_volume_acoes":     1_000_000,   # volume mínimo diário em QUANTIDADE DE AÇÕES (filtro fino do core_engine)
```

- [ ] **Step 4: Atualizar o uso no core_engine**

Em `backend/services/core_engine.py` (linha 82):

```python
        if vol_med < CONFIG["min_volume_acoes"]:
```

- [ ] **Step 5: Rodar os testes e ver passar**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/core/config.py backend/services/core_engine.py tests/test_config.py
git commit -m "refactor(config): renomeia min_volume_diario para min_volume_acoes (A5)"
```

---

## Task 2: CONFIG — knobs do carregador e dos pontos expostos

**Files:**
- Modify: `tests/test_config.py` (adicionar teste)
- Modify: `backend/core/config.py` (bloco CONFIG)

- [ ] **Step 1: Escrever o teste das novas chaves (falha primeiro)**

Adicionar ao final de `tests/test_config.py`:

```python
class TestLoaderKnobs:
    """Knobs do carregador de tickers e dos pontos expostos (A2/A3)."""

    @pytest.mark.parametrize("key", [
        "min_volume_rs", "ticker_top_n", "ticker_cache_segundos",
        "scan_max_workers", "telegram_throttle_s",
    ])
    def test_knob_exists(self, key):
        assert key in CONFIG, f"CONFIG missing key: {key}"

    def test_min_volume_rs_positive(self):
        assert CONFIG["min_volume_rs"] > 0

    def test_scan_max_workers_reasonable(self):
        assert 1 <= CONFIG["scan_max_workers"] <= 32
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_config.py::TestLoaderKnobs -q`
Expected: FAIL — `CONFIG missing key: min_volume_rs`

- [ ] **Step 3: Adicionar os knobs ao CONFIG**

Em `backend/core/config.py`, dentro do dict `CONFIG` (antes do bloco Telegram, após a seção `# ── Filtros`):

```python
    # ── Carregador de tickers (universo líquido) ───────────────────────────
    "min_volume_rs":         5_000_000,   # piso de volume financeiro diário (R$) p/ pré-filtro
    "ticker_top_n":          150,         # nº máx de tickers no universo líquido (None = sem limite)
    "ticker_cache_segundos": 3600,        # TTL do cache da lista líquida (em processo)

    # ── Scan / notificações (pontos expostos A2/A3) ────────────────────────
    "scan_max_workers":      8,           # workers do scan completo (alavanca anti rate-limit)
    "telegram_throttle_s":   0.5,         # delay entre envios de Telegram (evita 429)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py tests/test_config.py
git commit -m "feat(config): adiciona knobs do carregador, workers e throttle do Telegram"
```

---

## Task 3: `data_providers.fetch_b3_official_tickers()`

**Files:**
- Test: `tests/test_data_providers.py` (criar)
- Modify: `backend/services/data_providers.py` (imports + função)

- [ ] **Step 1: Escrever os testes (falha primeiro)**

Criar `tests/test_data_providers.py`:

```python
"""Testes de data_providers — fetch B3 oficial e filtro de volume (sem rede)."""
from unittest.mock import MagicMock
import pandas as pd
from backend.services import data_providers as dp


def _fake_b3_response(results, total_pages):
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {"page": {"totalPages": total_pages}, "results": results}
    return m


def test_fetch_b3_official_expands_suffixes(monkeypatch):
    resp = _fake_b3_response([{"issuingCompany": "PETR", "tradingName": "PETROBRAS"}], 1)
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp.requests, "get", lambda *a, **k: resp)
    out = dp.fetch_b3_official_tickers()
    assert out == {"PETR3": "PETROBRAS", "PETR4": "PETROBRAS", "PETR11": "PETROBRAS"}


def test_fetch_b3_official_paginates(monkeypatch):
    r1 = _fake_b3_response([{"issuingCompany": "PETR", "tradingName": "PETROBRAS"}], 2)
    r2 = _fake_b3_response([{"issuingCompany": "VALE", "tradingName": "VALE"}], 2)
    seq = iter([r1, r2])
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp.requests, "get", lambda *a, **k: next(seq))
    monkeypatch.setattr(dp.time, "sleep", lambda s: None)
    out = dp.fetch_b3_official_tickers()
    assert "PETR3" in out and "VALE3" in out


def test_fetch_b3_official_graceful_on_error(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(dp.requests, "get", boom)
    assert dp.fetch_b3_official_tickers() == {}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_data_providers.py -q`
Expected: FAIL — `AttributeError: module 'backend.services.data_providers' has no attribute 'fetch_b3_official_tickers'` (e `dp.time` ainda não existe)

- [ ] **Step 3: Adicionar imports no topo de `data_providers.py`**

Logo após `import requests` (linha 2), adicionar:

```python
import time
import json
import base64
```

- [ ] **Step 4: Implementar a função**

Adicionar em `backend/services/data_providers.py` (após `fetch_all_b3_tickers`, antes de `_fetch_chain`):

```python
_B3_LISTED_BASE = ("https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy"
                   "/CompanyCall/GetInitialCompanies")
_B3_SUFIXOS = ("3", "4", "11")
_B3_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}


def _b3_page_url(page_number: int, page_size: int = 120) -> str:
    payload = {"language": "pt-br", "pageNumber": page_number, "pageSize": page_size}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return f"{_B3_LISTED_BASE}/{encoded}"


def fetch_b3_official_tickers() -> Dict[str, str]:
    """
    Colhe raízes de empresas + nomes via API oficial da B3 e expande cada raiz
    de 4 letras nos sufixos negociáveis (3, 4, 11). Retorna {ticker_base: nome}.
    Cache 24h. Qualquer falha → {} (degradação graciosa). O ruído (tickers que
    não negociam) é removido depois pelo filtro de volume.
    """
    cached = cache_get("b3_official_tickers")
    if cached is not None:
        return cached

    resultado: Dict[str, str] = {}
    try:
        page, total_pages = 1, 1
        while page <= total_pages:
            r = requests.get(_b3_page_url(page), headers=_B3_HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
            total_pages = data.get("page", {}).get("totalPages", 1) or 1
            for emp in data.get("results", []):
                raiz = (emp.get("issuingCompany") or "").strip().upper()
                nome = (emp.get("tradingName") or emp.get("companyName") or raiz).strip()
                if len(raiz) == 4 and raiz.isalpha():
                    for suf in _B3_SUFIXOS:
                        resultado.setdefault(f"{raiz}{suf}", nome)
            page += 1
            if page <= total_pages:
                time.sleep(0.3)
        cache_set("b3_official_tickers", resultado, ttl=86400)
        logger.info(f"B3 oficial: {len(resultado)} candidatos em {total_pages} página(s)")
        return resultado
    except Exception as e:
        logger.warning(f"Erro ao buscar API oficial da B3: {e}")
        return {}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_data_providers.py -q`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/services/data_providers.py tests/test_data_providers.py
git commit -m "feat(data): fetch_b3_official_tickers — API oficial da B3 com expansao de sufixos"
```

---

## Task 4: `data_providers.filtrar_por_volume()`

**Files:**
- Modify: `tests/test_data_providers.py` (adicionar testes)
- Modify: `backend/services/data_providers.py` (import yfinance + funções)

- [ ] **Step 1: Escrever os testes (falha primeiro)**

Adicionar a `tests/test_data_providers.py`:

```python
def _multi_df(data: dict):
    """Monta um DataFrame estilo yfinance group_by='ticker' (colunas MultiIndex)."""
    idx = pd.date_range("2026-05-20", periods=3)
    cols = {}
    for t, (closes, vols) in data.items():
        cols[(t, "Close")] = closes
        cols[(t, "Volume")] = vols
    df = pd.DataFrame(cols, index=idx)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def test_filtrar_por_volume_aplica_limiar(monkeypatch):
    df = _multi_df({
        "AAAA3.SA": ([10, 10, 10], [1_000_000, 1_000_000, 1_000_000]),  # 10M R$
        "BBBB4.SA": ([1, 1, 1], [100, 100, 100]),                       # 100 R$
    })
    monkeypatch.setattr(dp.yf, "download", lambda *a, **k: df)
    out = dp.filtrar_por_volume(["AAAA3.SA", "BBBB4.SA"], min_volume_rs=5_000_000)
    assert out["AAAA3.SA"] == 10_000_000
    assert "BBBB4.SA" not in out


def test_filtrar_por_volume_ignora_sem_dados(monkeypatch):
    df = _multi_df({"AAAA3.SA": ([10, 10, 10], [1_000_000, 1_000_000, 1_000_000])})
    monkeypatch.setattr(dp.yf, "download", lambda *a, **k: df)
    # CCCC3.SA não está no df → ignorado
    out = dp.filtrar_por_volume(["AAAA3.SA", "CCCC3.SA"], min_volume_rs=1_000_000)
    assert "AAAA3.SA" in out and "CCCC3.SA" not in out


def test_filtrar_por_volume_lista_vazia():
    assert dp.filtrar_por_volume([], min_volume_rs=1) == {}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_data_providers.py -k filtrar -q`
Expected: FAIL — `module ... has no attribute 'yf'` / `'filtrar_por_volume'`

- [ ] **Step 3: Importar yfinance no topo de `data_providers.py`**

Após os imports existentes (junto com `import time`/`import json`):

```python
import yfinance as yf
```

- [ ] **Step 4: Implementar as funções**

Adicionar em `backend/services/data_providers.py` (após `fetch_b3_official_tickers`):

```python
def _volume_financeiro(data, ticker: str, single: bool) -> Optional[float]:
    """Volume financeiro médio diário (Close*Volume) de um ticker no df do yfinance.
    Lida com df single-index (1 ticker) e MultiIndex (vários)."""
    try:
        if single:
            sub = data
        else:
            if ticker not in data.columns.get_level_values(0):
                return None
            sub = data[ticker]
        close = sub["Close"].dropna()
        volume = sub["Volume"].dropna()
        if close.empty or volume.empty:
            return None
        fin = (close * volume).dropna()
        if fin.empty:
            return None
        return float(fin.mean())
    except Exception:
        return None


def filtrar_por_volume(
    tickers: List[str],
    min_volume_rs: float,
    batch_size: int = 20,
    delay_s: float = 1.0,
    period: str = "10d",
) -> Dict[str, float]:
    """
    Baixa OHLCV de `period` via yfinance em lotes e retorna
    {ticker: volume_financeiro_medio_rs} apenas para os que atingem min_volume_rs.
    Tickers sem dados são ignorados; erro num lote → loga e pula. Delay entre lotes.
    """
    aprovados: Dict[str, float] = {}
    if not tickers:
        return aprovados

    for i in range(0, len(tickers), batch_size):
        lote = tickers[i:i + batch_size]
        try:
            data = yf.download(
                lote, period=period, interval="1d", auto_adjust=True,
                progress=False, group_by="ticker", threads=True,
            )
        except Exception as e:
            logger.warning(f"filtrar_por_volume: lote {i // batch_size} falhou: {e}")
            continue

        single = len(lote) == 1
        for t in lote:
            vol_rs = _volume_financeiro(data, t, single)
            if vol_rs is not None and vol_rs >= min_volume_rs:
                aprovados[t] = vol_rs

        if i + batch_size < len(tickers):
            time.sleep(delay_s)

    logger.info(f"filtro de volume: {len(aprovados)}/{len(tickers)} ≥ R${min_volume_rs:,.0f}")
    return aprovados
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_data_providers.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/services/data_providers.py tests/test_data_providers.py
git commit -m "feat(data): filtrar_por_volume — pre-filtro de volume financeiro em R$"
```

---

## Task 5: `ticker_loader.carregar_tickers_b3()` + cache

**Files:**
- Create: `backend/services/ticker_loader.py`
- Test: `tests/test_ticker_loader.py` (criar)

- [ ] **Step 1: Escrever os testes (falha primeiro)**

Criar `tests/test_ticker_loader.py`:

```python
"""Testes do ticker_loader — orquestração do universo líquido (sem rede)."""
from backend.services import ticker_loader as tl
from backend.core.config import ATIVOS_B3


def setup_function():
    tl.clear_cache()


def _mock_sources(monkeypatch, b3=None, brapi=None, vols=None):
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: b3 or {})
    monkeypatch.setattr(tl, "fetch_all_b3_tickers", lambda: brapi or [])
    monkeypatch.setattr(tl, "filtrar_por_volume", lambda tickers, mv, **k: vols or {})


def test_curados_sempre_incluidos(monkeypatch):
    _mock_sources(monkeypatch)  # nada passa no filtro
    out = tl.carregar_tickers_b3(top_n=None)
    for t in ATIVOS_B3:
        assert t in out


def test_top_n_curados_primeiro_depois_volume(monkeypatch):
    _mock_sources(monkeypatch, brapi=["ZZZZ3", "YYYY3"],
                  vols={"ZZZZ3.SA": 9e9, "YYYY3.SA": 1e9})
    out = list(tl.carregar_tickers_b3(top_n=len(ATIVOS_B3) + 1).keys())
    assert out[0] in ATIVOS_B3              # curado primeiro
    assert out[-1] == "ZZZZ3.SA"           # maior volume entra
    assert "YYYY3.SA" not in out           # cortado pelo top_n


def test_nomes_curados_preservados(monkeypatch):
    _mock_sources(monkeypatch, b3={"PETR4": "OUTRO NOME"})
    out = tl.carregar_tickers_b3(filtrar_volume=False, top_n=None)
    assert out["PETR4.SA"] == ATIVOS_B3["PETR4.SA"]  # curado tem precedência


def test_cache_reuso(monkeypatch):
    chamadas = {"n": 0}
    def brapi():
        chamadas["n"] += 1
        return []
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {})
    monkeypatch.setattr(tl, "fetch_all_b3_tickers", brapi)
    monkeypatch.setattr(tl, "filtrar_por_volume", lambda *a, **k: {})
    tl.carregar_tickers_b3()
    tl.carregar_tickers_b3()
    assert chamadas["n"] == 1               # 2ª chamada veio do cache


def test_force_refresh_ignora_cache(monkeypatch):
    chamadas = {"n": 0}
    def brapi():
        chamadas["n"] += 1
        return []
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {})
    monkeypatch.setattr(tl, "fetch_all_b3_tickers", brapi)
    monkeypatch.setattr(tl, "filtrar_por_volume", lambda *a, **k: {})
    tl.carregar_tickers_b3()
    tl.carregar_tickers_b3(force_refresh=True)
    assert chamadas["n"] == 2


def test_todas_fontes_fora_volta_curados(monkeypatch):
    _mock_sources(monkeypatch)
    out = tl.carregar_tickers_b3(filtrar_volume=False, top_n=None)
    assert set(out.keys()) == set(ATIVOS_B3.keys())
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_ticker_loader.py -q`
Expected: FAIL — `ModuleNotFoundError: backend.services.ticker_loader`

- [ ] **Step 3: Criar o módulo**

Criar `backend/services/ticker_loader.py`:

```python
"""Carregador do universo de tickers da B3 (universo líquido).

Une as fontes (lista curada + API oficial da B3 + brapi), aplica o pré-filtro de
volume financeiro e o top_n, e mantém um cache TTL em processo (independe do
Redis) para reuso entre scans.

Camadas: este módulo (service) é a casa da montagem de universo — o core
(config) não importa services.
"""
import time
import logging
from typing import Dict, Optional

from backend.core.config import CONFIG, ATIVOS_B3
from backend.services.data_providers import (
    fetch_all_b3_tickers,
    fetch_b3_official_tickers,
    filtrar_por_volume,
)

logger = logging.getLogger("b3_scanner")

# Cache TTL em processo: {chave_params: (timestamp, valor)}
_universe_cache: dict = {}


def clear_cache() -> None:
    """Limpa o cache em processo (uso em testes)."""
    _universe_cache.clear()


def _base(ticker: str) -> str:
    return ticker.upper().replace(".SA", "").strip()


def carregar_tickers_b3(
    min_volume_rs: Optional[float] = None,
    top_n: Optional[int] = None,
    usar_api_b3: bool = True,
    usar_brapi: bool = True,
    usar_lista_curada: bool = True,
    filtrar_volume: bool = True,
    cache_segundos: Optional[int] = None,
    force_refresh: bool = False,
) -> Dict[str, str]:
    """Retorna {TICKER.SA: nome} do universo líquido (curados primeiro)."""
    if min_volume_rs is None:
        min_volume_rs = CONFIG["min_volume_rs"]
    if top_n is None:
        top_n = CONFIG.get("ticker_top_n")
    if cache_segundos is None:
        cache_segundos = CONFIG.get("ticker_cache_segundos", 3600)

    chave = (min_volume_rs, top_n, usar_api_b3, usar_brapi, usar_lista_curada, filtrar_volume)
    if not force_refresh and chave in _universe_cache:
        ts, valor = _universe_cache[chave]
        if time.time() - ts < cache_segundos:
            return valor

    # 1. Universo bruto {base: nome} — curados têm precedência de nome
    curados = {_base(t): nome for t, nome in ATIVOS_B3.items()}
    universo: Dict[str, str] = {}
    if usar_lista_curada:
        universo.update(curados)
    if usar_api_b3:
        for base, nome in fetch_b3_official_tickers().items():
            universo.setdefault(_base(base), nome)
    if usar_brapi:
        for base in fetch_all_b3_tickers():
            universo.setdefault(_base(base), _base(base))

    curados_bases = list(curados.keys()) if usar_lista_curada else []
    curados_set = set(curados_bases)

    # 2. Filtro de volume — curados sempre passam (precedência + fallback)
    if filtrar_volume:
        nao_curados = [b for b in universo if b not in curados_set]
        vols = filtrar_por_volume([f"{b}.SA" for b in nao_curados], min_volume_rs)
        aprovados = sorted(
            ((_base(sa), v) for sa, v in vols.items()),
            key=lambda kv: kv[1], reverse=True,
        )
        ordem = curados_bases + [b for b, _ in aprovados]
    else:
        ordem = curados_bases + [b for b in universo if b not in curados_set]

    # 3. top_n (curados ficam no topo, então nunca são cortados antes dos demais)
    if top_n is not None:
        ordem = ordem[:top_n]

    resultado = {f"{b}.SA": universo.get(b, b) for b in ordem}
    _universe_cache[chave] = (time.time(), resultado)
    logger.info(f"Universo líquido: {len(resultado)} tickers (curados={len(curados_bases)})")
    return resultado
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_ticker_loader.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/ticker_loader.py tests/test_ticker_loader.py
git commit -m "feat(loader): carregar_tickers_b3 — universo liquido com cache em processo"
```

---

## Task 6: A1 — mover `get_all_b3_assets` para o loader (fim da violação de camadas)

**Files:**
- Modify: `backend/services/ticker_loader.py` (adicionar wrapper)
- Modify: `backend/core/config.py` (remover função + import interno)
- Modify: `backend/services/signal_service.py:16` (import)
- Modify: `backend/api/routers/signals.py:8` (import)
- Modify: `tests/test_ticker_loader.py` (testes de camada)

- [ ] **Step 1: Escrever os testes de camada (falha primeiro)**

Adicionar a `tests/test_ticker_loader.py`:

```python
def test_get_all_b3_assets_vive_no_loader():
    assert hasattr(tl, "get_all_b3_assets")


def test_config_nao_exporta_mais_get_all_b3_assets():
    import backend.core.config as cfg
    assert not hasattr(cfg, "get_all_b3_assets")


def test_config_nao_importa_services():
    """config (core) não pode importar services (regra de camadas)."""
    import inspect, backend.core.config as cfg
    src = inspect.getsource(cfg)
    assert "backend.services" not in src
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_ticker_loader.py -k "loader or camada or config or services" -q`
Expected: FAIL — `config` ainda tem `get_all_b3_assets` e importa services

- [ ] **Step 3: Adicionar o wrapper no loader**

Ao final de `backend/services/ticker_loader.py`:

```python
def get_all_b3_assets() -> Dict[str, str]:
    """Compat: universo líquido como dict {TICKER.SA: nome}. (Antes em config.py.)

    Mantido para os consumidores existentes (run_scan, /watchlist). Reflete o
    universo líquido real, compartilhando o cache do carregador.
    """
    return carregar_tickers_b3()
```

- [ ] **Step 4: Remover `get_all_b3_assets` do config**

Em `backend/core/config.py`, apagar a função inteira `get_all_b3_assets` (linhas ~127-139, incluindo o docstring e o `from backend.services.data_providers import fetch_all_b3_tickers` interno). Manter `ATIVOS_B3`, `OTM_*`, helpers.

- [ ] **Step 5: Atualizar o import no signal_service**

Em `backend/services/signal_service.py` (linha 16), trocar:

```python
from backend.core.config import ATIVOS_B3, CONFIG
from backend.services.ticker_loader import carregar_tickers_b3, get_all_b3_assets
```

- [ ] **Step 6: Atualizar o import no router signals**

Em `backend/api/routers/signals.py` (linha 8), trocar:

```python
from backend.core.config import ATIVOS_B3
from backend.services.ticker_loader import get_all_b3_assets
```

- [ ] **Step 7: Rodar testes e ver passar**

Run: `python -m pytest tests/test_ticker_loader.py tests/test_api_routing.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/services/ticker_loader.py backend/core/config.py backend/services/signal_service.py backend/api/routers/signals.py tests/test_ticker_loader.py
git commit -m "refactor(loader): move get_all_b3_assets do core para o service (A1 camadas)"
```

---

## Task 7: A3/B3 — Telegram em lote com throttle + fix do `\n` literal

**Files:**
- Test: `tests/test_telegram.py` (criar)
- Modify: `backend/services/telegram_service.py` (imports topo, `notificar_lote`, fix `\n`)

- [ ] **Step 1: Escrever os testes (falha primeiro)**

Criar `tests/test_telegram.py`:

```python
"""Testes do telegram_service — lote com throttle e quebras de linha reais."""
from backend.services import telegram_service as ts


def test_notificar_lote_envia_todos_com_throttle(monkeypatch):
    enviados, slept = [], []
    monkeypatch.setattr(ts, "enviar_telegram", lambda s: enviados.append(s["ticker"]))
    monkeypatch.setattr(ts.time, "sleep", lambda s: slept.append(s))
    ts.notificar_lote([{"ticker": "A"}, {"ticker": "B"}, {"ticker": "C"}], throttle_s=0.1)
    assert enviados == ["A", "B", "C"]
    assert slept == [0.1, 0.1]   # 2 sleeps entre 3 mensagens


def test_notificar_lote_vazio_nao_quebra(monkeypatch):
    monkeypatch.setattr(ts, "enviar_telegram", lambda s: None)
    monkeypatch.setattr(ts.time, "sleep", lambda s: None)
    ts.notificar_lote([])  # não deve levantar


def test_enviar_telegram_usa_quebras_reais(monkeypatch):
    capt = {}
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "y")

    def fake_post(url, data=None, timeout=None):
        capt["text"] = data["text"]
        return object()

    monkeypatch.setattr(ts.requests, "post", fake_post)
    ts.enviar_telegram({"ticker": "PETR4", "nome": "Petrobras", "tipo_sinal": "CALL",
                        "mes_venc": 6, "ano_venc": 2026, "gatilhos": ["g1"]})
    assert "\\n" not in capt["text"]   # sem barra-n literal
    assert "\n" in capt["text"]         # quebras de linha reais
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_telegram.py -q`
Expected: FAIL — `ts.time`/`ts.requests` inexistentes no topo, `notificar_lote` indefinido, e `\\n` presente no texto

- [ ] **Step 3: Mover `requests`/`time` para o topo do módulo**

Em `backend/services/telegram_service.py`, junto aos imports do topo (após `import json`):

```python
import time
import requests
```

E **remover** o `import requests` de dentro de `enviar_telegram` (linha 54).

- [ ] **Step 4: Corrigir o `\n` literal**

Em `enviar_telegram`, na construção de `msg` (linhas ~61-72), trocar todas as ocorrências de `\\n` por `\n`. O bloco correto:

```python
    msg = (
        f"🎯 *SINAL B3 — {sinal.get('ticker')}* ({sinal.get('nome')})\n"
        f"*Tipo:* {sinal.get('tipo_sinal')} | *Venc:* {mes_str}/{sinal.get('ano_venc')}\n"
        f"*Strike ref:* R$ {sinal.get('strike_ref', 0):.2f} ({sinal.get('dist_otm_pct', 0):.0f}% OTM)\n"
        f"*IV Hist:* {sinal.get('iv_hist')}% | *DTE:* {sinal.get('dte')} du\n\n"
        f"*Entrada:* R$ {sinal.get('entrada_min', 0):.2f} – {sinal.get('entrada_max', 0):.2f}\n"
        f"*Alvo 1:* R$ {sinal.get('alvo1', 0):.2f} (+{CONFIG.get('alvo1_pct', 0.25)*100:.0f}%) | R/R: {sinal.get('rr_alvo1', 0):.1f}×\n"
        f"*Alvo 2:* R$ {sinal.get('alvo2', 0):.2f} (+{CONFIG.get('alvo2_pct', 0.5)*100:.0f}%) | R/R: {sinal.get('rr_alvo2', 0):.1f}×\n"
        f"*Stop:* R$ {sinal.get('stop', 0):.2f} ({CONFIG.get('stop_pct', 0.5)*100:.0f}%)\n\n"
        f"*Score:* {sinal.get('score')}/10\n"
        f"*Gatilhos:*\n• " + "\n• ".join(sinal.get("gatilhos", []))
    )
```

- [ ] **Step 5: Implementar `notificar_lote`**

Adicionar após `enviar_telegram`:

```python
def notificar_lote(sinais: list, throttle_s: float | None = None) -> None:
    """Envia uma lista de sinais ao Telegram com throttle entre mensagens (A3).

    Fica FORA do hot-loop de scan: o chamador acumula os sinais e envia ao final,
    evitando travar a coleta e tomar 429 quando há muitos sinais.
    """
    if throttle_s is None:
        throttle_s = CONFIG.get("telegram_throttle_s", 0.5)
    for i, sinal in enumerate(sinais):
        enviar_telegram(sinal)
        if i < len(sinais) - 1 and throttle_s > 0:
            time.sleep(throttle_s)
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_telegram.py -q`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/services/telegram_service.py tests/test_telegram.py
git commit -m "fix(telegram): notificar_lote com throttle e corrige quebras de linha (A3/B3)"
```

---

## Task 8: A2/A4 — `run_scan(universe=...)`, workers, Telegram em lote, log de duração

**Files:**
- Test: `tests/test_signal_service.py` (criar)
- Modify: `backend/services/signal_service.py` (import linha 19; `run_scan`; `scan_batch`)

- [ ] **Step 1: Escrever os testes (falha primeiro)**

Criar `tests/test_signal_service.py`:

```python
"""Testes de run_scan — seleção de universo, lote único de Telegram (sem rede)."""
from backend.services import signal_service as ss
from backend.core.config import ATIVOS_B3


def _stub_common(monkeypatch):
    monkeypatch.setattr(ss, "persist_signals", lambda s: None)
    monkeypatch.setattr(ss, "update_last_scan", lambda s: None)
    monkeypatch.setattr(ss, "_maybe_broadcast", lambda s: None)


def test_run_scan_curado_itera_ativos_b3(monkeypatch):
    _stub_common(monkeypatch)
    seen = []
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: seen.append(t) or None)
    monkeypatch.setattr(ss, "notificar_lote", lambda s: None)
    ss.run_scan(universe="curado")
    assert set(seen) == set(ATIVOS_B3.keys())


def test_run_scan_liquido_usa_loader(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(ss, "carregar_tickers_b3", lambda: {"XPTO3.SA": "Xpto"})
    seen = []
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: seen.append(t) or None)
    monkeypatch.setattr(ss, "notificar_lote", lambda s: None)
    ss.run_scan()  # default = liquido
    assert seen == ["XPTO3.SA"]


def test_run_scan_telegram_em_lote_unico(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(ss, "carregar_tickers_b3", lambda: {"A3.SA": "A", "B3.SA": "B"})
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: {"ticker": t})
    lotes = []
    monkeypatch.setattr(ss, "notificar_lote", lambda s: lotes.append(list(s)))
    ss.run_scan()
    assert len(lotes) == 1          # um único envio em lote, não por-sinal
    assert len(lotes[0]) == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_signal_service.py -q`
Expected: FAIL — `run_scan() got unexpected keyword 'universe'` / `ss.notificar_lote` inexistente

- [ ] **Step 3: Atualizar o import do Telegram (linha 19)**

Em `backend/services/signal_service.py`:

```python
from backend.services.telegram_service import enviar_telegram, notificar_lote
```

- [ ] **Step 4: Reescrever `run_scan`**

Substituir a função `run_scan` inteira (linhas ~222-240) por:

```python
def run_scan(verbose: bool = False, universe: str = "liquido"):
    """Scan agendado. universe: 'liquido' (padrão, universo filtrado) | 'curado'.

    A2: workers via CONFIG['scan_max_workers']. A3: Telegram em lote ao final
    (fora do hot-loop). A4: loga a duração do scan.
    """
    inicio = datetime.now(timezone.utc)
    if universe == "curado":
        ativos = list(ATIVOS_B3.items())
    else:
        ativos = list(carregar_tickers_b3().items())
    logger.info(f"Iniciando scan ({universe}) — {len(ativos)} ativos...")
    sinais: list[dict] = []

    max_workers = CONFIG.get("scan_max_workers", 8)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(analyse_ticker, ticker, nome, verbose): ticker
                   for ticker, nome in ativos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)
                _maybe_broadcast(result)

    update_last_scan(sinais)
    persist_signals(sinais)
    notificar_lote(sinais)
    dur = (datetime.now(timezone.utc) - inicio).total_seconds()
    logger.info(f"Scan ({universe}) concluído — {len(sinais)} sinal(is) em {dur:.0f}s")
```

- [ ] **Step 5: Rotear `scan_batch` pelo lote (consistência A3)**

Em `scan_batch` (linhas ~213-217), trocar o loop de envio:

```python
    if sinais:
        persist_signals(sinais)
        notificar_lote(sinais)
        update_last_scan(sinais)
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_signal_service.py -q`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/services/signal_service.py tests/test_signal_service.py
git commit -m "feat(scan): run_scan(universe), workers configuraveis, Telegram em lote, log de duracao (A2/A3/A4)"
```

---

## Task 9: Endpoints de scan — `universe=` + Telegram em lote

**Files:**
- Modify: `backend/api/routers/scan.py` (linhas 16-17 import; 105; 114; 74-77 stream)

- [ ] **Step 1: Atualizar `/scan/all` e `/scan/all-b3`**

Em `backend/api/routers/scan.py`:

- Linha 105 (`scan_all`): `signal_service.run_scan(universe="curado")`
- Linha 114 (`scan_all_b3`): `signal_service.run_scan(universe="liquido")` (substitui `all_b3=True`)

- [ ] **Step 2: Rotear o Telegram do stream pelo lote**

`enviar_telegram` é usado em `scan.py` **apenas** no `scan_stream` (linha ~77). Substituir o import da linha 17 por `notificar_lote` (isso já remove o `enviar_telegram` não usado):

```python
from backend.services.telegram_service import notificar_lote
```

E trocar o envio no `scan_stream` (linhas ~74-78):

```python
        if sinais:
            persist_signals(sinais)
            notificar_lote(sinais)
            signal_service.update_last_scan(sinais)
```

- [ ] **Step 3: Rodar os testes de roteamento e o conjunto de scan**

Run: `python -m pytest tests/test_api_routing.py tests/test_signal_service.py -q`
Expected: PASS (rotas resolvem para os mesmos handlers; comportamento de universo coberto na Task 8)

- [ ] **Step 4: Commit**

```bash
git add backend/api/routers/scan.py
git commit -m "feat(api): /scan/all-b3 varre universo liquido; Telegram em lote no stream"
```

---

## Task 10: CHANGELOG + verificação final

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 1: Registrar no CHANGELOG**

Adicionar no topo da seção de versões de `docs/CHANGELOG.md` (seguir o estilo existente do arquivo):

```markdown
## [Não lançado]

### Adicionado
- Carregador dinâmico de tickers da B3 (`ticker_loader.py`): universo líquido = curados + API oficial da B3 + brapi, com pré-filtro de volume financeiro (R$) e `top_n`. Cache TTL em processo (independe do Redis).
- `data_providers`: `fetch_b3_official_tickers()` (API oficial da B3, expansão de sufixos 3/4/11) e `filtrar_por_volume()` (volume financeiro em R$).
- CONFIG: `min_volume_rs`, `ticker_top_n`, `ticker_cache_segundos`, `scan_max_workers`, `telegram_throttle_s`.

### Alterado
- Scan agendado passa a varrer o **universo líquido** por padrão (`run_scan(universe="liquido")`); `/signals/scan/all-b3` agora varre ~150 líquidos (antes ~400 crus).
- `get_all_b3_assets` movido de `config` (core) para `ticker_loader` (service) — fim da violação de camadas (A1).
- Telegram enviado em lote com throttle, fora do hot-loop de scan (A3).
- CONFIG: `min_volume_diario` renomeado para `min_volume_acoes` (A5).

### Corrigido
- Mensagens do Telegram usavam `\n` literal em vez de quebras de linha reais (B3).
```

- [ ] **Step 2: Rodar a suíte completa**

Run: `python -m pytest -q`
Expected: PASS (toda a suíte verde — nova + existente)

- [ ] **Step 3: Lint rápido de import/camadas (sanidade)**

Run: `python -c "import backend.api.main; import backend.services.ticker_loader; print('imports ok')"`
Expected: `imports ok` (sem ImportError nem circular)

- [ ] **Step 4: Commit**

```bash
git add docs/CHANGELOG.md
git commit -m "docs(changelog): registra carregador de tickers e correcoes expostas"
```

---

## Notas de execução

- **Sem rede nos testes:** todo I/O (`requests`, `yfinance`, `time.sleep`) é mockado. Se um teste tentar acessar a rede, é bug do teste.
- **Ordem importa:** Tasks 3-4 (data_providers) antes da Task 5 (loader); Task 5 antes da Task 6 (move). Task 7 (telegram) antes da Task 8 (run_scan usa `notificar_lote`).
- **Follow-ups (PR separado):** B1 (decompor `analisar_ativo`), B2 (nome enriquecido em `scan_single`/`scan_batch`).
- **Pós-merge, observabilidade:** acompanhar o log `Scan (liquido) concluído — N sinal(is) em Ds` (A4). Se `D` se aproximar de 30min (cadência), reduzir `ticker_top_n` ou `scan_max_workers`.
