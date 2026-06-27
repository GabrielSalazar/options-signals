"""Teste de wiring do outcome_service (Supabase + preços mockados)."""
from backend.services import outcome_service as osvc


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": self._data})()


class _FakeSupabase:
    def __init__(self, data):
        self._data = data

    def table(self, *a, **k):
        return _FakeQuery(self._data)


def _row(**over):
    r = {
        "ticker": "TESTE3", "tipo_sinal": "CALL", "strike_ref": 110.0,
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
