"""
G-2 — Testes do endpoint GET /market/analysis/{ticker}.

Estratégia:
- fetch_brapi_historical e _fetch_chain mockados com unittest.mock.patch
  (thread-safe; o TestClient da FastAPI executa em thread separada)
- Patch nos nomes importados pelo router: backend.api.routers.market.*
- DataFrame sintético de 300 linhas
- Chain mockada com 3 opções (2 CALL + 1 PUT)
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_MOD = "backend.api.routers.market"

_REQUIRED_FIELDS = {
    "ticker", "preco_atual", "hv_20", "hv_60",
    "ma20", "ma50", "ma200", "sigma_20", "rsi14",
    "bollinger_pct_b", "z_score_20",
    "faixa_52s_min", "faixa_52s_max", "chain",
}

_CHAIN_MOCK = [
    # [ticker_op, _, tipo, _, _, strike, _, _, preco, negocios]
    ["PETRH400", None, "CALL", None, None, 40.0, None, None, 1.45, 320],
    ["PETRH380", None, "CALL", None, None, 38.0, None, None, 2.10, 180],
    ["PETRT400", None, "PUT",  None, None, 40.0, None, None, 1.20,  90],
]


def _make_synthetic_df(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """DataFrame OHLCV sintético com n linhas, retornos normalmente distribuídos."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    log_returns = rng.normal(0.0003, 0.018, size=n)
    close = 38.0 * np.exp(np.cumsum(log_returns))
    spread = close * 0.005
    high  = close + spread
    low   = close - spread
    open_ = close * (1 + rng.normal(0, 0.003, size=n))
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
    return df


# ---------------------------------------------------------------------------
# Testes felizes
# ---------------------------------------------------------------------------

def test_analysis_retorna_todos_campos():
    """Todos os campos do AssetAnalysisPayload devem estar presentes na resposta."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=_CHAIN_MOCK)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200, response.text
    data = response.json()
    assert _REQUIRED_FIELDS.issubset(data.keys()), (
        f"Campos ausentes: {_REQUIRED_FIELDS - data.keys()}"
    )


def test_analysis_campos_numericos_nao_nulos():
    """Todos os campos numéricos devem ser não-nulos e finitos."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=_CHAIN_MOCK)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    data = response.json()
    numeric_fields = _REQUIRED_FIELDS - {"ticker", "chain"}
    for field in numeric_fields:
        value = data[field]
        assert value is not None, f"Campo '{field}' é None"
        assert isinstance(value, (int, float)), f"Campo '{field}' não é numérico: {value!r}"
        assert np.isfinite(value), f"Campo '{field}' não é finito: {value}"


def test_analysis_ticker_correto_na_resposta():
    """O campo ticker deve refletir o ticker da requisição (uppercase)."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/petr4")

    assert response.status_code == 200
    assert response.json()["ticker"] == "PETR4"


def test_analysis_chain_mapeada_corretamente():
    """Os itens da chain devem ter strike, preco, tipo e negocios."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=_CHAIN_MOCK)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    chain = response.json()["chain"]
    assert len(chain) == 3
    for item in chain:
        assert set(item.keys()) == {"strike", "preco", "tipo", "negocios"}
        assert item["tipo"] in ("call", "put")
        assert item["strike"] > 0
        assert item["preco"] >= 0
        assert item["negocios"] >= 0


# ---------------------------------------------------------------------------
# Testes de erro
# ---------------------------------------------------------------------------

def test_analysis_ticker_invalido_retorna_404():
    """DataFrame vazio → HTTP 404."""
    with patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()):
        response = client.get("/market/analysis/TICKERINVALIDO")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_analysis_dados_insuficientes_retorna_422():
    """DataFrame com menos de 60 linhas → HTTP 422."""
    df_mock = _make_synthetic_df(n=30)
    with patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 422
    assert "insuficiente" in response.json()["detail"].lower()


def test_analysis_chain_vazia_nao_causa_500():
    """chain=[] não deve causar erro 500 — retorno gracioso com lista vazia."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    assert response.json()["chain"] == []


def test_analysis_chain_excecao_nao_causa_500():
    """Exceção em _fetch_chain → chain=[] sem 500."""
    df_mock = _make_synthetic_df(300)

    def _chain_raises(ticker):
        raise RuntimeError("API fora do ar")

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", side_effect=RuntimeError("API fora do ar"))):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    assert response.json()["chain"] == []


# ---------------------------------------------------------------------------
# Sanidade dos valores calculados
# ---------------------------------------------------------------------------

def test_analysis_faixa_52s_coerente():
    """faixa_52s_min <= preco_atual <= faixa_52s_max (para dados normais)."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    data = response.json()
    assert data["faixa_52s_min"] <= data["preco_atual"] <= data["faixa_52s_max"]


def test_analysis_rsi_no_intervalo():
    """RSI₁₄ deve estar entre 0 e 100."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/PETR4")

    rsi = response.json()["rsi14"]
    assert 0 <= rsi <= 100, f"RSI fora do intervalo: {rsi}"


def test_analysis_hv_positivo():
    """HV₂₀ e HV₆₀ devem ser positivos."""
    df_mock = _make_synthetic_df(300)
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/PETR4")

    data = response.json()
    assert data["hv_20"] > 0, "HV₂₀ deve ser positivo"
    assert data["hv_60"] > 0, "HV₆₀ deve ser positivo"


# ---------------------------------------------------------------------------
# Task 6: Endpoint /market/indicators/{ticker}
# ---------------------------------------------------------------------------

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
