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
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_b3_official_tickers()
    assert out == {"PETR3": "PETROBRAS", "PETR4": "PETROBRAS", "PETR11": "PETROBRAS"}


def test_fetch_b3_official_paginates(monkeypatch):
    r1 = _fake_b3_response([{"issuingCompany": "PETR", "tradingName": "PETROBRAS"}], 2)
    r2 = _fake_b3_response([{"issuingCompany": "VALE", "tradingName": "VALE"}], 2)
    seq = iter([r1, r2])
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: next(seq))
    monkeypatch.setattr(dp.time, "sleep", lambda s: None)
    out = dp.fetch_b3_official_tickers()
    assert "PETR3" in out and "VALE3" in out


def test_fetch_b3_official_graceful_on_error(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(dp, "get_with_retry", boom)
    assert dp.fetch_b3_official_tickers() == {}


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


def _op(ticker_opcao, tipo, strike, preco, negocios=50):
    # Layout da chain bruta: [ticker, _, tipo, _, _, strike, _, _, preco, negocios]
    return [ticker_opcao, None, tipo, None, None, strike, None, None, preco, negocios]


def test_obter_opcoes_vizinhas_filtra_tipo_vencimento_e_exclui_strike(monkeypatch):
    chain = [
        _op("PETRC405", "CALL", 40.5, 1.20),   # mesmo venc, vizinho
        _op("PETRC410", "CALL", 41.0, 1.00),   # strike excluído
        _op("PETRC395", "CALL", 39.5, 1.50),   # mesmo venc, vizinho
        _op("PETRP405", "PUT",  40.5, 0.80),   # tipo errado
        _op("PETRC505", "CALL", 50.5, 0.10),   # outro vencimento
    ]
    venc_por_ticker = {
        "PETRC405": (6, 2026), "PETRC410": (6, 2026), "PETRC395": (6, 2026),
        "PETRP405": (6, 2026), "PETRC505": (7, 2026),
    }
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    monkeypatch.setattr(dp, "decodificar_opcao_b3",
                        lambda t: dict(zip(("mes_venc", "ano_venc"), venc_por_ticker.get(t, (0, 0)))))
    vizinhos = dp.obter_opcoes_vizinhas("PETR4", "CALL", strike_alvo=41.0,
                                        mes_v=6, ano_v=2026, excluir_strike=41.0)
    strikes = sorted(v["strike_real"] for v in vizinhos)
    assert strikes == [39.5, 40.5]


def test_obter_opcoes_vizinhas_respeita_limite_n(monkeypatch):
    chain = [_op(f"PETRC{400+i}", "CALL", 40.0 + i, 1.0) for i in range(10)]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    monkeypatch.setattr(dp, "decodificar_opcao_b3", lambda t: {"mes_venc": 6, "ano_venc": 2026})
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
    monkeypatch.setattr(dp, "decodificar_opcao_b3", lambda t: {"mes_venc": 6, "ano_venc": 2026})
    atm = dp.obter_opcao_atm("PETR4", preco_spot=41.2, mes_v=6, ano_v=2026, tipo_alvo="CALL")
    assert atm["strike_real"] == 41.0


def test_obter_opcao_atm_retorna_none_sem_chain(monkeypatch):
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: [])
    assert dp.obter_opcao_atm("PETR4", preco_spot=41.2, mes_v=6, ano_v=2026) is None


# ---------------------------------------------------------------------------
# fetch_brapi_historical
# ---------------------------------------------------------------------------

def test_fetch_brapi_historical_usa_cache_quando_disponivel(monkeypatch):
    cached = [{"Open": 1, "High": 2, "Low": 0.5, "Close": 1.5, "Volume": 100}]
    monkeypatch.setattr(dp, "cache_get", lambda k: cached)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert not out.empty
    assert out.iloc[0]["Close"] == 1.5


def test_fetch_brapi_historical_cache_vazio_retorna_df_vazio(monkeypatch):
    """cached é uma lista vazia (`[]`) -> `if cached:` é falsy mas `is not None` é True."""
    monkeypatch.setattr(dp, "cache_get", lambda k: [])
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert out.empty


def test_fetch_brapi_historical_cache_corrompido_segue_para_rede(monkeypatch):
    """pd.DataFrame(cached) lança exceção -> cai no `except: pass` e segue pro fetch real."""
    monkeypatch.setattr(dp, "cache_get", lambda k: object())  # não constrói DataFrame
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"results": []}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert out.empty


def test_fetch_brapi_historical_usa_token_quando_definido(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setenv("BRAPI_TOKEN", "minha-chave")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"results": []}
        return resp

    monkeypatch.setattr(dp, "get_with_retry", fake_get)
    dp.fetch_brapi_historical("PETR4.SA")
    assert captured["params"]["token"] == "minha-chave"


def test_fetch_brapi_historical_sem_resultados_retorna_df_vazio(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"results": []}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert out.empty


def test_fetch_brapi_historical_sem_historical_data_price_retorna_df_vazio(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"results": [{"symbol": "PETR4"}]}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert out.empty


def test_fetch_brapi_historical_sucesso_monta_df_ohlcv(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    sets = {}
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: sets.setdefault("v", v))
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "results": [{
            "historicalDataPrice": [
                {"date": 1716163200, "open": 10.0, "high": 11.0, "low": 9.5,
                 "close": 10.5, "volume": 1000},
                {"date": 1716249600, "open": 10.5, "high": 11.5, "low": 10.0,
                 "close": 11.0, "volume": 1200},
            ]
        }]
    }
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 2
    assert sets["v"]  # cache_set foi chamado com registros não vazios


def test_fetch_brapi_historical_erro_de_rede_retorna_df_vazio(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)

    def boom(*a, **k):
        raise RuntimeError("timeout")

    monkeypatch.setattr(dp, "get_with_retry", boom)
    out = dp.fetch_brapi_historical("PETR4.SA")
    assert out.empty


# ---------------------------------------------------------------------------
# fetch_all_b3_tickers
# ---------------------------------------------------------------------------

def test_fetch_all_b3_tickers_usa_cache(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: ["PETR4", "VALE3"])
    assert dp.fetch_all_b3_tickers() == ["PETR4", "VALE3"]


def test_fetch_all_b3_tickers_filtra_e_armazena_cache(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    sets = {}
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: sets.setdefault("v", v))
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"stocks": ["PETR4", "VALE3", "AB", "PETR11", "XYZW9A"]}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp.fetch_all_b3_tickers()
    assert "PETR4" in out and "VALE3" in out and "PETR11" in out
    assert "AB" not in out  # menor que 5 chars
    assert sets["v"] == out


def test_fetch_all_b3_tickers_token_no_params(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setenv("BRAPI_TOKEN", "tok123")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"stocks": []}
        return resp

    monkeypatch.setattr(dp, "get_with_retry", fake_get)
    dp.fetch_all_b3_tickers()
    assert captured["params"]["token"] == "tok123"


def test_fetch_all_b3_tickers_erro_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(dp, "get_with_retry", boom)
    assert dp.fetch_all_b3_tickers() == []


# ---------------------------------------------------------------------------
# fetch_b3_official_tickers — cache hit
# ---------------------------------------------------------------------------

def test_fetch_b3_official_tickers_usa_cache(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: {"PETR4": "PETROBRAS"})
    assert dp.fetch_b3_official_tickers() == {"PETR4": "PETROBRAS"}


# ---------------------------------------------------------------------------
# _volume_financeiro / filtrar_por_volume — branches adicionais
# ---------------------------------------------------------------------------

def test_filtrar_por_volume_lote_com_excecao_continua(monkeypatch):
    """yf.download lança erro num lote -> loga e segue para o próximo (linhas 177-179)."""
    calls = {"n": 0}
    segundo_lote_df = _multi_df({
        "CCCC3.SA": ([10, 10, 10], [1_000_000, 1_000_000, 1_000_000]),
        "DDDD4.SA": ([10, 10, 10], [1_000_000, 1_000_000, 1_000_000]),
    })

    def fake_download(lote, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("yfinance offline")
        return segundo_lote_df

    monkeypatch.setattr(dp.yf, "download", fake_download)
    monkeypatch.setattr(dp.time, "sleep", lambda s: None)
    out = dp.filtrar_por_volume(["AAAA3.SA", "BBBB4.SA", "CCCC3.SA", "DDDD4.SA"],
                                min_volume_rs=1_000_000, batch_size=2)
    assert "CCCC3.SA" in out and "DDDD4.SA" in out
    assert "AAAA3.SA" not in out and "BBBB4.SA" not in out


def test_filtrar_por_volume_dorme_entre_lotes(monkeypatch):
    df = _multi_df({"AAAA3.SA": ([10, 10, 10], [1_000_000, 1_000_000, 1_000_000])})
    monkeypatch.setattr(dp.yf, "download", lambda *a, **k: df)
    slept = []
    monkeypatch.setattr(dp.time, "sleep", lambda s: slept.append(s))
    dp.filtrar_por_volume(["AAAA3.SA"] * 2, min_volume_rs=1_000_000, batch_size=1, delay_s=0.5)
    assert slept == [0.5]


def test_volume_financeiro_single_index(monkeypatch):
    idx = pd.date_range("2026-05-20", periods=3)
    df = pd.DataFrame({"Close": [10, 10, 10], "Volume": [100, 100, 100]}, index=idx)
    vol = dp._volume_financeiro(df, "AAAA3.SA", single=True)
    assert vol == 1000.0


def test_volume_financeiro_ticker_ausente_multiindex_retorna_none():
    df = _multi_df({"AAAA3.SA": ([10, 10, 10], [100, 100, 100])})
    assert dp._volume_financeiro(df, "ZZZZ9.SA", single=False) is None


def test_volume_financeiro_close_ou_volume_vazio_retorna_none():
    idx = pd.date_range("2026-05-20", periods=3)
    df = pd.DataFrame({"Close": [None, None, None], "Volume": [100, 100, 100]}, index=idx)
    assert dp._volume_financeiro(df, "AAAA3.SA", single=True) is None


def test_volume_financeiro_excecao_retorna_none():
    """Estrutura inesperada (sem coluna Close) -> except Exception: return None."""
    df = pd.DataFrame({"Foo": [1, 2, 3]})
    assert dp._volume_financeiro(df, "AAAA3.SA", single=True) is None


def test_volume_financeiro_fin_vazio_apos_alinhamento_retorna_none():
    """close e volume não-vazios mas com índices disjuntos -> produto alinhado vazio (linha 148)."""
    close = pd.Series([10.0, 11.0], index=pd.date_range("2026-01-01", periods=2))
    volume = pd.Series([100.0, 200.0], index=pd.date_range("2030-01-01", periods=2))
    df = pd.DataFrame({"Close": close, "Volume": volume})
    assert dp._volume_financeiro(df, "AAAA3.SA", single=True) is None


# ---------------------------------------------------------------------------
# _fetch_chain
# ---------------------------------------------------------------------------

def test_fetch_chain_usa_cache(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: [["x"]])
    assert dp._fetch_chain("PETR4") == [["x"]]


def test_fetch_chain_success_diferente_de_data_retorna_vazio(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    sets = {}
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: sets.setdefault("v", v))
    resp = MagicMock()
    resp.json.return_value = {"success": "error"}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp._fetch_chain("PETR4")
    assert out == []
    assert sets["v"] == []


def test_fetch_chain_sucesso_retorna_chain(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    resp = MagicMock()
    resp.json.return_value = {"success": "data", "data": {"cotacoesOpcoes": [["a"]]}}
    monkeypatch.setattr(dp, "get_with_retry", lambda *a, **k: resp)
    out = dp._fetch_chain("PETR4")
    assert out == [["a"]]


def test_fetch_chain_erro_de_rede_retorna_vazio(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    sets = {}
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: sets.setdefault("v", v))

    def boom(*a, **k):
        raise RuntimeError("timeout")

    monkeypatch.setattr(dp, "get_with_retry", boom)
    out = dp._fetch_chain("PETR4")
    assert out == []
    assert sets["v"] == []


# ---------------------------------------------------------------------------
# get_real_options_from_opcoes_net
# ---------------------------------------------------------------------------

def test_get_real_options_usa_cache(monkeypatch):
    cached = {"ticker_opcao": "PETRC405", "strike_real": 40.5, "preco_tela": 1.2, "num_negocios": 50}
    monkeypatch.setattr(dp, "cache_get", lambda k: cached)
    out = dp.get_real_options_from_opcoes_net("PETR4", "CALL", 40.5)
    assert out == cached


def test_get_real_options_cache_vazio_retorna_none(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: {})
    assert dp.get_real_options_from_opcoes_net("PETR4", "CALL", 40.5) is None


def test_get_real_options_acha_strike_mais_proximo(monkeypatch):
    chain = [
        _op("PETRC400", "CALL", 40.0, 1.50, negocios=20),
        _op("PETRC405", "CALL", 40.5, 1.20, negocios=15),
        _op("PETRP405", "PUT", 40.5, 0.80, negocios=15),  # tipo errado
        _op("PETRC999", "CALL", 99.0, None, negocios=15),  # preco None
        _op("PETRC998", "CALL", 98.0, 0.0, negocios=15),  # preco <= 0.01
        _op("PETRC997", "CALL", 97.0, 1.0, negocios=None),  # negocios None
        _op("PETRC996", "CALL", 96.0, 1.0, negocios=1),  # abaixo de min_neg
    ]
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    out = dp.get_real_options_from_opcoes_net("PETR4", "CALL", strike_alvo=40.4)
    assert out["ticker_opcao"] == "PETRC405"


def test_get_real_options_curto_demais_ignorado(monkeypatch):
    chain = [["PETRC405", None, "CALL"]]  # menos de 10 campos
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    assert dp.get_real_options_from_opcoes_net("PETR4", "CALL", 40.0) is None


def test_get_real_options_sem_match_retorna_none(monkeypatch):
    monkeypatch.setattr(dp, "cache_get", lambda k: None)
    monkeypatch.setattr(dp, "cache_set", lambda k, v, ttl=0: None)
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: [])
    assert dp.get_real_options_from_opcoes_net("PETR4", "CALL", 40.0) is None


# ---------------------------------------------------------------------------
# obter_opcoes_vizinhas / obter_opcao_atm — filtros adicionais
# ---------------------------------------------------------------------------

def test_obter_opcoes_vizinhas_curto_demais_ignorado(monkeypatch):
    chain = [["PETRC405", None, "CALL"]]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    out = dp.obter_opcoes_vizinhas("PETR4", "CALL", 40.0, mes_v=6, ano_v=2026, excluir_strike=999)
    assert out == []


def test_obter_opcoes_vizinhas_filtra_preco_e_negocios_invalidos(monkeypatch):
    chain = [
        _op("PETRC400", "CALL", 40.0, None, negocios=10),
        _op("PETRC401", "CALL", 40.1, 0.0, negocios=10),
        _op("PETRC402", "CALL", 40.2, 1.0, negocios=None),
        _op("PETRC403", "CALL", 40.3, 1.0, negocios=1),  # abaixo de min_neg
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    monkeypatch.setattr(dp, "decodificar_opcao_b3", lambda t: {"mes_venc": 6, "ano_venc": 2026})
    out = dp.obter_opcoes_vizinhas("PETR4", "CALL", 40.0, mes_v=6, ano_v=2026, excluir_strike=999)
    assert out == []


def test_obter_opcao_atm_curto_demais_ignorado(monkeypatch):
    chain = [["PETRC405", None, "CALL"]]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    assert dp.obter_opcao_atm("PETR4", preco_spot=40.0, mes_v=6, ano_v=2026) is None


def test_obter_opcao_atm_filtra_tipo_preco_negocios(monkeypatch):
    chain = [
        _op("PETRP405", "PUT", 40.5, 1.0, negocios=10),  # tipo errado p/ CALL
        _op("PETRC406", "CALL", 40.6, None, negocios=10),  # preco None
        _op("PETRC407", "CALL", 40.7, 0.0, negocios=10),  # preco baixo
        _op("PETRC408", "CALL", 40.8, 1.0, negocios=None),  # negocios None
        _op("PETRC409", "CALL", 40.9, 1.0, negocios=1),  # abaixo de min_neg
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    monkeypatch.setattr(dp, "decodificar_opcao_b3", lambda t: {"mes_venc": 6, "ano_venc": 2026})
    assert dp.obter_opcao_atm("PETR4", preco_spot=40.0, mes_v=6, ano_v=2026, tipo_alvo="CALL") is None


def test_obter_opcao_atm_decoded_vencimento_errado_ignorado(monkeypatch):
    chain = [_op("PETRC405", "CALL", 40.5, 1.0, negocios=10)]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    monkeypatch.setattr(dp, "decodificar_opcao_b3", lambda t: {"mes_venc": 7, "ano_venc": 2026})
    assert dp.obter_opcao_atm("PETR4", preco_spot=40.0, mes_v=6, ano_v=2026) is None


# ---------------------------------------------------------------------------
# get_liquid_options_for_ticker
# ---------------------------------------------------------------------------

def test_get_liquid_options_for_ticker_ordena_por_negocios_e_limita(monkeypatch):
    chain = [
        _op("PETRC400", "CALL", 40.0, 1.0, negocios=5),
        _op("PETRP400", "PUT", 40.0, 1.0, negocios=50),
        _op("PETRC410", "CALL", 41.0, 1.0, negocios=20),
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    out = dp.get_liquid_options_for_ticker("PETR4", limit=2)
    assert [o["ticker_opcao"] for o in out] == ["PETRP400", "PETRC410"]
    assert out[0]["tipo"] == "PUT"
    assert out[0]["ticker_subjacente"] == "PETR4"


def test_get_liquid_options_for_ticker_filtra_invalidos(monkeypatch):
    chain = [
        ["PETRC400", None, "CALL"],  # curto demais
        _op("PETRX400", "WARRANT", 40.0, 1.0, negocios=10),  # tipo inválido
        _op("PETRC401", "CALL", 40.1, 1.0, negocios=0),  # negocios <= 0
        _op("PETRC402", "CALL", 40.2, None, negocios=10),  # preco None
        _op("PETRC403", "CALL", 40.3, 0.0, negocios=10),  # preco baixo
        _op("PETRC404", "CALL", 40.4, 1.0, negocios=10),  # válido
    ]
    monkeypatch.setattr(dp, "_fetch_chain", lambda t: chain)
    out = dp.get_liquid_options_for_ticker("PETR4")
    assert len(out) == 1
    assert out[0]["ticker_opcao"] == "PETRC404"
