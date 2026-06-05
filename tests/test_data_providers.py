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
