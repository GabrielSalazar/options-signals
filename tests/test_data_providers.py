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
