"""Teste de wiring do outcome_service (Supabase + preços mockados)."""
from backend.services import outcome_service as osvc


class _FakeQuery:
    def __init__(self, store, table_name, data=None):
        self._store = store
        self._table = table_name
        self._data = data

    def select(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, rows, on_conflict=None):
        self._store.setdefault(self._table, []).extend(rows)
        return self

    def execute(self):
        if self._table == "signals":
            return type("R", (), {"data": self._data})()
        return type("R", (), {"data": []})()


class _FakeSupabase:
    def __init__(self, data):
        self._data = data
        self.store = {}

    def table(self, nome):
        return _FakeQuery(self.store, nome, self._data)


def _row(**over):
    r = {
        "id": 1, "ticker": "TESTE3", "tipo_sinal": "CALL", "strike_ref": 110.0,
        "premio_est": 1.0, "preco_tela": None,
        "alvo1": 1.25, "alvo2": 3.50, "alvo_final": 8.0, "stop": 0.57,
        "hv_20d": 40.0, "iv_mercado": None, "dte": 20, "preco_acao": 100.0,
        "score": 9, "score_ponderado": 72, "ponderado_passou": True,
        "timestamp": "2026-05-20T13:00:00+00:00",
    }
    r.update(over)
    return r


def test_avaliar_sinais_sem_supabase_retorna_erro(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: None)
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["resolvidos"] == 0
    assert "erro" in rep


def test_avaliar_sinais_avalia_e_agrega(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase([_row()]))
    # ação subindo → CALL ganha
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 1
    assert rep["ganhos"] == 1
    assert rep["win_rate_classico"] == 100.0
    assert "distribuicao" in rep


def test_avaliar_sinais_pula_sem_precos(monkeypatch):
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase([_row()]))
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [])  # sem dados
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 0


def test_avaliar_sinais_persiste_trigger_outcomes_para_desfecho_terminal(monkeypatch):
    fake = _FakeSupabase([_row(gatilhos_ids=["G2", "G3"], setup="REVERSAO")])
    monkeypatch.setattr(osvc, "get_supabase", lambda: fake)
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])

    osvc.avaliar_sinais(dias=30)

    linhas = fake.store.get("trigger_outcomes", [])
    assert len(linhas) == 2
    assert {l["gatilho_id"] for l in linhas} == {"G2", "G3"}
    assert all(l["signal_id"] == 1 for l in linhas)
    assert all(l["resultado_final"] == "alvo_final" for l in linhas)
    assert all(l["retorno_pct"] == 700.0 for l in linhas)
    assert all(l["dias_ate_resolucao"] == 5 for l in linhas)
    assert {l["familia"] for l in linhas} == {"OSCILADOR", "ESTRUTURA"}


def test_avaliar_sinais_pula_trigger_outcomes_sem_gatilhos_ids(monkeypatch):
    fake = _FakeSupabase([_row()])  # sinal legado, sem gatilhos_ids
    monkeypatch.setattr(osvc, "get_supabase", lambda: fake)
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])

    osvc.avaliar_sinais(dias=30)

    assert fake.store.get("trigger_outcomes", []) == []
