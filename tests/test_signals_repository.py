"""Testes de caracterização do signals_repository.

Garante que cada método monta a query encadeada esperada (select/eq/gte/
order/range/limit/execute) e devolve o resultado de execute() sem alterá-lo,
seguindo o padrão de fake de tests/test_outcome_service.py e
tests/test_signals.py. O cliente supabase é passado diretamente (já obtido
pelo chamador), sem monkeypatch de get_supabase.
"""
from backend.services import signals_repository as repo


class _FakeQuery:
    """Fake de query-builder do Supabase: encadeia métodos, registra as
    chamadas e retorna dados fixos em execute()."""

    def __init__(self, data=None, count=None, calls=None):
        self._data = data if data is not None else []
        self._count = count
        self._calls = calls if calls is not None else []

    def select(self, *a, **k):
        self._calls.append(("select", a, k))
        return self

    def eq(self, *a, **k):
        self._calls.append(("eq", a, k))
        return self

    def gte(self, *a, **k):
        self._calls.append(("gte", a, k))
        return self

    def order(self, *a, **k):
        self._calls.append(("order", a, k))
        return self

    def range(self, *a, **k):
        self._calls.append(("range", a, k))
        return self

    def limit(self, *a, **k):
        self._calls.append(("limit", a, k))
        return self

    def execute(self):
        self._calls.append(("execute", (), {}))
        return type("R", (), {"data": self._data, "count": self._count})()


class _FakeSupabase:
    def __init__(self, data=None, count=None):
        self._data = data
        self._count = count
        self.calls = []

    def table(self, nome):
        self.calls.append(("table", nome))
        return _FakeQuery(self._data, self._count, self.calls)


# ---------------------------------------------------------------------------
# fetch_signals
# ---------------------------------------------------------------------------

def test_fetch_signals_sem_filtros():
    fake = _FakeSupabase(data=[{"ticker": "PETR4"}], count=1)

    res = repo.fetch_signals(fake, limit=50, offset=0, tipo=None, min_score=0)

    assert res.data == [{"ticker": "PETR4"}]
    assert res.count == 1
    nomes = [c[0] for c in fake.calls if c[0] != "table"]
    assert nomes == ["select", "order", "range", "execute"]
    assert ("range", (0, 49), {}) in fake.calls


def test_fetch_signals_com_tipo_e_min_score():
    fake = _FakeSupabase(data=[{"ticker": "VALE3", "tipo_sinal": "PUT", "score": 9}], count=1)

    res = repo.fetch_signals(fake, limit=10, offset=5, tipo="PUT", min_score=8)

    assert res.data[0]["ticker"] == "VALE3"
    assert ("eq", ("tipo_sinal", "PUT"), {}) in fake.calls
    assert ("gte", ("score", 8), {}) in fake.calls
    assert ("range", (5, 14), {}) in fake.calls


# ---------------------------------------------------------------------------
# fetch_history
# ---------------------------------------------------------------------------

def test_fetch_history_sem_filtros():
    fake = _FakeSupabase(data=[{"ticker": "PETR4"}])

    res = repo.fetch_history(fake, limit=50, offset=0, ticker=None, tipo_sinal=None)

    assert res.data == [{"ticker": "PETR4"}]
    nomes = [c[0] for c in fake.calls if c[0] != "table"]
    assert nomes == ["select", "order", "range", "execute"]


def test_fetch_history_com_ticker_e_tipo_sinal():
    fake = _FakeSupabase(data=[{"ticker": "VALE3", "tipo_sinal": "PUT"}])

    res = repo.fetch_history(fake, limit=20, offset=0, ticker="vale3", tipo_sinal="put")

    assert res.data[0]["ticker"] == "VALE3"
    # o repositório normaliza com .upper(), igual ao código original do router.
    assert ("eq", ("ticker", "VALE3"), {}) in fake.calls
    assert ("eq", ("tipo_sinal", "PUT"), {}) in fake.calls


# ---------------------------------------------------------------------------
# fetch_analytics
# ---------------------------------------------------------------------------

def test_fetch_analytics():
    fake = _FakeSupabase(data=[{"ticker": "PETR4", "tipo_sinal": "CALL", "score": 8}])

    res = repo.fetch_analytics(fake, "PETR4")

    assert res.data[0]["ticker"] == "PETR4"
    assert ("eq", ("ticker", "PETR4"), {}) in fake.calls
    assert ("limit", (100,), {}) in fake.calls
    nomes = [c[0] for c in fake.calls if c[0] != "table"]
    assert nomes == ["select", "eq", "order", "limit", "execute"]


# ---------------------------------------------------------------------------
# fetch_performance
# ---------------------------------------------------------------------------

def test_fetch_performance():
    rows = [{"ticker": "PETR4", "tipo_sinal": "CALL", "score": 8}]
    fake = _FakeSupabase(data=rows)

    cutoff = "2026-05-01T00:00:00+00:00"
    res = repo.fetch_performance(fake, cutoff)

    assert res.data == rows
    assert ("gte", ("timestamp", cutoff), {}) in fake.calls
    assert ("limit", (2000,), {}) in fake.calls
    nomes = [c[0] for c in fake.calls if c[0] != "table"]
    assert nomes == ["select", "gte", "order", "limit", "execute"]
