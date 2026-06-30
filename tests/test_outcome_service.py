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


# ── _persistir_trigger_outcomes: desfecho não terminal e falha de upsert ────

def test_persistir_trigger_outcomes_desfecho_nao_terminal_nao_persiste(monkeypatch):
    """Desfecho 'aberto'/'indeterminado' (não terminal) sai cedo (linha 36-37),
    sem chamar o supabase."""
    fake = _FakeSupabase([])
    sinal = _row(gatilhos_ids=["G2"])
    osvc._persistir_trigger_outcomes(fake, sinal, {"desfecho": "aberto", "dias_ate": None})
    assert fake.store.get("trigger_outcomes", []) == []


def test_persistir_trigger_outcomes_falha_upsert_loga_e_nao_propaga(monkeypatch, caplog):
    """Se supabase.table(...).upsert(...).execute() lançar, o erro é capturado e
    logado (linhas 56-57), sem quebrar avaliar_sinais."""
    class _BoomQuery(_FakeQuery):
        def execute(self):
            raise RuntimeError("conexão perdida")

    class _BoomSupabase(_FakeSupabase):
        def table(self, nome):
            if nome == "trigger_outcomes":
                return _BoomQuery(self.store, nome)
            return super().table(nome)

    fake = _BoomSupabase([_row(gatilhos_ids=["G2", "G3"], setup="REVERSAO")])
    monkeypatch.setattr(osvc, "get_supabase", lambda: fake)
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])

    with caplog.at_level("WARNING", logger="b3_api"):
        rep = osvc.avaliar_sinais(dias=30)

    assert rep["sinais_avaliados"] == 1  # avaliação do sinal segue mesmo com falha de persistência
    assert any("Erro ao persistir trigger_outcomes" in m for m in caplog.messages)


# ── _precos_desde: caminho real (sem mock), via _baixar_ohlcv ──────────────

def test_precos_desde_retorna_closes_a_partir_da_data(monkeypatch):
    from datetime import datetime, timezone

    import pandas as pd

    idx = pd.date_range("2026-05-01", periods=10, freq="D")
    df = pd.DataFrame({"Close": [float(i) for i in range(10)]}, index=idx)
    monkeypatch.setattr(osvc, "_baixar_ohlcv", lambda *a, **k: df)

    desde = datetime(2026, 5, 5, tzinfo=timezone.utc)
    precos = osvc._precos_desde("PETR4.SA", desde)

    assert precos == [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


def test_precos_desde_df_none_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(osvc, "_baixar_ohlcv", lambda *a, **k: None)
    assert osvc._precos_desde("PETR4.SA", __import__("datetime").datetime.now()) == []


def test_precos_desde_df_vazio_retorna_lista_vazia(monkeypatch):
    import pandas as pd
    monkeypatch.setattr(osvc, "_baixar_ohlcv", lambda *a, **k: pd.DataFrame())
    assert osvc._precos_desde("PETR4.SA", __import__("datetime").datetime.now()) == []


def test_precos_desde_sem_coluna_close_retorna_lista_vazia(monkeypatch):
    import pandas as pd
    df = pd.DataFrame({"Open": [1.0, 2.0]})
    monkeypatch.setattr(osvc, "_baixar_ohlcv", lambda *a, **k: df)
    assert osvc._precos_desde("PETR4.SA", __import__("datetime").datetime.now()) == []


def test_precos_desde_normaliza_colunas_multiindex(monkeypatch):
    """Colunas tipo (campo, ticker) — formato do yfinance multi-ticker — são
    normalizadas para o nome simples antes de procurar 'Close'."""
    from datetime import datetime, timezone

    import pandas as pd

    idx = pd.date_range("2026-05-01", periods=3, freq="D")
    df = pd.DataFrame({("Close", "PETR4.SA"): [10.0, 11.0, 12.0]}, index=idx)
    monkeypatch.setattr(osvc, "_baixar_ohlcv", lambda *a, **k: df)

    desde = datetime(2026, 5, 1, tzinfo=timezone.utc)
    precos = osvc._precos_desde("PETR4.SA", desde)

    assert precos == [10.0, 11.0, 12.0]


# ── avaliar_sinais: erro na query, linhas malformadas, timestamp inválido ───

def test_avaliar_sinais_erro_na_query_retorna_erro(monkeypatch):
    class _BoomQuery(_FakeQuery):
        def execute(self):
            raise RuntimeError("timeout na query")

    class _BoomSupabase(_FakeSupabase):
        def table(self, nome):
            return _BoomQuery(self.store, nome)

    monkeypatch.setattr(osvc, "get_supabase", lambda: _BoomSupabase([]))
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["resolvidos"] == 0
    assert rep["erro"] == "timeout na query"


def test_avaliar_sinais_pula_linha_sem_strike_ref_ou_dte(monkeypatch):
    rows = [_row(strike_ref=None), _row(id=2, dte=None)]
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase(rows))
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 0


def test_avaliar_sinais_pula_linha_com_timestamp_invalido(monkeypatch):
    rows = [_row(timestamp="isso-nao-e-uma-data")]
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase(rows))
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 0


def test_avaliar_sinais_pula_linha_sem_ticker(monkeypatch):
    rows = [_row(ticker="")]
    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase(rows))
    monkeypatch.setattr(osvc, "_precos_desde", lambda t, d: [100, 104, 108, 113, 118, 122])
    rep = osvc.avaliar_sinais(dias=30)
    assert rep["sinais_avaliados"] == 0


def test_avaliar_sinais_adiciona_sufixo_sa_quando_ausente(monkeypatch):
    """Ticker sem '.SA' recebe o sufixo antes de buscar preços (linha 103-104)."""
    capturado = {}

    def _fake_precos(ticker_sa, dt):
        capturado["ticker"] = ticker_sa
        return [100, 104, 108, 113, 118, 122]

    monkeypatch.setattr(osvc, "get_supabase", lambda: _FakeSupabase([_row(ticker="petr4")]))
    monkeypatch.setattr(osvc, "_precos_desde", _fake_precos)
    rep = osvc.avaliar_sinais(dias=30)
    assert capturado["ticker"] == "PETR4.SA"
    assert rep["sinais_avaliados"] == 1
