"""Testes de run_scan — seleção de universo, lote único de Telegram (sem rede)."""
import asyncio

from backend.core.config import ATIVOS_B3
from backend.services import signal_service as ss


def _stub_common(monkeypatch):
    monkeypatch.setattr(ss, "persist_signals", lambda s: None)
    monkeypatch.setattr(ss, "update_last_scan", lambda s: None)
    monkeypatch.setattr(ss, "_maybe_broadcast", lambda s: None)


def test_run_scan_curado_itera_ativos_b3(monkeypatch):
    _stub_common(monkeypatch)
    seen = []
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: seen.append(t) or None)
    monkeypatch.setattr(ss, "notificar_lote", lambda s: None)
    ss.run_scan(universe="curado")
    assert set(seen) == set(ATIVOS_B3.keys())


def test_run_scan_liquido_usa_loader(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(ss, "carregar_tickers_b3", lambda: {"XPTO3.SA": "Xpto"})
    seen = []
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: seen.append(t) or None)
    monkeypatch.setattr(ss, "notificar_lote", lambda s: None)
    ss.run_scan()  # default = liquido
    assert seen == ["XPTO3.SA"]


def test_run_scan_telegram_em_lote_unico(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(ss, "carregar_tickers_b3", lambda: {"A3.SA": "A", "B3.SA": "B"})
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: {"ticker": t})
    lotes = []
    monkeypatch.setattr(ss, "notificar_lote", lambda s: lotes.append(list(s)))
    ss.run_scan()
    assert len(lotes) == 1          # um único envio em lote, não por-sinal
    assert len(lotes[0]) == 2


def test_scan_batch_usa_nome_enriquecido(monkeypatch):
    from backend.services import ticker_loader as tl
    monkeypatch.setattr(tl, "fetch_b3_official_tickers", lambda: {"XPTO3": "XPTO Corp"})
    captured = {}
    monkeypatch.setattr(ss, "analyse_ticker", lambda t_sa, nome: captured.update(nome=nome) or None)
    monkeypatch.setattr(ss, "persist_signals", lambda s: None)
    monkeypatch.setattr(ss, "update_last_scan", lambda s: None)
    monkeypatch.setattr(ss, "notificar_lote", lambda s: None)
    ss.scan_batch(["XPTO3"])  # não-curado → deve vir o nome da B3, não o código
    assert captured["nome"] == "XPTO Corp"


def test_persist_signals_propaga_campos_da_camada_2(monkeypatch):
    capturado = {}

    class _FakeTable:
        def insert(self, rows):
            capturado["rows"] = rows
            return self
        def execute(self):
            return type("R", (), {"data": capturado["rows"]})()

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())

    sinal = {
        "ticker": "TESTE3", "tipo_sinal": "CALL", "score": 9,
        "gatilhos_ids": ["G2", "G3"], "familias_ativas": 2,
        "score_familias_capped": 4, "consenso_decisao": "passaria",
        "setup": "REVERSAO", "setup_params_shadow": {"otm_mult": 0.7},
    }
    ss.persist_signals([sinal])

    row = capturado["rows"][0]
    assert row["gatilhos_ids"] == ["G2", "G3"]
    assert row["familias_ativas"] == 2
    assert row["score_familias_capped"] == 4
    assert row["consenso_decisao"] == "passaria"
    assert row["setup"] == "REVERSAO"
    assert row["setup_params_shadow"] == {"otm_mult": 0.7}


# ── Estado em memória ───────────────────────────────────────────────────────────

def test_update_last_scan_atualiza_lista_e_timestamp():
    ss.update_last_scan([{"ticker": "PETR4"}])
    assert ss.last_scan_signals() == [{"ticker": "PETR4"}]
    assert ss.last_scan_ts() is not None


def test_update_last_scan_lista_vazia_ainda_atualiza_ts():
    ss.update_last_scan([])
    assert ss.last_scan_signals() == []
    assert ss.last_scan_ts() is not None


# ── Fila de alertas (SSE) ───────────────────────────────────────────────────────

def test_register_e_unregister_alert_queue():
    q = ss.register_alert_queue()
    assert q in ss._alert_queues
    ss.unregister_alert_queue(q)
    assert q not in ss._alert_queues


def test_unregister_alert_queue_inexistente_nao_quebra():
    q = asyncio.Queue()
    ss.unregister_alert_queue(q)  # nunca registrada — não deve levantar


def test_broadcast_alert_envia_para_todas_as_filas():
    async def _run():
        q1 = ss.register_alert_queue()
        q2 = ss.register_alert_queue()
        try:
            await ss.broadcast_alert({"ticker": "VALE3"})
            assert q1.get_nowait() == {"ticker": "VALE3"}
            assert q2.get_nowait() == {"ticker": "VALE3"}
        finally:
            ss.unregister_alert_queue(q1)
            ss.unregister_alert_queue(q2)

    asyncio.run(_run())


def test_maybe_broadcast_sem_loop_rodando_nao_quebra():
    # Chamado fora de uma coroutine: get_running_loop() levanta RuntimeError,
    # tratado internamente — não deve propagar exceção.
    ss._maybe_broadcast({"ticker": "ITUB4"})


def test_maybe_broadcast_com_loop_rodando_agenda_task(monkeypatch):
    async def _run():
        q = ss.register_alert_queue()
        try:
            ss._maybe_broadcast({"ticker": "BBAS3"})
            await asyncio.sleep(0)  # cede controle para a task agendada
            assert q.get_nowait() == {"ticker": "BBAS3"}
        finally:
            ss.unregister_alert_queue(q)

    asyncio.run(_run())


# ── persist_signals: caminhos de erro ───────────────────────────────────────────

def test_persist_signals_lista_vazia_nao_chama_supabase(monkeypatch):
    chamado = []
    monkeypatch.setattr(ss, "get_supabase", lambda: chamado.append(1))
    ss.persist_signals([])
    assert chamado == []


def test_persist_signals_sem_supabase_loga_warning(monkeypatch, caplog):
    monkeypatch.setattr(ss, "get_supabase", lambda: None)
    with caplog.at_level("WARNING"):
        ss.persist_signals([{"ticker": "PETR4", "tipo_sinal": "CALL", "score": 7}])
    assert "Supabase indisponível" in caplog.text


def test_persist_signals_excecao_no_insert_e_logada(monkeypatch, caplog):
    class _FakeTable:
        def insert(self, rows):
            return self
        def execute(self):
            raise RuntimeError("boom")

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())
    with caplog.at_level("ERROR"):
        ss.persist_signals([{"ticker": "PETR4", "tipo_sinal": "CALL", "score": 7}])
    assert "Erro ao persistir sinais" in caplog.text


# ── cleanup_old_signals ─────────────────────────────────────────────────────────

def test_cleanup_old_signals_sem_supabase_retorna_silenciosamente(monkeypatch):
    monkeypatch.setattr(ss, "get_supabase", lambda: None)
    ss.cleanup_old_signals()  # não deve levantar


def test_cleanup_old_signals_chama_delete_lt(monkeypatch):
    capturado = {}

    class _FakeQuery:
        def lt(self, col, cutoff):
            capturado["col"] = col
            capturado["cutoff"] = cutoff
            return self
        def execute(self):
            return type("R", (), {})()

    class _FakeTable:
        def delete(self):
            return _FakeQuery()

    class _FakeSupabase:
        def table(self, nome):
            capturado["table"] = nome
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())
    ss.cleanup_old_signals(days=10)
    assert capturado["table"] == "signals"
    assert capturado["col"] == "timestamp"
    assert capturado["cutoff"]


def test_cleanup_old_signals_excecao_e_logada(monkeypatch, caplog):
    class _FakeTable:
        def delete(self):
            raise RuntimeError("falhou")

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())
    with caplog.at_level("ERROR"):
        ss.cleanup_old_signals()
    assert "Erro no cleanup" in caplog.text


# ── rebuild_historico_sinais ────────────────────────────────────────────────────

def test_rebuild_historico_sinais_sem_supabase_retorna(monkeypatch):
    monkeypatch.setattr(ss, "get_supabase", lambda: None)
    ss.rebuild_historico_sinais()  # não deve levantar


def test_rebuild_historico_sinais_popula_a_partir_do_supabase(monkeypatch):
    from backend.core import config as cfg
    cfg._historico_sinais.clear()

    rows = [
        {"ticker": "PETR4", "timestamp": "2026-06-01T10:00:00Z", "tipo_sinal": "CALL", "score_tecnico": 8, "score": 8},
        {"ticker": "PETR4", "timestamp": "2026-06-02T10:00:00Z", "tipo_sinal": "PUT", "score": 6},
        {"ticker": "", "timestamp": "2026-06-02T10:00:00Z"},  # ticker vazio: ignorado
        {"ticker": "VALE3", "timestamp": ""},                  # timestamp vazio: ignorado
        {"ticker": "BAD3", "timestamp": "not-a-date"},         # parse falha: ignorado silenciosamente
    ]

    class _FakeQuery:
        def select(self, *a, **k):
            return self
        def gte(self, *a, **k):
            return self
        def order(self, *a, **k):
            return self
        def execute(self):
            return type("R", (), {"data": rows})()

    class _FakeTable:
        def select(self, *a, **k):
            return _FakeQuery()

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())
    ss.rebuild_historico_sinais()

    assert "PETR4" in cfg._historico_sinais
    assert len(cfg._historico_sinais["PETR4"]) == 2
    assert cfg._historico_sinais["PETR4"][0]["tipo"] == "CALL"
    assert cfg._historico_sinais["PETR4"][0]["score"] == 8
    assert cfg._historico_sinais["PETR4"][1]["score"] == 6  # cai para "score" quando "score_tecnico" ausente
    assert "VALE3" not in cfg._historico_sinais
    assert "BAD3" not in cfg._historico_sinais
    cfg._historico_sinais.clear()


def test_rebuild_historico_sinais_excecao_geral_e_logada(monkeypatch, caplog):
    class _FakeTable:
        def select(self, *a, **k):
            raise RuntimeError("falhou geral")

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(ss, "get_supabase", lambda: _FakeSupabase())
    with caplog.at_level("WARNING"):
        ss.rebuild_historico_sinais()
    assert "Erro ao reconstituir historico_sinais" in caplog.text


# ── analyse_ticker / _normalize_ticker ──────────────────────────────────────────

def test_normalize_ticker_adiciona_sufixo_sa():
    assert ss._normalize_ticker("petr4") == "PETR4.SA"


def test_normalize_ticker_preserva_sufixo_existente():
    assert ss._normalize_ticker("petr4.sa") == "PETR4.SA"


def test_analyse_ticker_excecao_retorna_none_e_loga(monkeypatch, caplog):
    def _boom(ticker, nome, verbose=False):
        raise ValueError("falhou na análise")

    monkeypatch.setattr(ss, "analisar_ativo", _boom)
    with caplog.at_level("WARNING"):
        resultado = ss.analyse_ticker("PETR4.SA", "Petrobras")
    assert resultado is None
    assert "Erro ao analisar" in caplog.text


def test_analyse_ticker_sucesso_retorna_sinal(monkeypatch):
    monkeypatch.setattr(ss, "analisar_ativo", lambda t, n, verbose=False: {"ticker": t})
    resultado = ss.analyse_ticker("PETR4.SA", "Petrobras")
    assert resultado == {"ticker": "PETR4.SA"}


# ── scan_single ──────────────────────────────────────────────────────────────────

def test_scan_single_sem_sinal_retorna_none(monkeypatch):
    monkeypatch.setattr(ss, "nome_ativo", lambda t: "Nome")
    monkeypatch.setattr(ss, "analisar_ativo", lambda t, n, verbose=True: None)
    persistiu = []
    monkeypatch.setattr(ss, "persist_signals", lambda s: persistiu.append(s))
    enviou = []
    monkeypatch.setattr(ss, "enviar_telegram", lambda s: enviou.append(s))
    resultado = ss.scan_single("petr4")
    assert resultado is None
    assert persistiu == []
    assert enviou == []


def test_scan_single_com_sinal_persiste_notifica_e_broadcast(monkeypatch):
    monkeypatch.setattr(ss, "nome_ativo", lambda t: "Petrobras")
    sinal = {"ticker": "PETR4.SA", "score": 8}
    monkeypatch.setattr(ss, "analisar_ativo", lambda t, n, verbose=True: sinal)
    persistiu = []
    monkeypatch.setattr(ss, "persist_signals", lambda s: persistiu.append(s))
    enviou = []
    monkeypatch.setattr(ss, "enviar_telegram", lambda s: enviou.append(s))
    broadcasts = []
    monkeypatch.setattr(ss, "_maybe_broadcast", lambda s: broadcasts.append(s))

    resultado = ss.scan_single("petr4")

    assert resultado == sinal
    assert persistiu == [[sinal]]
    assert enviou == [sinal]
    assert broadcasts == [sinal]


# ── scan_batch ───────────────────────────────────────────────────────────────────

def test_scan_batch_sem_sinais_nao_persiste_nem_notifica(monkeypatch):
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n: None)
    persistiu = []
    monkeypatch.setattr(ss, "persist_signals", lambda s: persistiu.append(s))
    notificou = []
    monkeypatch.setattr(ss, "notificar_lote", lambda s: notificou.append(s))
    atualizou = []
    monkeypatch.setattr(ss, "update_last_scan", lambda s: atualizou.append(s))

    resultado = ss.scan_batch(["XPTO3"])

    assert resultado == []
    assert persistiu == []
    assert notificou == []
    assert atualizou == []


def test_scan_batch_com_sinais_persiste_e_atualiza_estado(monkeypatch):
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n: {"ticker": t})
    persistiu = []
    monkeypatch.setattr(ss, "persist_signals", lambda s: persistiu.append(list(s)))
    notificou = []
    monkeypatch.setattr(ss, "notificar_lote", lambda s: notificou.append(list(s)))
    atualizou = []
    monkeypatch.setattr(ss, "update_last_scan", lambda s: atualizou.append(list(s)))

    resultado = ss.scan_batch(["XPTO3", "ABCD4"])

    assert len(resultado) == 2
    assert len(persistiu) == 1 and len(persistiu[0]) == 2
    assert len(notificou) == 1 and len(notificou[0]) == 2
    assert len(atualizou) == 1 and len(atualizou[0]) == 2


# ── run_scan: persistência e notificação ao final ───────────────────────────────

def test_run_scan_persiste_e_notifica_com_sinais(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(ss, "carregar_tickers_b3", lambda: {"A3.SA": "A"})
    monkeypatch.setattr(ss, "analyse_ticker", lambda t, n, verbose=False: {"ticker": t})
    persistiu = []
    monkeypatch.setattr(ss, "persist_signals", lambda s: persistiu.append(list(s)))
    notificou = []
    monkeypatch.setattr(ss, "notificar_lote", lambda s: notificou.append(list(s)))

    ss.run_scan()

    assert len(persistiu) == 1 and persistiu[0] == [{"ticker": "A3.SA"}]
    assert len(notificou) == 1
