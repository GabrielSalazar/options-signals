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


def test_get_all_b3_assets_vive_no_loader():
    assert hasattr(tl, "get_all_b3_assets")


def test_config_nao_exporta_mais_get_all_b3_assets():
    import backend.core.config as cfg
    assert not hasattr(cfg, "get_all_b3_assets")


def test_config_nao_importa_services():
    """config (core) não pode importar services (regra de camadas)."""
    import inspect
    import backend.core.config as cfg
    src = inspect.getsource(cfg)
    assert "backend.services" not in src


def test_nome_ativo_curado_tem_precedencia(monkeypatch):
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {"PETR4": "OUTRO"})
    assert tl.nome_ativo("PETR4.SA") == ATIVOS_B3["PETR4.SA"]
    assert tl.nome_ativo("petr4") == ATIVOS_B3["PETR4.SA"]


def test_nome_ativo_usa_nome_b3_para_nao_curado(monkeypatch):
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {"XPTO3": "XPTO Corp"})
    assert tl.nome_ativo("XPTO3.SA") == "XPTO Corp"


def test_nome_ativo_fallback_codigo(monkeypatch):
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {})
    assert tl.nome_ativo("ZZZZ3") == "ZZZZ3"
