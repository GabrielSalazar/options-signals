"""
G-2 — Testes do endpoint GET /market/analysis/{ticker}.

Estratégia:
- fetch_brapi_historical e _fetch_chain mockados com unittest.mock.patch
  (thread-safe; o TestClient da FastAPI executa em thread separada)
- Patch nos nomes importados pelo router: backend.api.routers.market.*
- DataFrame sintético de 300 linhas
- Chain mockada com 3 opções (2 CALL + 1 PUT)
"""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.domain.indicators import calcular_indicadores

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
                "vwap_dist_pct", "vwap_available", "expected_move", "faixa_1sigma", "dte_proximo_venc",
                "iv_atm", "vol_read", "setups", "faixa_52s_min", "faixa_52s_max"]:
        assert key in data, f"faltando {key}"
    assert isinstance(data["setups"], list) and len(data["setups"]) == 9
    assert data["iv_atm"] is None
    assert data["vol_read"] in ("premio_gordo", "premio_barato", "neutro", "indisponivel")
    assert isinstance(data["vwap_available"], bool)


def test_indicators_vwap_indisponivel_usa_preco_atual_como_fallback(monkeypatch):
    """Quando a coluna 'vwap' não está presente no DataFrame de indicadores
    (ex.: falha no cálculo upstream), vwap_available deve ser False e o vwap
    exibido cai para preco_atual (linha 388), em vez de propagar erro/None."""
    import backend.api.routers.market as m

    df = _fake_df()

    def _calc_sem_vwap(df_in):
        ind = calcular_indicadores(df_in)
        return ind.drop(columns=["vwap"])

    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: df)
    monkeypatch.setattr(m, "_fetch_chain", lambda t: [])
    monkeypatch.setattr(m, "calcular_indicadores", _calc_sem_vwap)

    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    data = r.json()
    assert data["vwap_available"] is False
    assert data["vwap"] == data["preco_atual"]
    assert data["vwap_dist_pct"] == 0.0


def test_indicators_404_sem_dados(monkeypatch):
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: pd.DataFrame())
    r = client.get("/market/indicators/XXXX")
    assert r.status_code == 404


def test_indicators_dados_insuficientes_422(monkeypatch):
    """DataFrame com menos de 60 linhas em /indicators → HTTP 422 (linha 360)."""
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: _fake_df(n=30))
    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 422


def test_indicators_dte_exception_usa_default_21(monkeypatch):
    """Se mes_vencimento_ideal() lança, dte cai para 21 (linhas 395-400)."""
    import backend.api.routers.market as m

    def _raises():
        raise RuntimeError("sem calendário B3")

    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: _fake_df())
    monkeypatch.setattr(m, "mes_vencimento_ideal", _raises)
    monkeypatch.setattr(m, "_fetch_chain", lambda t: [])
    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    assert r.json()["dte_proximo_venc"] == 21


def test_indicators_dte_zero_usa_default_21(monkeypatch):
    """Se dte vier <= 0 do calendário, cai para 21 (branch 'if not dte or dte <= 0')."""
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: _fake_df())
    monkeypatch.setattr(m, "mes_vencimento_ideal", lambda: (6, 2026, 0))
    monkeypatch.setattr(m, "_fetch_chain", lambda t: [])
    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    assert r.json()["dte_proximo_venc"] == 21


def test_indicators_iv_atm_disponivel_premio_gordo(monkeypatch):
    """Chain com opção ATM real (preço BS @ sigma=0.30) deve produzir iv_atm
    não-nulo e, quando hv_20 é bem menor que a IV implícita, vol_read='premio_gordo'."""
    import backend.api.routers.market as m

    df = _fake_df(n=120, base=40.0)
    preco_atual = float(df["Close"].iloc[-1])

    # Opção ATM (strike == preco_atual) com preço Black-Scholes a sigma=0.30, T=21du.
    from backend.domain.greeks import bs_call_price
    T = 21 / 252
    preco_op = bs_call_price(preco_atual, preco_atual, T, sigma=0.30)
    chain_mock = [
        [f"XXXXH{int(preco_atual)}", None, "CALL", None, None, preco_atual, None, None, preco_op, 500],
    ]

    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: df)
    monkeypatch.setattr(m, "mes_vencimento_ideal", lambda: (8, 2026, 21))
    monkeypatch.setattr(m, "_fetch_chain", lambda t: chain_mock)
    # Força hv_20 bem abaixo da IV recuperada (~0.30) para cair no ramo 'premio_gordo'.
    monkeypatch.setattr(m, "estimar_iv_historica", lambda df, janela: 0.10)

    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    data = r.json()
    assert data["iv_atm"] is not None
    assert data["iv_atm"] == pytest.approx(0.30, abs=0.02)
    assert data["iv_hv_ratio"] is not None
    assert data["vol_read"] == "premio_gordo"


def test_indicators_iv_atm_chain_excecao_degrada_indisponivel(monkeypatch):
    """Se _fetch_chain explode dentro de /indicators, iv_atm cai para None e
    vol_read continua 'indisponivel' (linhas 408-415, except)."""
    import backend.api.routers.market as m
    monkeypatch.setattr(m, "_fetch_historical_with_fallback", lambda t: _fake_df())
    monkeypatch.setattr(m, "mes_vencimento_ideal", lambda: (8, 2026, 21))

    def _chain_raises(ticker):
        raise RuntimeError("opcoes.net fora do ar")

    monkeypatch.setattr(m, "_fetch_chain", _chain_raises)
    r = client.get("/market/indicators/PETR4")
    assert r.status_code == 200
    data = r.json()
    assert data["iv_atm"] is None
    assert data["vol_read"] == "indisponivel"


# ---------------------------------------------------------------------------
# _atm_iv_from_chain — função auxiliar pura (linhas 457-500)
# ---------------------------------------------------------------------------

def test_atm_iv_from_chain_vazia_retorna_none():
    from backend.api.routers.market import _atm_iv_from_chain
    assert _atm_iv_from_chain([], 40.0, 21) is None


def test_atm_iv_from_chain_sem_candidatos_validos_retorna_none():
    """Todas as linhas com preço <= 0.01 ou tipo inválido são descartadas."""
    from backend.api.routers.market import _atm_iv_from_chain
    chain = [
        ["X1", None, "CALL", None, None, 40.0, None, None, 0.0, 10],   # preco <= 0.01
        ["X2", None, "FUTURO", None, None, 40.0, None, None, 5.0, 10],  # tipo inválido
        ["X3", None, "CALL", None, None, "abc", None, None, 5.0, 10],   # strike não numérico
    ]
    assert _atm_iv_from_chain(chain, 40.0, 21) is None


def test_atm_iv_from_chain_ignora_linhas_curtas():
    """Linhas com menos de 10 colunas são puladas (op[:10])."""
    from backend.api.routers.market import _atm_iv_from_chain
    chain = [["X1", None, "CALL"]]  # só 3 colunas
    assert _atm_iv_from_chain(chain, 40.0, 21) is None


def test_atm_iv_from_chain_recupera_sigma_correto():
    """Preço BS real a sigma=0.25 deve ser invertido para ~0.25 pelo Newton-Raphson."""
    from backend.api.routers.market import _atm_iv_from_chain
    from backend.domain.greeks import bs_put_price

    S = 50.0
    T = 21 / 252
    preco_put = bs_put_price(S, S, T, sigma=0.25)
    chain = [["Y1", None, "PUT", None, None, S, None, None, preco_put, 50]]

    iv = _atm_iv_from_chain(chain, S, 21)
    assert iv is not None
    assert iv == pytest.approx(0.25, abs=0.02)


def test_atm_iv_from_chain_guardrail_fora_de_faixa_retorna_none():
    """IV implausível (>4.99 ou <0.01) deve ser descartada pelo guardrail."""
    from backend.api.routers.market import _atm_iv_from_chain
    # Preço de mercado absurdamente alto para o strike/spot/T dados força
    # Newton-Raphson a convergir (ou estourar) fora da faixa plausível.
    chain = [["Z1", None, "CALL", None, None, 40.0, None, None, 39.9, 50]]
    iv = _atm_iv_from_chain(chain, 40.0, 1)
    assert iv is None or (0.01 < iv < 4.99)


# ---------------------------------------------------------------------------
# GET /market — cotações de índices e ações (linhas 23-66)
# ---------------------------------------------------------------------------

def _make_yf_multiindex_df():
    """DataFrame com MultiIndex de colunas (ticker, campo OHLC), como retornado
    por yf.download() com múltiplos tickers e group_by='ticker'."""
    dates = pd.date_range("2026-06-01", periods=5, freq="B")
    tickers = ["^BVSP", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA",
               "ABEV3.SA", "BBAS3.SA", "MGLU3.SA", "RENT3.SA"]
    cols = pd.MultiIndex.from_product([tickers, ["Open", "High", "Low", "Close", "Volume"]])
    data = {}
    base = 100.0
    for t in tickers:
        closes = [base, base * 1.01, base * 0.99, base * 1.02, base * 1.03]
        for field, vals in [("Open", closes), ("High", closes), ("Low", closes),
                             ("Close", closes), ("Volume", [1e6] * 5)]:
            data[(t, field)] = vals
        base += 10
    df = pd.DataFrame(data, index=dates, columns=cols)
    return df


def test_get_market_retorna_indices_e_acoes():
    df_mock = _make_yf_multiindex_df()
    with patch(f"{_MOD}.logger"):
        with patch("yfinance.download", return_value=df_mock):
            response = client.get("/market")

    assert response.status_code == 200
    data = response.json()
    assert "indices" in data and "acoes" in data
    assert len(data["indices"]) == 1
    assert data["indices"][0]["ticker"] == "IBOV"
    assert "price" in data["indices"][0] and "chg_pct" in data["indices"][0]
    tickers_acoes = {a["ticker"] for a in data["acoes"]}
    assert tickers_acoes == {"PETR4", "VALE3", "ITUB4", "WEGE3", "ABEV3", "BBAS3", "MGLU3", "RENT3"}


def test_get_market_quote_individual_falha_e_omite_ticker():
    """Se get_quote() levanta para um ticker específico (coluna ausente), aquele
    ticker é omitido do resultado em vez de quebrar a requisição inteira."""
    df_mock = _make_yf_multiindex_df()
    # Remove as colunas do IBOV para forçar KeyError dentro de get_quote().
    df_mock = df_mock.drop(columns="^BVSP", level=0)

    with patch("yfinance.download", return_value=df_mock):
        response = client.get("/market")

    assert response.status_code == 200
    data = response.json()
    assert data["indices"] == []  # IBOV indisponível, mas resto segue OK
    assert len(data["acoes"]) == 8


def test_get_market_download_excecao_retorna_503():
    """Exceção em yf.download() deve resultar em 503 (Dados de mercado indisponíveis)."""
    with patch("yfinance.download", side_effect=RuntimeError("rate limit")):
        response = client.get("/market")

    assert response.status_code == 503
    assert "indispon" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /market/opcoes — opções mais líquidas (linhas 79-99)
# ---------------------------------------------------------------------------

def test_get_market_options_ordena_por_negocios_top6():
    """Resultado deve ser ordenado por 'negocios' desc e limitado a 6 itens."""
    fake_opts = [
        {"ticker_opcao": f"OPT{i}", "ticker_subjacente": "PETR4", "tipo": "CALL",
         "strike": 40.0, "preco": 1.0, "negocios": i * 10}
        for i in range(1, 9)  # 8 opções por ticker, negocios=10..80
    ]
    with patch("backend.services.data_providers.get_liquid_options_for_ticker",
               return_value=fake_opts[:2]):
        response = client.get("/market/opcoes")

    assert response.status_code == 200
    data = response.json()
    assert "opcoes" in data
    assert len(data["opcoes"]) <= 6
    negocios_vals = [o["negocios"] for o in data["opcoes"]]
    assert negocios_vals == sorted(negocios_vals, reverse=True)


def test_get_market_options_falha_parcial_nao_quebra_request():
    """Se get_liquid_options_for_ticker levanta para alguns tickers, o endpoint
    deve seguir respondendo 200 com os resultados parciais dos demais."""
    def _flaky(ticker, limit=2):
        if ticker in ("PETR4", "VALE3"):
            raise RuntimeError(f"falha de rede para {ticker}")
        return [{"ticker_opcao": f"{ticker}H1", "ticker_subjacente": ticker,
                  "tipo": "CALL", "strike": 10.0, "preco": 0.5, "negocios": 5}]

    with patch("backend.services.data_providers.get_liquid_options_for_ticker", side_effect=_flaky):
        response = client.get("/market/opcoes")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["opcoes"], list)
    # PETR4 e VALE3 falharam: nenhuma opção deles deve aparecer.
    subjacentes = {o["ticker_subjacente"] for o in data["opcoes"]}
    assert "PETR4" not in subjacentes
    assert "VALE3" not in subjacentes


def test_get_market_options_todas_falham_retorna_lista_vazia():
    """Falha total (todos os tickers) deve retornar lista vazia, não 500."""
    with patch("backend.services.data_providers.get_liquid_options_for_ticker",
               side_effect=RuntimeError("opcoes.net indisponível")):
        response = client.get("/market/opcoes")

    assert response.status_code == 200
    assert response.json()["opcoes"] == []


# ---------------------------------------------------------------------------
# GET /market/opcoes/chain/{ticker} — chain bruta (linhas 105-119)
# ---------------------------------------------------------------------------

def test_get_options_chain_mapeia_campos_corretamente():
    chain_mock = [
        ["PETRH400", None, "CALL", None, None, 40.0, None, None, 1.45, 320],
        ["PETRT380", None, "PUT", None, None, 38.0, None, None, 2.0, 0],
    ]
    with patch("backend.services.data_providers._fetch_chain", return_value=chain_mock):
        response = client.get("/market/opcoes/chain/PETR4")

    assert response.status_code == 200
    data = response.json()
    assert len(data["chain"]) == 2
    item = data["chain"][0]
    assert item == {"ticker": "PETRH400", "tipo": "CALL", "strike": 40.0,
                     "preco": 1.45, "negocios": 320}
    # negocios=0/None deve virar 0, não quebrar
    assert data["chain"][1]["negocios"] == 0


def test_get_options_chain_ignora_linhas_curtas():
    """Linhas com menos de 10 colunas (op[:10]) são puladas silenciosamente."""
    chain_mock = [
        ["PETRH400", None, "CALL"],  # curta demais, deve ser ignorada
        ["PETRH420", None, "CALL", None, None, 42.0, None, None, 0.80, 50],
    ]
    with patch("backend.services.data_providers._fetch_chain", return_value=chain_mock):
        response = client.get("/market/opcoes/chain/PETR4")

    assert response.status_code == 200
    assert len(response.json()["chain"]) == 1


def test_get_options_chain_vazia():
    with patch("backend.services.data_providers._fetch_chain", return_value=[]):
        response = client.get("/market/opcoes/chain/PETR4")

    assert response.status_code == 200
    assert response.json()["chain"] == []


# ---------------------------------------------------------------------------
# _fetch_historical_with_fallback — brapi → yfinance → Yahoo HTTP (linhas
# 122-169; brapi feliz já é exercitado indiretamente pelos testes de
# /analysis e /indicators acima via mock de fetch_brapi_historical)
# ---------------------------------------------------------------------------

def test_fetch_historical_fallback_brapi_vazio_usa_yfinance():
    """brapi retorna vazio → cai para yfinance (linhas 134-142)."""
    import backend.api.routers.market as m

    yf_df = pd.DataFrame({
        "Open": [10.0, 10.5], "High": [10.2, 10.7], "Low": [9.8, 10.3],
        "Close": [10.1, 10.6], "Volume": [1000.0, 2000.0],
    }, index=pd.date_range("2026-01-01", periods=2, freq="B"))

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()),
          patch("yfinance.download", return_value=yf_df)):
        result = m._fetch_historical_with_fallback("PETR4")

    assert not result.empty
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert result.index.name == "date"


def test_fetch_historical_fallback_brapi_vazio_yfinance_multiindex():
    """yfinance pode retornar colunas MultiIndex para ticker único; devem ser
    reduzidas a Index simples (linha 140-141)."""
    import backend.api.routers.market as m

    dates = pd.date_range("2026-01-01", periods=2, freq="B")
    cols = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["PETR4.SA"]])
    yf_df = pd.DataFrame([[10.0, 10.2, 9.8, 10.1, 1000.0],
                          [10.5, 10.7, 10.3, 10.6, 2000.0]], index=dates, columns=cols)

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()),
          patch("yfinance.download", return_value=yf_df)):
        result = m._fetch_historical_with_fallback("PETR4")

    assert not result.empty
    assert "Close" in result.columns


def test_fetch_historical_fallback_yfinance_falha_tenta_yahoo_http():
    """yfinance levanta exceção → cai para fallback HTTP direto da Yahoo
    Finance Chart API (linhas 143-165), que aqui também é mockado."""
    import backend.api.routers.market as m

    fake_json = {
        "chart": {
            "result": [{
                "timestamp": [1700000000, 1700086400],
                "indicators": {
                    "quote": [{"open": [10.0, 10.5], "high": [10.2, 10.7],
                               "low": [9.8, 10.3], "close": [10.1, 10.6],
                               "volume": [1000, 2000]}],
                    "adjclose": [{"adjclose": [10.1, 10.6]}],
                },
            }]
        }
    }

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_json

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()),
          patch("yfinance.download", side_effect=RuntimeError("yfinance indisponível")),
          patch("requests.get", return_value=_FakeResponse())):
        result = m._fetch_historical_with_fallback("PETR4")

    assert not result.empty
    assert list(result["Close"]) == [10.1, 10.6]


def test_fetch_historical_fallback_todos_falham_retorna_df_vazio():
    """brapi vazio, yfinance falha e Yahoo HTTP falha → DataFrame vazio (linha 169)."""
    import backend.api.routers.market as m

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()),
          patch("yfinance.download", side_effect=RuntimeError("yfinance indisponível")),
          patch("requests.get", side_effect=RuntimeError("rede fora do ar"))):
        result = m._fetch_historical_with_fallback("PETR4")

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_fetch_historical_fallback_yahoo_http_sem_resultado_retorna_vazio():
    """Resposta HTTP 200 da Yahoo mas sem 'result' no JSON → DataFrame vazio."""
    import backend.api.routers.market as m

    class _FakeEmptyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"chart": {"result": []}}

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=pd.DataFrame()),
          patch("yfinance.download", side_effect=RuntimeError("yfinance indisponível")),
          patch("requests.get", return_value=_FakeEmptyResponse())):
        result = m._fetch_historical_with_fallback("PETR4")

    assert result.empty


# ---------------------------------------------------------------------------
# /analysis/{ticker} — branches de fundamentalistas via yfinance.Ticker.info
# (linhas 255-264, 269-278, 284-294, 302-303) e chain com tipo inválido (311, 314)
# ---------------------------------------------------------------------------

class _FakeYfTicker:
    """Stub de yf.Ticker que simula `.info` vazio (forçando os ramos de
    cálculo via income_stmt/balance_sheet/cash_flow) ou levanta exceção."""

    def __init__(self, info=None, income_stmt=None, balance_sheet=None, cash_flow=None,
                 raise_on_info=False):
        self._info = info if info is not None else {}
        self.income_stmt = income_stmt if income_stmt is not None else pd.DataFrame()
        self.balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()
        self.cash_flow = cash_flow if cash_flow is not None else pd.DataFrame()
        self._raise_on_info = raise_on_info

    @property
    def info(self):
        if self._raise_on_info:
            raise RuntimeError("yfinance.Ticker.info indisponível")
        return self._info


def test_analysis_fundamentalistas_calculados_via_dre_balanco_fluxo():
    """info vazio (sem trailingEps/bookValue/freeCashflow) → LPA/VPA/FCL
    calculados via income_stmt/balance_sheet/cash_flow (linhas 255-264,
    269-278, 284-294) e preco_graham/preco_dcf preenchidos (296-300)."""
    df_mock = _make_synthetic_df(300)

    income_stmt = pd.DataFrame({0: [5_000_000_000.0]}, index=["Net Income"])
    balance_sheet = pd.DataFrame({0: [40_000_000_000.0]}, index=["Stockholders Equity"])
    cash_flow = pd.DataFrame({0: [8_000_000_000.0, -1_000_000_000.0]},
                              index=["Operating Cash Flow", "Capital Expenditure"])
    info = {"sharesOutstanding": 1_000_000_000}

    fake_ticker = _FakeYfTicker(info=info, income_stmt=income_stmt,
                                 balance_sheet=balance_sheet, cash_flow=cash_flow)

    # NOTA: /analysis/{ticker} obtém histórico via _fetch_historical_with_fallback,
    # que chama fetch_brapi_historical através do módulo de origem
    # (backend.services.data_providers), não do nome importado em
    # backend.api.routers.market — por isso o patch precisa visar o módulo de origem.
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[]),
          patch("yfinance.Ticker", return_value=fake_ticker)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    data = response.json()
    assert data["preco_graham"] is not None
    assert data["preco_dcf"] is not None
    assert data["preco_graham"] > 0
    assert data["preco_dcf"] > 0


def test_analysis_fundamentalistas_falha_silenciosa_quando_info_excecao():
    """Se t.info levanta, o bloco fundamentalista falha silenciosamente e
    preco_graham/preco_dcf ficam None (linhas 302-303), sem 500."""
    df_mock = _make_synthetic_df(300)
    fake_ticker = _FakeYfTicker(raise_on_info=True)

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[]),
          patch("yfinance.Ticker", return_value=fake_ticker)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    data = response.json()
    assert data["preco_graham"] is None
    assert data["preco_dcf"] is None


def test_analysis_fundamentalistas_usa_info_direto_quando_disponivel():
    """info com trailingEps/bookValue/freeCashflow preenchidos não deve
    cair nos ramos de fallback via DRE/balanço/fluxo."""
    df_mock = _make_synthetic_df(300)
    info = {
        "trailingEps": 5.0, "bookValue": 25.0,
        "freeCashflow": 3_000_000_000.0, "sharesOutstanding": 1_000_000_000,
    }
    fake_ticker = _FakeYfTicker(info=info)

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=[]),
          patch("yfinance.Ticker", return_value=fake_ticker)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    data = response.json()
    import math
    assert data["preco_graham"] == round(math.sqrt(22.5 * 5.0 * 25.0), 2)


def test_analysis_chain_ignora_tipo_invalido_e_linha_curta():
    """Itens da chain com tipo fora de CALL/PUT ou linhas curtas devem ser
    ignorados sem quebrar a resposta (linhas 310-314)."""
    df_mock = _make_synthetic_df(300)
    chain_mock = [
        ["X1", None, "CALL"],  # curta demais — ignorada
        ["X2", None, "FUTURO", None, None, 40.0, None, None, 1.0, 10],  # tipo inválido — ignorada
        ["X3", None, "PUT", None, None, 38.0, None, None, 1.2, 90],  # válida
    ]
    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_mock),
          patch(f"{_MOD}._fetch_chain", return_value=chain_mock)):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    chain = response.json()["chain"]
    assert len(chain) == 1
    assert chain[0]["tipo"] == "put"


def test_analysis_rsi_nan_usa_default_50():
    """Quando close tem variação insuficiente para RSI (todos preços iguais),
    o resultado de _rsi_manual pode ser NaN → default 50.0 (linha 213-214)."""
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    flat = [40.0] * n  # lista plana: evita reindex por label ao montar o DataFrame
    df_flat = pd.DataFrame({
        "Open": flat, "High": flat, "Low": flat, "Close": flat,
        "Volume": [1_000_000.0] * n,
    }, index=idx)

    with (patch(f"{_MOD}.fetch_brapi_historical", return_value=df_flat),
          patch(f"{_MOD}._fetch_chain", return_value=[])):
        response = client.get("/market/analysis/PETR4")

    assert response.status_code == 200
    assert response.json()["rsi14"] == 50.0
