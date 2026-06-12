# Indicadores e Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar a sub-página `/analytics/indicadores` ("Indicadores e Setup") que, ao digitar um ticker, mostra indicadores técnicos, setups de price action e uma leitura de mercado para o ativo e suas opções.

**Architecture:** Endpoint dedicado `GET /market/indicators/{ticker}` reusa o fetch histórico e `calcular_indicadores` existentes e adiciona um módulo puro `setups.py`. O front consome via hook próprio e renderiza painéis isolados; o valuation reaproveita `scoreAsset`. Painéis sem fonte de dados aparecem como "em breve".

**Tech Stack:** Python/FastAPI/pandas/pytest (backend); Next.js/React/TypeScript/recharts/vitest (frontend).

Spec: `docs/superpowers/specs/2026-06-11-analytics-indicadores-e-setup-design.md`

**Convenção de commit:** NÃO incluir trailer `Co-Authored-By` de Claude/Anthropic (um commit-msg hook bloqueia).

---

## File Structure

Backend:
- Create `backend/domain/setups.py` — detecção pura de setups (uma responsabilidade: OHLC+indicadores → lista de `SetupResult`).
- Modify `backend/api/routers/market.py` — novo endpoint `/market/indicators/{ticker}`; expõe atr/vwap; expected move; leitura de vol; parse de vencimento da chain.
- Create `tests/test_setups.py` — testes do módulo de setups.
- Modify `tests/test_market_analysis.py` — (opcional) derivações novas do endpoint.

Frontend:
- Create `src/lib/types/indicators.ts` — tipo do payload.
- Create `src/hooks/useIndicators.ts` — hook de fetch.
- Create `src/lib/indicators-narrative.ts` — regras puras de narrativa/técnica (testável).
- Create `src/components/indicators/Gauges.tsx` — primitivos de barra/gauge compartilhados.
- Create `src/components/indicators/IndicatorPanels.tsx` — Momento/Tendência/Reversão/Volatilidade.
- Create `src/components/indicators/SetupsGrid.tsx` — grade de setups.
- Create `src/components/indicators/VolReadCard.tsx` — leitura para opções.
- Create `src/components/indicators/ComingSoonPanel.tsx` — painéis "em breve".
- Create `src/components/indicators/IndicatorsHeader.tsx` — cabeçalho + resumo.
- Create `src/app/analytics/indicadores/page.tsx` — a página.
- Modify `src/app/analytics/page.tsx` — link para a sub-página.
- Create `src/lib/__tests__/indicators-narrative.test.ts` — testes da narrativa.

---

## Task 1: `setups.py` — base, tendência MME9 e Larry 9.1

**Files:**
- Create: `backend/domain/setups.py`
- Test: `tests/test_setups.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_setups.py
import pandas as pd
from backend.domain.setups import SetupResult, _tendencia_ema9, larry_91


def _df(rows):
    """rows: list of (open, high, low, close). Volume fixo, ema9 adicionada à parte."""
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"])
    df["Volume"] = 1_000_000.0
    return df


def _with_ema9(df, ema9_vals):
    df = df.copy()
    df["ema9"] = ema9_vals
    return df


class TestTendenciaEma9:
    def test_up_quando_ema9_sobe(self):
        df = _with_ema9(_df([(1, 1, 1, 1)] * 5), [10, 11, 12, 13, 14])
        assert _tendencia_ema9(df) == "up"

    def test_down_quando_ema9_cai(self):
        df = _with_ema9(_df([(1, 1, 1, 1)] * 5), [14, 13, 12, 11, 10])
        assert _tendencia_ema9(df) == "down"


class TestLarry91:
    def test_compra_ativa_rompe_maxima_anterior_em_tendencia_alta(self):
        # ema9 subindo; último close (12) > high anterior (11)
        df = _df([(9, 10, 8, 9), (10, 11, 9, 10), (10, 13, 10, 12)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_91(df)
        assert r.status == "ativo"
        assert r.vies == "alta"

    def test_inativo_quando_nao_rompe(self):
        df = _df([(9, 10, 8, 9), (10, 11, 9, 10), (10, 10.5, 10, 10.2)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_91(df)
        assert r.status == "inativo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setups.py -v`
Expected: FAIL com `ModuleNotFoundError: backend.domain.setups`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/domain/setups.py
"""Detecção pura de setups de price action a partir de OHLCV + indicadores.

Cada detector avalia o candle mais recente (iloc[-1]) e retorna um SetupResult.
São interpretações determinísticas e simplificadas, adequadas a um flag de
estado numa página de leitura — não a execução automática.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class SetupResult:
    nome: str
    status: str   # "ativo" | "armado" | "inativo"
    vies: str     # "alta" | "baixa" | "neutro"
    descricao: str


def _tendencia_ema9(df: pd.DataFrame) -> str:
    """Inclinação da MME9: 'up', 'down' ou 'flat' (slope ema9[-1] - ema9[-4])."""
    if "ema9" not in df.columns or len(df) < 4:
        return "flat"
    slope = float(df["ema9"].iloc[-1]) - float(df["ema9"].iloc[-4])
    if slope > 0:
        return "up"
    if slope < 0:
        return "down"
    return "flat"


def larry_91(df: pd.DataFrame) -> SetupResult:
    """Continuação por rompimento na direção da MME9."""
    nome = "Larry 9.1"
    if len(df) < 4:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    close = float(df["Close"].iloc[-1])
    high_prev = float(df["High"].iloc[-2])
    low_prev = float(df["Low"].iloc[-2])
    if tend == "up" and close > high_prev:
        return SetupResult(nome, "ativo", "alta",
                           "MME9 em alta e rompimento da máxima anterior — continuação compradora.")
    if tend == "down" and close < low_prev:
        return SetupResult(nome, "ativo", "baixa",
                           "MME9 em baixa e rompimento da mínima anterior — continuação vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Sem rompimento a favor da MME9.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setups.py -v`
Expected: PASS (4 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/setups.py tests/test_setups.py
git commit -m "feat(setups): base SetupResult, tendência MME9 e Larry 9.1"
```

---

## Task 2: `setups.py` — Larry 9.2 e 9.3

**Files:**
- Modify: `backend/domain/setups.py`
- Test: `tests/test_setups.py`

- [ ] **Step 1: Write the failing test**

```python
# adicionar a tests/test_setups.py
from backend.domain.setups import larry_92, larry_93


class TestLarry92:
    def test_armado_em_alta_com_pullback(self):
        # ema9 up; último candle faz mínima menor que a anterior
        df = _df([(10, 11, 9, 10), (11, 12, 10, 11), (10, 11, 8, 9)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_92(df)
        assert r.status == "armado"
        assert r.vies == "alta"

    def test_disparado_em_alta(self):
        # anterior foi pullback (low[-2] < low[-3]); atual rompe a máxima anterior
        df = _df([(10, 12, 10, 11), (10, 11, 8, 9), (9, 13, 9, 12)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_92(df)
        assert r.status == "ativo"
        assert r.vies == "alta"


class TestLarry93:
    def test_armado_apos_duas_minimas_decrescentes_em_alta(self):
        df = _df([(10, 12, 11, 11), (10, 11, 10, 10), (9, 10, 9, 9)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_93(df)
        assert r.status == "armado"
        assert r.vies == "alta"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setups.py::TestLarry92 tests/test_setups.py::TestLarry93 -v`
Expected: FAIL com `ImportError: cannot import name 'larry_92'`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar a backend/domain/setups.py
def larry_92(df: pd.DataFrame) -> SetupResult:
    """Pivô de retorno à média (1 candle de pullback)."""
    nome = "Larry 9.2"
    if len(df) < 4:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    low = df["Low"]
    high = df["High"]
    if tend == "up":
        disparou = float(low.iloc[-3]) > float(low.iloc[-2]) and float(high.iloc[-1]) > float(high.iloc[-2])
        if disparou:
            return SetupResult(nome, "ativo", "alta",
                               "Rompimento da máxima após pullback — entrada compradora a favor da MME9.")
        if float(low.iloc[-1]) < float(low.iloc[-2]):
            return SetupResult(nome, "armado", "alta",
                               f"Pullback em tendência de alta — aguardando rompimento de R$ {float(high.iloc[-1]):.2f}.")
    if tend == "down":
        disparou = float(high.iloc[-3]) < float(high.iloc[-2]) and float(low.iloc[-1]) < float(low.iloc[-2])
        if disparou:
            return SetupResult(nome, "ativo", "baixa",
                               "Rompimento da mínima após repique — entrada vendedora a favor da MME9.")
        if float(high.iloc[-1]) > float(high.iloc[-2]):
            return SetupResult(nome, "armado", "baixa",
                               f"Repique em tendência de baixa — aguardando perda de R$ {float(low.iloc[-1]):.2f}.")
    return SetupResult(nome, "inativo", "neutro", "Sem pivô de retorno à média.")


def larry_93(df: pd.DataFrame) -> SetupResult:
    """Continuação após duas correções consecutivas contra a tendência."""
    nome = "Larry 9.3"
    if len(df) < 4:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    tend = _tendencia_ema9(df)
    low = df["Low"]
    high = df["High"]
    if tend == "up" and float(low.iloc[-1]) < float(low.iloc[-2]) < float(low.iloc[-3]):
        return SetupResult(nome, "armado", "alta",
                           "Duas mínimas decrescentes em tendência de alta — correção madura, aguardando retomada.")
    if tend == "down" and float(high.iloc[-1]) > float(high.iloc[-2]) > float(high.iloc[-3]):
        return SetupResult(nome, "armado", "baixa",
                           "Duas máximas crescentes em tendência de baixa — repique maduro, aguardando retomada.")
    return SetupResult(nome, "inativo", "neutro", "Sem padrão de continuação 9.3.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setups.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/domain/setups.py tests/test_setups.py
git commit -m "feat(setups): Larry 9.2 e 9.3"
```

---

## Task 3: `setups.py` — Inside Bar e Rompimento de máxima/mínima

**Files:**
- Modify: `backend/domain/setups.py`
- Test: `tests/test_setups.py`

- [ ] **Step 1: Write the failing test**

```python
# adicionar a tests/test_setups.py
from backend.domain.setups import inside_bar, rompimento


class TestInsideBar:
    def test_ativo_quando_candle_dentro_do_anterior(self):
        df = _df([(10, 14, 8, 12), (11, 13, 9, 10)])
        df = _with_ema9(df, [10, 11])
        r = inside_bar(df)
        assert r.status == "ativo"

    def test_inativo_quando_rompe(self):
        df = _df([(10, 13, 9, 12), (11, 14, 9, 13)])
        df = _with_ema9(df, [10, 11])
        assert inside_bar(df).status == "inativo"


class TestRompimento:
    def test_rompe_resistencia(self):
        df = _df([(10, 11, 9, 10)] * 3)
        df["resistencia_20"] = [10.5, 10.5, 10.5]
        df["suporte_20"] = [8, 8, 8]
        df.loc[df.index[-1], "Close"] = 11.0  # close > resistencia anterior 10.5
        r = rompimento(df)
        assert r.status == "ativo" and r.vies == "alta"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setups.py::TestInsideBar tests/test_setups.py::TestRompimento -v`
Expected: FAIL com `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar a backend/domain/setups.py
def inside_bar(df: pd.DataFrame) -> SetupResult:
    """Candle atual contido no range do anterior."""
    nome = "Inside Bar"
    if len(df) < 2:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    dentro = (float(df["High"].iloc[-1]) <= float(df["High"].iloc[-2])
              and float(df["Low"].iloc[-1]) >= float(df["Low"].iloc[-2]))
    if dentro:
        tend = _tendencia_ema9(df)
        vies = "alta" if tend == "up" else "baixa" if tend == "down" else "neutro"
        return SetupResult(nome, "ativo", vies,
                           "Barra interna — compressão de volatilidade; rompimento define a direção.")
    return SetupResult(nome, "inativo", "neutro", "Sem barra interna no candle atual.")


def rompimento(df: pd.DataFrame) -> SetupResult:
    """Rompimento da resistência/suporte de 20 períodos."""
    nome = "Rompimento 20"
    if len(df) < 2 or "resistencia_20" not in df.columns:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    close = float(df["Close"].iloc[-1])
    resist = float(df["resistencia_20"].iloc[-2])
    sup = float(df["suporte_20"].iloc[-2])
    if close > resist:
        return SetupResult(nome, "ativo", "alta",
                           f"Rompimento da máxima de 20 períodos (R$ {resist:.2f}) — força compradora.")
    if close < sup:
        return SetupResult(nome, "ativo", "baixa",
                           f"Perda do suporte de 20 períodos (R$ {sup:.2f}) — força vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Preço dentro do range de 20 períodos.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setups.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/domain/setups.py tests/test_setups.py
git commit -m "feat(setups): Inside Bar e Rompimento de 20 períodos"
```

---

## Task 4: `setups.py` — Engolfo, Pin Bar/Martelo/Shooting Star, Doji

**Files:**
- Modify: `backend/domain/setups.py`
- Test: `tests/test_setups.py`

- [ ] **Step 1: Write the failing test**

```python
# adicionar a tests/test_setups.py
from backend.domain.setups import engolfo, pin_bar, doji


class TestCandles:
    def test_engolfo_de_alta(self):
        # anterior vermelho (open10>close9); atual verde engole (open8<=close9, close12>=open10)
        df = _df([(10, 10, 9, 9), (8, 13, 8, 12)])
        df = _with_ema9(df, [10, 9])
        r = engolfo(df)
        assert r.status == "ativo" and r.vies == "alta"

    def test_martelo(self):
        # corpo pequeno no topo, sombra inferior longa
        df = _df([(10, 10, 8, 9.8)])
        df = _with_ema9(df, [9])
        r = pin_bar(df)
        assert r.status == "ativo" and r.vies == "alta"

    def test_doji(self):
        df = _df([(10, 11, 9, 10.02)])
        df = _with_ema9(df, [10])
        assert doji(df).status == "ativo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setups.py::TestCandles -v`
Expected: FAIL com `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar a backend/domain/setups.py
def engolfo(df: pd.DataFrame) -> SetupResult:
    """Padrão de engolfo (engulfing) de alta ou baixa."""
    nome = "Engolfo"
    if len(df) < 2:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o1, c1 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    o0, c0 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1])
    bull = c1 < o1 and c0 > o0 and o0 <= c1 and c0 >= o1
    bear = c1 > o1 and c0 < o0 and o0 >= c1 and c0 <= o1
    if bull:
        return SetupResult(nome, "ativo", "alta", "Engolfo de alta — reversão compradora.")
    if bear:
        return SetupResult(nome, "ativo", "baixa", "Engolfo de baixa — reversão vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Sem engolfo no candle atual.")


def pin_bar(df: pd.DataFrame) -> SetupResult:
    """Martelo (sombra inferior longa) ou Shooting Star (sombra superior longa)."""
    nome = "Pin Bar"
    if len(df) < 1:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o = float(df["Open"].iloc[-1]); c = float(df["Close"].iloc[-1])
    h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])
    corpo = abs(c - o)
    rng = h - l
    if rng <= 0:
        return SetupResult(nome, "inativo", "neutro", "Candle sem range.")
    sombra_inf = min(o, c) - l
    sombra_sup = h - max(o, c)
    if corpo > 0 and sombra_inf >= 2 * corpo and max(o, c) >= l + 0.66 * rng:
        return SetupResult(nome, "ativo", "alta", "Martelo — rejeição de preços baixos.")
    if corpo > 0 and sombra_sup >= 2 * corpo and min(o, c) <= l + 0.34 * rng:
        return SetupResult(nome, "ativo", "baixa", "Shooting Star — rejeição de preços altos.")
    return SetupResult(nome, "inativo", "neutro", "Sem pin bar no candle atual.")


def doji(df: pd.DataFrame) -> SetupResult:
    """Doji — corpo desprezível frente ao range (indecisão)."""
    nome = "Doji"
    if len(df) < 1:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    o = float(df["Open"].iloc[-1]); c = float(df["Close"].iloc[-1])
    h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])
    rng = h - l
    if rng > 0 and abs(c - o) <= 0.1 * rng:
        return SetupResult(nome, "ativo", "neutro", "Doji — indecisão entre compra e venda.")
    return SetupResult(nome, "inativo", "neutro", "Sem doji no candle atual.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setups.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/domain/setups.py tests/test_setups.py
git commit -m "feat(setups): Engolfo, Pin Bar/Martelo e Doji"
```

---

## Task 5: `setups.py` — Pullback MME9/21 e agregador `detectar_setups`

**Files:**
- Modify: `backend/domain/setups.py`
- Test: `tests/test_setups.py`

- [ ] **Step 1: Write the failing test**

```python
# adicionar a tests/test_setups.py
from backend.domain.setups import pullback_media, detectar_setups


class TestPullbackEDetectar:
    def test_pullback_em_alta_tocando_ema9(self):
        df = _df([(10, 11, 9, 10), (11, 12, 10, 11), (11, 12, 10.5, 11)])
        df["ema9"] = [9, 10, 11]
        df["ema21"] = [8, 9, 10]      # ema9 > ema21 → tendência de alta
        df["atr"] = [1.0, 1.0, 1.0]
        r = pullback_media(df)
        assert r.status == "ativo" and r.vies == "alta"

    def test_detectar_retorna_todos_os_setups(self):
        df = _df([(10, 11, 9, 10)] * 5)
        df["ema9"] = [9, 9.5, 10, 10.5, 11]
        df["ema21"] = [8, 8.5, 9, 9.5, 10]
        df["atr"] = [1.0] * 5
        df["resistencia_20"] = [11] * 5
        df["suporte_20"] = [8] * 5
        nomes = [s.nome for s in detectar_setups(df)]
        assert nomes == [
            "Larry 9.1", "Larry 9.2", "Larry 9.3", "Inside Bar",
            "Rompimento 20", "Engolfo", "Pin Bar", "Doji", "Pullback MME9/21",
        ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_setups.py::TestPullbackEDetectar -v`
Expected: FAIL com `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar a backend/domain/setups.py
def pullback_media(df: pd.DataFrame) -> SetupResult:
    """Reentrada a favor da tendência após repique à MME9 ou MME21."""
    nome = "Pullback MME9/21"
    if len(df) < 1 or "ema9" not in df.columns or "ema21" not in df.columns:
        return SetupResult(nome, "inativo", "neutro", "Dados insuficientes.")
    ema9 = float(df["ema9"].iloc[-1]); ema21 = float(df["ema21"].iloc[-1])
    high = float(df["High"].iloc[-1]); low = float(df["Low"].iloc[-1]); close = float(df["Close"].iloc[-1])
    atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else (high - low)
    tocou9 = low <= ema9 <= high or abs(close - ema9) < 0.5 * atr
    tocou21 = low <= ema21 <= high or abs(close - ema21) < 0.5 * atr
    if ema9 > ema21 and (tocou9 or tocou21):
        return SetupResult(nome, "ativo", "alta", "Pullback à média em tendência de alta — reentrada compradora.")
    if ema9 < ema21 and (tocou9 or tocou21):
        return SetupResult(nome, "ativo", "baixa", "Repique à média em tendência de baixa — reentrada vendedora.")
    return SetupResult(nome, "inativo", "neutro", "Preço longe das médias 9/21.")


def detectar_setups(df: pd.DataFrame) -> list[SetupResult]:
    """Executa todos os detectores na ordem canônica de exibição."""
    return [
        larry_91(df), larry_92(df), larry_93(df),
        inside_bar(df), rompimento(df),
        engolfo(df), pin_bar(df), doji(df),
        pullback_media(df),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_setups.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/setups.py tests/test_setups.py
git commit -m "feat(setups): Pullback MME9/21 e agregador detectar_setups"
```

---

## Task 6: Endpoint `GET /market/indicators/{ticker}`

**Files:**
- Modify: `backend/api/routers/market.py`
- Test: `tests/test_market_analysis.py`

- [ ] **Step 1: Write the failing test**

```python
# adicionar a tests/test_market_analysis.py
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def _fake_df(n=120, base=40.0):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    rng = np.random.default_rng(7)
    close = base * np.cumprod(1 + rng.normal(0.0, 0.012, n))
    high = close * 1.01; low = close * 0.99; open_ = close * 1.001
    vol = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


def test_indicators_endpoint_payload(monkeypatch):
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: _fake_df())
    monkeypatch.setattr(m, "_fetch_chain", lambda t: [])  # sem chain → iv_atm null
    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    data = r.json()
    for key in ["ticker", "preco_atual", "rsi14", "adx", "atr14", "vwap",
                "vwap_dist_pct", "expected_move", "faixa_1sigma", "dte_proximo_venc",
                "iv_atm", "vol_read", "setups", "faixa_52s_min", "faixa_52s_max"]:
        assert key in data, f"faltando {key}"
    assert isinstance(data["setups"], list) and len(data["setups"]) == 9
    assert data["iv_atm"] is None
    assert data["vol_read"] in ("premio_gordo", "premio_barato", "neutro", "indisponivel")


def test_indicators_404_sem_dados(monkeypatch):
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: pd.DataFrame())
    r = client.get("/market/indicators/XXXX")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_analysis.py::test_indicators_endpoint_payload -v`
Expected: FAIL com 404/`Not Found` (rota inexistente)

- [ ] **Step 3: Write minimal implementation**

Adicionar import no topo de `backend/api/routers/market.py` (junto aos outros):

```python
from backend.domain.indicators import calcular_indicadores
from backend.domain.setups import detectar_setups
from backend.domain.options_math import estimar_iv_historica, mes_vencimento_ideal
from backend.domain.greeks import implied_volatility
```

(Se `calcular_indicadores`/`estimar_iv_historica` já estiverem importados, não duplicar.)

Adicionar o endpoint ao final do arquivo:

```python
@router.get("/indicators/{ticker}")
def get_market_indicators(ticker: str):
    """Indicadores técnicos + setups de price action + leitura de vol para a
    sub-página 'Indicadores e Setup'. Contrato: IndicatorsPayload (ver spec)."""
    import math
    import backend.api.routers.market as _self

    df = _self._fetch_historical_with_fallback(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' não encontrado.")
    if len(df) < 60:
        raise HTTPException(status_code=422, detail=f"Dados insuficientes para '{ticker}'.")

    ind = calcular_indicadores(df)
    close = ind["Close"]
    preco_atual = float(close.iloc[-1])

    def _last(col: str, default: float = 0.0) -> float:
        if col in ind.columns:
            v = float(ind[col].iloc[-1])
            return v if not math.isnan(v) else default
        return default

    def _sma(series, window):
        return float(series.rolling(window).mean().iloc[-1]) if len(series) >= window else float(series.mean())

    ma20, ma50 = _sma(close, 20), _sma(close, 50)
    ma200 = _sma(close, 200) if len(close) >= 200 else _sma(close, len(close))

    hv_20 = _self.estimar_iv_historica(df, janela=20)
    hv_60 = _self.estimar_iv_historica(df, janela=60)
    log_ret = np.log(close / close.shift(1)).dropna()
    sigma_20 = float(log_ret.tail(20).std() * np.sqrt(252)) if len(log_ret) >= 20 else hv_20

    bb_mid = close.rolling(20).mean(); bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std; bb_lo = bb_mid - 2 * bb_std
    rng_bb = float((bb_up - bb_lo).iloc[-1])
    bollinger_pct_b = float((preco_atual - float(bb_lo.iloc[-1])) / rng_bb) if rng_bb > 0 else 0.5
    z_score_20 = float((preco_atual - ma20) / (sigma_20 + 1e-9)) if sigma_20 > 0 else 0.0

    vwap = _last("vwap", preco_atual)
    vwap_dist_pct = (preco_atual - vwap) / vwap * 100 if vwap else 0.0

    ult252 = close.tail(252)
    faixa_min, faixa_max = float(ult252.min()), float(ult252.max())

    # --- Expected move (base HV) e DTE do próximo vencimento ---
    try:
        _, _, dte = mes_vencimento_ideal()  # dte em dias úteis
        if not dte or dte <= 0:
            dte = 21
    except Exception:
        dte = 21
    em = preco_atual * sigma_20 * math.sqrt(max(dte, 1) / 252)
    faixa_1sigma = [round(preco_atual - em, 2), round(preco_atual + em, 2)]

    # --- IV ATM via chain (degrada para null) ---
    iv_atm = None
    iv_hv_ratio = None
    vol_read = "indisponivel"
    try:
        chain = _self._fetch_chain(ticker)
        atm = _atm_iv_from_chain(chain, preco_atual, dte)
        if atm is not None:
            iv_atm = round(atm, 4)
            iv_hv_ratio = round(iv_atm / hv_20, 2) if hv_20 > 0 else None
    except Exception:
        iv_atm = None
    if iv_atm is not None and hv_20 > 0:
        ratio = iv_atm / hv_20
        vol_read = "premio_gordo" if ratio > 1.2 else "premio_barato" if ratio < 0.9 else "neutro"

    setups = [
        {"nome": s.nome, "status": s.status, "vies": s.vies, "descricao": s.descricao}
        for s in detectar_setups(ind)
    ]

    return {
        "ticker": ticker.upper(),
        "preco_atual": round(preco_atual, 2),
        "hora": pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%H:%M"),
        "rsi14": _last("rsi", 50.0) if "rsi" in ind.columns else round(_self._rsi_manual(close, 14).iloc[-1], 2),
        "stoch_k": _last("stoch_k", 50.0),
        "stoch_d": _last("stoch_d", 50.0),
        "vol_ratio": round(_last("vol_ratio", 1.0), 2),
        "ma20": round(ma20, 2), "ma50": round(ma50, 2), "ma200": round(ma200, 2),
        "adx": round(_last("adx", 0.0), 2),
        "macd_diff": round(_last("macd_diff", 0.0), 4),
        "bollinger_pct_b": round(bollinger_pct_b, 4),
        "z_score_20": round(z_score_20, 4),
        "atr14": round(_last("atr", 0.0), 4),
        "vwap": round(vwap, 2),
        "vwap_dist_pct": round(vwap_dist_pct, 2),
        "hv_20": round(hv_20, 4), "hv_60": round(hv_60, 4),
        "sigma_20": round(sigma_20, 4),
        "expected_move": round(em, 2),
        "expected_move_pct": round(em / preco_atual * 100, 2),
        "faixa_1sigma": faixa_1sigma,
        "dte_proximo_venc": dte,
        "iv_atm": iv_atm,
        "iv_hv_ratio": iv_hv_ratio,
        "vol_read": vol_read,
        "faixa_52s_min": round(faixa_min, 2),
        "faixa_52s_max": round(faixa_max, 2),
        "setups": setups,
    }


def _atm_iv_from_chain(chain: list, spot: float, dte: int):
    """IV ATM a partir da chain bruta da opcoes.net. Retorna None se não der.

    Estrutura por linha (op[:10]): ticker, _, tipo, _, _, strike, _, _, preco, negocios.
    A data de vencimento não está nesse slice — sem ela, usamos dte (estimado, dias
    úteis) e o strike mais próximo do spot. Se a inversão de IV falhar, retorna None.
    """
    if not chain:
        return None
    melhores = []
    for op in chain:
        if len(op) < 10:
            continue
        _, _, tipo, _, _, strike, _, _, preco, neg = op[:10]
        try:
            strike = float(strike); preco = float(preco)
        except (TypeError, ValueError):
            continue
        if tipo not in ("CALL", "PUT") or preco <= 0.01:
            continue
        melhores.append((abs(strike - spot), tipo, strike, preco))
    if not melhores:
        return None
    melhores.sort(key=lambda x: x[0])
    _, tipo, strike, preco = melhores[0]
    try:
        T = max(dte, 1) / 252  # dte em dias úteis → anos
        # greeks.implied_volatility(S, K, T, market_price, opt_type)
        iv = implied_volatility(spot, strike, T, preco, tipo.upper())
        # Newton retorna sigma_init (0.5) em casos degenerados; trate como inválido se ~0.5 exato
        return float(iv) if iv and 0.01 < iv < 4.99 else None
    except Exception:
        return None
```

> **Nota de integração (confirmado no código):**
> 1. `mes_vencimento_ideal()` existe em `backend/domain/options_math.py` e retorna `(mes, ano, dte)` com `dte` em **dias úteis** — usar direto (já no código acima).
> 2. `implied_volatility(S, K, T, market_price, opt_type)` existe em `backend/domain/greeks.py` (Newton-Raphson; `opt_type` em maiúsculas; `T` em anos). Já usado em `_atm_iv_from_chain`. Em casos degenerados retorna `sigma_init`; o guard `0.01 < iv < 4.99` filtra valores não confiáveis.
> 3. `_rsi_manual` já é usado no arquivo; `calcular_indicadores` adiciona a coluna `rsi` — preferir a coluna.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market_analysis.py::test_indicators_endpoint_payload tests/test_market_analysis.py::test_indicators_404_sem_dados -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/routers/market.py tests/test_market_analysis.py
git commit -m "feat(market): endpoint /market/indicators com indicadores, setups e leitura de vol"
```

---

## Task 7: Tipos e hook no frontend

**Files:**
- Create: `src/lib/types/indicators.ts`
- Create: `src/hooks/useIndicators.ts`

- [ ] **Step 1: Criar o tipo do payload**

```ts
// src/lib/types/indicators.ts
export type SetupStatus = 'ativo' | 'armado' | 'inativo';
export type SetupVies = 'alta' | 'baixa' | 'neutro';

export interface SetupItem {
  nome: string;
  status: SetupStatus;
  vies: SetupVies;
  descricao: string;
}

export type VolRead = 'premio_gordo' | 'premio_barato' | 'neutro' | 'indisponivel';

export interface IndicatorsPayload {
  ticker: string;
  preco_atual: number;
  hora: string;
  rsi14: number;
  stoch_k: number;
  stoch_d: number;
  vol_ratio: number;
  ma20: number; ma50: number; ma200: number;
  adx: number;
  macd_diff: number;
  bollinger_pct_b: number;
  z_score_20: number;
  atr14: number;
  vwap: number;
  vwap_dist_pct: number;
  hv_20: number; hv_60: number;
  sigma_20: number;
  expected_move: number;
  expected_move_pct: number;
  faixa_1sigma: [number, number];
  dte_proximo_venc: number;
  iv_atm: number | null;
  iv_hv_ratio: number | null;
  vol_read: VolRead;
  faixa_52s_min: number;
  faixa_52s_max: number;
  setups: SetupItem[];
}
```

- [ ] **Step 2: Verificar a base URL da API**

Run: `rg "API_BASE|NEXT_PUBLIC_API|baseURL|fetch\(`" src/hooks/useAssetAnalysis.ts src/lib/api.ts -n`
Expected: localizar como `useAssetAnalysis` monta a URL (reusar o mesmo padrão).

- [ ] **Step 3: Criar o hook (espelhando useAssetAnalysis)**

```ts
// src/hooks/useIndicators.ts
import { useState, useEffect } from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';

// Reusar a mesma constante de base da API que useAssetAnalysis usa.
// Ajustar o import/const conforme o padrão encontrado no Step 2.
import { API_BASE } from '@/lib/api';

export function useIndicators(ticker: string | null) {
  const [data, setData] = useState<IndicatorsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) { setData(null); setError(null); return; }
    let cancel = false;
    setLoading(true); setError(null);
    fetch(`${API_BASE}/market/indicators/${encodeURIComponent(ticker)}`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail || `Erro ${r.status}`);
        }
        return r.json();
      })
      .then((d: IndicatorsPayload) => { if (!cancel) setData(d); })
      .catch((e: Error) => { if (!cancel) { setError(e.message); setData(null); } })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [ticker]);

  return { data, loading, error };
}
```

> Se `API_BASE` não for exportado de `src/lib/api.ts`, replicar a mesma derivação usada por `useAssetAnalysis` (mesmo env var). Conferir no Step 2.

- [ ] **Step 4: Typecheck**

Run: `npx tsc --noEmit`
Expected: sem erros nos arquivos novos.

- [ ] **Step 5: Commit**

```bash
git add src/lib/types/indicators.ts src/hooks/useIndicators.ts
git commit -m "feat(indicadores): tipos e hook useIndicators"
```

---

## Task 8: Narrativa/valuation (regras puras) + testes

**Files:**
- Create: `src/lib/indicators-narrative.ts`
- Create: `src/lib/__tests__/indicators-narrative.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/lib/__tests__/indicators-narrative.test.ts
import { describe, it, expect } from 'vitest';
import { tendenciaLabel, momentoLabel, tecnicaLabel, volReadLabel } from '@/lib/indicators-narrative';
import type { IndicatorsPayload } from '@/lib/types/indicators';

const base: IndicatorsPayload = {
  ticker: 'PETR4', preco_atual: 41.65, hora: '15:42',
  rsi14: 17.9, stoch_k: 17, stoch_d: 11, vol_ratio: 2.3,
  ma20: 43.4, ma50: 46.2, ma200: 40.9, adx: 60.6, macd_diff: -0.18,
  bollinger_pct_b: 0.23, z_score_20: -2.1, atr14: 1.12, vwap: 41.3, vwap_dist_pct: 0.8,
  hv_20: 0.31, hv_60: 0.30, sigma_20: 0.30, expected_move: 2.8, expected_move_pct: 6.7,
  faixa_1sigma: [38.85, 44.45], dte_proximo_venc: 26, iv_atm: 0.42, iv_hv_ratio: 1.35,
  vol_read: 'premio_gordo', faixa_52s_min: 36, faixa_52s_max: 47, setups: [],
};

describe('indicators-narrative', () => {
  it('momento sobrevendido quando RSI < 30', () => {
    expect(momentoLabel(base)).toBe('sobrevendido');
  });
  it('tendência baixa forte quando ADX alto e preço abaixo das médias curtas', () => {
    expect(tendenciaLabel(base)).toBe('baixa forte');
  });
  it('técnica "faca caindo" em baixa forte + sobrevendido', () => {
    expect(tecnicaLabel(base)).toBe('faca caindo');
  });
  it('vol read favorece venda de prêmio quando prêmio gordo', () => {
    expect(volReadLabel('premio_gordo')).toContain('vender');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/__tests__/indicators-narrative.test.ts`
Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Write minimal implementation**

```ts
// src/lib/indicators-narrative.ts
import type { IndicatorsPayload, VolRead } from '@/lib/types/indicators';

export function momentoLabel(p: IndicatorsPayload): string {
  if (p.rsi14 < 30) return 'sobrevendido';
  if (p.rsi14 > 70) return 'sobrecomprado';
  return 'neutro';
}

export function tendenciaLabel(p: IndicatorsPayload): string {
  const abaixoCurtas = p.preco_atual < p.ma20 && p.preco_atual < p.ma50;
  const acimaCurtas = p.preco_atual > p.ma20 && p.preco_atual > p.ma50;
  const forte = p.adx >= 25;
  if (abaixoCurtas) return forte ? 'baixa forte' : 'baixa';
  if (acimaCurtas) return forte ? 'alta forte' : 'alta';
  return 'lateral';
}

export function tecnicaLabel(p: IndicatorsPayload): string {
  const tend = tendenciaLabel(p);
  const mom = momentoLabel(p);
  if (tend === 'baixa forte' && mom === 'sobrevendido') return 'faca caindo';
  if (tend === 'alta forte' && mom === 'sobrecomprado') return 'esticado';
  if (tend.startsWith('alta')) return 'compradora';
  if (tend.startsWith('baixa')) return 'vendedora';
  return 'indefinida';
}

export function volReadLabel(v: VolRead): string {
  switch (v) {
    case 'premio_gordo': return 'IV elevada — favorece vender prêmio';
    case 'premio_barato': return 'IV baixa — favorece comprar prêmio';
    case 'neutro': return 'IV em linha com a histórica';
    default: return 'IV indisponível — leitura baseada em HV';
  }
}

export function resumo(p: IndicatorsPayload): string {
  const mom = momentoLabel(p);
  const tend = tendenciaLabel(p);
  const vol = volReadLabel(p.vol_read);
  const reversao = (mom === 'sobrevendido' && tend.includes('baixa'))
    || (mom === 'sobrecomprado' && tend.includes('alta')) ? ' — sinal de reversão prematuro' : '';
  return `${cap(mom)} em tendência de ${tend}${reversao}. ${vol}.`;
}

function cap(s: string): string { return s.charAt(0).toUpperCase() + s.slice(1); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/__tests__/indicators-narrative.test.ts`
Expected: PASS (4 testes)

- [ ] **Step 5: Commit**

```bash
git add src/lib/indicators-narrative.ts src/lib/__tests__/indicators-narrative.test.ts
git commit -m "feat(indicadores): regras de narrativa (momento/tendência/técnica/vol)"
```

---

## Task 9: Primitivos de gauge

**Files:**
- Create: `src/components/indicators/Gauges.tsx`

- [ ] **Step 1: Criar os primitivos**

```tsx
// src/components/indicators/Gauges.tsx
'use client';

import React from 'react';

const GREEN = 'var(--dw-green)';
const RED = 'var(--dw-red)';
const BLUE = 'var(--dw-blue)';

/** Gauge 0–100 com 3 zonas (verde/amarelo/vermelho) e marcador. */
export function ZoneGauge({
  label, value, display, lowPct = 30, highPct = 70, color,
}: { label: string; value: number; display: string; lowPct?: number; highPct?: number; color?: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <span>{label}</span>
        <span style={{ fontWeight: 700, color: color ?? 'var(--dw-ink)' }}>{display}</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, overflow: 'hidden', background: 'var(--dw-rule)' }}>
        <div style={{ position: 'absolute', inset: 0, left: 0, width: `${lowPct}%`, background: 'rgba(16,185,129,0.25)' }} />
        <div style={{ position: 'absolute', inset: 0, left: `${lowPct}%`, width: `${highPct - lowPct}%`, background: 'rgba(245,158,11,0.20)' }} />
        <div style={{ position: 'absolute', inset: 0, left: `${highPct}%`, width: `${100 - highPct}%`, background: 'rgba(239,68,68,0.25)' }} />
        <div style={{
          position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
          height: 14, width: 14, borderRadius: '50%', background: BLUE,
          border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)', left: `${pct}%`,
        }} />
      </div>
    </div>
  );
}

/** Linha rótulo→valor simples. */
export function StatRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
      <span style={{ color: 'var(--dw-ink-muted)', fontSize: 12 }}>{label}</span>
      <span style={{ fontWeight: 700, color: color ?? 'var(--dw-ink)' }}>{value}</span>
    </div>
  );
}

/** Chip colorido para MAs (% acima/abaixo). */
export function MaChip({ label, pct }: { label: string; pct: number }) {
  const positive = pct >= 0;
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600,
      background: positive ? '#FEE2E2' : '#D1FAE5',
      color: positive ? '#991B1B' : '#065F46',
    }}>
      {label} {positive ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}

export { GREEN, RED, BLUE };
```

- [ ] **Step 2: Typecheck**

Run: `npx tsc --noEmit`
Expected: sem erros.

- [ ] **Step 3: Commit**

```bash
git add src/components/indicators/Gauges.tsx
git commit -m "feat(indicadores): primitivos de gauge (ZoneGauge, StatRow, MaChip)"
```

---

## Task 10: Painéis de indicadores

**Files:**
- Create: `src/components/indicators/IndicatorPanels.tsx`

- [ ] **Step 1: Criar os 4 painéis**

```tsx
// src/components/indicators/IndicatorPanels.tsx
'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { ZoneGauge, StatRow, MaChip } from './Gauges';

const sectionStyle: React.CSSProperties = {
  background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule-soft)',
  borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
};
const titleStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase',
  letterSpacing: '0.1em', margin: 0,
};

export function MomentoPanel({ p }: { p: IndicatorsPayload }) {
  const rsiColor = p.rsi14 < 30 ? 'var(--dw-green)' : p.rsi14 > 70 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Momento</p>
      <ZoneGauge label="RSI 14" value={p.rsi14} display={p.rsi14.toFixed(1)} color={rsiColor} />
      <ZoneGauge label="Stochastic K/D" value={p.stoch_k} display={`K ${p.stoch_k.toFixed(0)} / D ${p.stoch_d.toFixed(0)}`} lowPct={20} highPct={80} />
      <StatRow label="Volume rel. 20d" value={`${p.vol_ratio.toFixed(1)}×`} color={p.vol_ratio >= 1.5 ? 'var(--dw-green)' : undefined} />
    </div>
  );
}

export function TendenciaPanel({ p }: { p: IndicatorsPayload }) {
  const maPct = (ma: number) => ((p.preco_atual - ma) / ma) * 100;
  const adxColor = p.adx >= 25 ? 'var(--dw-blue)' : 'var(--dw-ink-muted)';
  const adxLabel = p.adx < 25 ? 'lateral' : p.adx < 50 ? 'tendência' : 'tendência forte';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Tendência</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        <MaChip label="MA20" pct={maPct(p.ma20)} />
        <MaChip label="MA50" pct={maPct(p.ma50)} />
        <MaChip label="MA200" pct={maPct(p.ma200)} />
      </div>
      <StatRow label="ADX 14" value={`${p.adx.toFixed(1)} — ${adxLabel}`} color={adxColor} />
      <StatRow label="MACD (hist.)" value={`${p.macd_diff > 0 ? '+' : ''}${p.macd_diff.toFixed(3)}`} color={p.macd_diff >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
    </div>
  );
}

export function ReversaoPanel({ p }: { p: IndicatorsPayload }) {
  const zColor = p.z_score_20 < -1 ? 'var(--dw-green)' : p.z_score_20 > 1 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Reversão</p>
      <ZoneGauge label="Bollinger %B" value={p.bollinger_pct_b * 100} display={`${(p.bollinger_pct_b * 100).toFixed(0)}%`} lowPct={20} highPct={80} />
      <StatRow label="Z-Score vs MA20" value={p.z_score_20.toFixed(2)} color={zColor} />
      <StatRow label="ATR 14" value={`R$ ${p.atr14.toFixed(2)} (${(p.atr14 / p.preco_atual * 100).toFixed(1)}%)`} />
      <StatRow label="Distância do VWAP" value={`${p.vwap_dist_pct > 0 ? '+' : ''}${p.vwap_dist_pct.toFixed(1)}%`} color={p.vwap_dist_pct >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
    </div>
  );
}

export function VolatilidadePanel({ p }: { p: IndicatorsPayload }) {
  const ivTxt = p.iv_atm != null ? `${(p.iv_atm * 100).toFixed(0)}%` : '—';
  const ratioTxt = p.iv_hv_ratio != null ? `${p.iv_hv_ratio.toFixed(2)}×` : 'indisponível';
  return (
    <div style={{ ...sectionStyle, border: '1.5px solid var(--dw-blue)' }}>
      <p style={titleStyle}>Volatilidade</p>
      <StatRow label="IV ATM × HV20" value={`${ivTxt} vs ${(p.hv_20 * 100).toFixed(0)}%`} />
      <StatRow label="IV / HV" value={ratioTxt} color="var(--dw-blue)" />
      <StatRow label="σ20 anualizada" value={`${(p.sigma_20 * 100).toFixed(0)}%`} />
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `npx tsc --noEmit`
Expected: sem erros.

- [ ] **Step 3: Commit**

```bash
git add src/components/indicators/IndicatorPanels.tsx
git commit -m "feat(indicadores): painéis Momento/Tendência/Reversão/Volatilidade"
```

---

## Task 11: SetupsGrid, VolReadCard, ComingSoonPanel, Header

**Files:**
- Create: `src/components/indicators/SetupsGrid.tsx`
- Create: `src/components/indicators/VolReadCard.tsx`
- Create: `src/components/indicators/ComingSoonPanel.tsx`
- Create: `src/components/indicators/IndicatorsHeader.tsx`

- [ ] **Step 1: SetupsGrid**

```tsx
// src/components/indicators/SetupsGrid.tsx
'use client';

import React from 'react';
import type { SetupItem } from '@/lib/types/indicators';

const STATUS_STYLE: Record<string, { bg: string; color: string; border: string; label: string }> = {
  ativo:   { bg: '#D1FAE5', color: '#065F46', border: '#6EE7B7', label: 'ativo' },
  armado:  { bg: '#FEF3C7', color: '#92400E', border: '#FCD34D', label: 'armado' },
  inativo: { bg: '#F1F5F9', color: '#64748B', border: '#E2E8F0', label: 'inativo' },
};
const VIES_COLOR: Record<string, string> = { alta: 'var(--dw-green)', baixa: 'var(--dw-red)', neutro: 'var(--dw-ink-muted)' };

export function SetupsGrid({ setups }: { setups: SetupItem[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
      {setups.map((s) => {
        const st = STATUS_STYLE[s.status] ?? STATUS_STYLE.inativo;
        const dim = s.status === 'inativo';
        return (
          <div key={s.nome} style={{
            background: 'var(--dw-white)', border: '1px solid var(--dw-rule)', borderRadius: 10,
            padding: 12, opacity: dim ? 0.6 : 1, display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 700, fontSize: 13, color: VIES_COLOR[s.vies] }}>{s.nome}</span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: st.bg, color: st.color, border: `1px solid ${st.border}` }}>{st.label}</span>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--dw-ink-muted)', lineHeight: 1.4 }}>{s.descricao}</p>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: VolReadCard**

```tsx
// src/components/indicators/VolReadCard.tsx
'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { volReadLabel } from '@/lib/indicators-narrative';

export function VolReadCard({ p }: { p: IndicatorsPayload }) {
  const [lo, hi] = p.faixa_1sigma;
  return (
    <div style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule-soft)', borderRadius: 10, padding: 16 }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 10px' }}>
        Leitura para opções
      </p>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
        <span style={{ color: 'var(--dw-ink-muted)' }}>Expected move ({p.dte_proximo_venc}d)</span>
        <span style={{ fontWeight: 700 }}>±R$ {p.expected_move.toFixed(2)} (±{p.expected_move_pct.toFixed(1)}%)</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)', marginBottom: 8 }}>
        <span>Faixa ±1σ</span>
        <span>R$ {lo.toFixed(2)} — R$ {hi.toFixed(2)}</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--dw-ink)', borderTop: '1px solid var(--dw-rule-soft)', paddingTop: 8 }}>
        {volReadLabel(p.vol_read)}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: ComingSoonPanel**

```tsx
// src/components/indicators/ComingSoonPanel.tsx
'use client';

import React from 'react';

export function ComingSoonPanel({ title, itens }: { title: string; itens: string[] }) {
  return (
    <div style={{ background: 'var(--dw-bg-soft)', border: '1px dashed var(--dw-rule)', borderRadius: 10, padding: 16, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-ink-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>{title}</p>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: '#EEF2FF', color: 'var(--dw-blue)', border: '1px solid #C7D2FE' }}>em breve</span>
      </div>
      <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--dw-ink-muted)', fontSize: 12, lineHeight: 1.7 }}>
        {itens.map((i) => <li key={i}>{i}</li>)}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: IndicatorsHeader**

```tsx
// src/components/indicators/IndicatorsHeader.tsx
'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { tecnicaLabel, resumo } from '@/lib/indicators-narrative';

export function IndicatorsHeader({ p, valuationScore }: { p: IndicatorsPayload; valuationScore: number }) {
  const valLabel = valuationScore >= 7 ? 'descontado' : valuationScore >= 4 ? 'neutro' : 'caro';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--dw-ink)' }}>{p.ticker}</h3>
        <span style={{ fontSize: 15, color: 'var(--dw-ink-muted)' }}>R$ {p.preco_atual.toFixed(2)}</span>
        <span style={{ fontSize: 12, color: 'var(--dw-ink-muted)' }}>🕐 {p.hora}</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 8, background: '#ECFDF5', color: '#065F46', border: '1px solid #A7F3D0' }}>
          Valuation: {valLabel} {valuationScore}/10
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 8, background: '#FFF7ED', color: '#9A3412', border: '1px solid #FED7AA' }}>
          Técnica: {tecnicaLabel(p)}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: 14, color: 'var(--dw-ink-light)' }}>{resumo(p)}</p>
    </div>
  );
}
```

- [ ] **Step 5: Typecheck + Commit**

Run: `npx tsc --noEmit`
Expected: sem erros.

```bash
git add src/components/indicators/SetupsGrid.tsx src/components/indicators/VolReadCard.tsx src/components/indicators/ComingSoonPanel.tsx src/components/indicators/IndicatorsHeader.tsx
git commit -m "feat(indicadores): SetupsGrid, VolReadCard, ComingSoonPanel e Header"
```

---

## Task 12: Página `/analytics/indicadores` + link em `/analytics`

**Files:**
- Create: `src/app/analytics/indicadores/page.tsx`
- Modify: `src/app/analytics/page.tsx`

- [ ] **Step 1: Conferir a assinatura de `scoreAsset`**

Run: `rg "export function scoreAsset" src/lib/asset-analysis.ts -n -A2`
Expected: confirmar que aceita um objeto com `preco_atual, ma20, ma50, rsi14, bollinger_pct_b, z_score_20, faixa_52s_min, faixa_52s_max`. O `IndicatorsPayload` contém todos esses campos; se o tipo do parâmetro for `AssetAnalysisPayload` (mais amplo), montar um objeto compatível incluindo `chain: []` e os demais campos presentes no payload.

- [ ] **Step 2: Criar a página**

```tsx
// src/app/analytics/indicadores/page.tsx
'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Search, ArrowLeft } from 'lucide-react';
import { useIndicators } from '@/hooks/useIndicators';
import { scoreAsset } from '@/lib/asset-analysis';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';
import { IndicatorsHeader } from '@/components/indicators/IndicatorsHeader';
import { MomentoPanel, TendenciaPanel, ReversaoPanel, VolatilidadePanel } from '@/components/indicators/IndicatorPanels';
import { SetupsGrid } from '@/components/indicators/SetupsGrid';
import { VolReadCard } from '@/components/indicators/VolReadCard';
import { ComingSoonPanel } from '@/components/indicators/ComingSoonPanel';

export default function IndicadoresPage() {
  const [input, setInput] = useState('PETR4');
  const [ticker, setTicker] = useState<string | null>(null);
  const { data, loading, error } = useIndicators(ticker);

  const analisar = useCallback(() => {
    const t = input.trim().toUpperCase();
    if (t) setTicker(t);
  }, [input]);

  const valuation = data
    ? scoreAsset({ ...data, hv_20: data.hv_20, hv_60: data.hv_60, sigma_20: data.sigma_20, ma200: data.ma200, macd_diff: data.macd_diff, stoch_k: data.stoch_k, stoch_d: data.stoch_d, adx: data.adx, preco_graham: null, preco_dcf: null, chain: [] } as AssetAnalysisPayload).score
    : 0;

  return (
    <div className="main-content">
      <div className="page-header">
        <div>
          <Link href="/analytics" className="label mb-2 inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="w-3 h-3" /> Voltar para Analytics
          </Link>
          <h1 className="font-serif">Indicadores e Setup</h1>
          <p className="mt-2 text-dw-ink-light text-base max-w-2xl">
            Leitura técnica em tempo real do ativo e de suas opções: indicadores mais usados, setups de price action e leitura de volatilidade.
          </p>
        </div>
      </div>

      <div className="card mb-6">
        <div className="label mb-3">Selecionar ativo</div>
        <div className="flex gap-3 items-center flex-wrap">
          <input
            type="text" value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && analisar()}
            placeholder="Ex: PETR4, VALE3, BBAS3"
            className="rounded-lg px-3 py-2.5 text-sm font-mono w-44 focus:outline-none focus:ring-2"
            style={{ border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)', color: 'var(--dw-ink)', '--tw-ring-color': 'var(--dw-blue)' } as React.CSSProperties}
          />
          <button onClick={analisar} disabled={loading} className="btn-demo flex items-center gap-2 disabled:opacity-50" style={{ background: 'var(--dw-blue)' }}>
            {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Search className="w-4 h-4" />}
            Analisar
          </button>
          {error && <span style={{ fontSize: 13, color: 'var(--dw-red)' }}>{error}</span>}
        </div>
      </div>

      {!ticker && (
        <div className="card flex items-center justify-center" style={{ height: 120, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
          <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>Digite um ativo para ver a leitura de mercado.</p>
        </div>
      )}

      {data && (
        <div className="card mb-6">
          <IndicatorsHeader p={data} valuationScore={valuation} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <MomentoPanel p={data} />
            <TendenciaPanel p={data} />
            <ReversaoPanel p={data} />
            <VolatilidadePanel p={data} />
          </div>
        </div>
      )}

      {data && (
        <div className="card mb-6">
          <h3 className="font-serif text-lg mb-1">Setups de Price Action</h3>
          <p className="text-xs mb-4" style={{ color: 'var(--dw-ink-muted)' }}>Estado dos setups mais usados no candle mais recente (diário).</p>
          <SetupsGrid setups={data.setups} />
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <VolReadCard p={data} />
          <ComingSoonPanel title="Fluxo de opções" itens={['Open Interest por strike', 'Max Pain', 'Put/Call ratio (OI)']} />
          <ComingSoonPanel title="Fluxo B3 · Aluguel" itens={['Taxa de aluguel (BTC)', 'Short interest / days-to-cover']} />
          <ComingSoonPanel title="Estrutura de volatilidade" itens={['IV Rank 252d', 'Estrutura a termo de IV', 'Skew 25Δ']} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Adicionar link na página `/analytics`**

Em `src/app/analytics/page.tsx`, dentro do `page-header` (após o `<p>` da descrição, por volta da linha 137), adicionar:

```tsx
          <Link
            href="/analytics/indicadores"
            className="inline-flex items-center gap-1.5 mt-3 text-sm font-bold text-dw-blue hover:underline"
          >
            Indicadores e Setup →
          </Link>
```

E garantir o import no topo do arquivo:

```tsx
import Link from 'next/link';
```

- [ ] **Step 4: Typecheck**

Run: `npx tsc --noEmit`
Expected: sem erros. (Se `scoreAsset` reclamar de tipo, ajustar o objeto montado no `valuation` para conter todos os campos requeridos por `AssetAnalysisPayload`.)

- [ ] **Step 5: Commit**

```bash
git add src/app/analytics/indicadores/page.tsx src/app/analytics/page.tsx
git commit -m "feat(indicadores): página /analytics/indicadores e link em Analytics"
```

---

## Task 13: Verificação fim-a-fim

- [ ] **Step 1: Rodar a suíte backend de setups e endpoint**

Run: `python -m pytest tests/test_setups.py tests/test_market_analysis.py -v`
Expected: PASS

- [ ] **Step 2: Rodar a suíte frontend**

Run: `npx vitest run src/lib/__tests__/indicators-narrative.test.ts`
Expected: PASS

- [ ] **Step 3: Typecheck completo**

Run: `npx tsc --noEmit`
Expected: sem erros.

- [ ] **Step 4: Subir o app e validar visualmente**

Run: `npm run dev` (background) e abrir `http://localhost:3000/analytics/indicadores`, digitar PETR4.
Expected: cabeçalho com preço/badges/resumo; 4 painéis; grade de 9 setups; card "Leitura para opções"; 3 painéis "em breve". Conferir no console do servidor que `/analytics/indicadores` compila e a chamada a `/market/indicators/PETR4` retorna 200.

- [ ] **Step 5: Commit final (se houver ajustes)**

```bash
git add -A
git commit -m "chore(indicadores): ajustes de verificação fim-a-fim"
```

---

## Notas de risco / integração a resolver na execução

1. **Vencimento/DTE** — `mes_vencimento_ideal()` (em `backend/domain/options_math.py`) já fornece `dte` em dias úteis. Confirmado.
2. **Invertedor de IV** — `implied_volatility()` (em `backend/domain/greeks.py`) já existe e é usado por `_atm_iv_from_chain`. Confirmado. Se a chain vier vazia/sem strike utilizável, `iv_atm` degrada para `null` (spec prevê).
3. **`API_BASE`** no front — reusar exatamente o padrão de `useAssetAnalysis` (mesma env var/derivação).
4. **`scoreAsset`** — se o parâmetro exigir `AssetAnalysisPayload` completo, montar objeto compatível (já feito na Task 12 com `chain: []` e campos extras).
5. **Coluna `rsi`** — `calcular_indicadores` adiciona `rsi`; preferir a coluna ao `_rsi_manual`.
