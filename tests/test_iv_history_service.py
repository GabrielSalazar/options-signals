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
