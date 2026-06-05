"""Testes de run_scan — seleção de universo, lote único de Telegram (sem rede)."""
from backend.services import signal_service as ss
from backend.core.config import ATIVOS_B3


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
