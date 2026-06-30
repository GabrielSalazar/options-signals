"""Testes de backend/services/backtest.py (serviço de backtest "de fato",
não confundir com o router backend/api/routers/backtest.py — já cobre 100%
em tests/test_backtest.py via mock de rodar_backtest).

Cobre:
  - rodar_backtest:
      * yf.download retorna DataFrame vazio → [] (early return, linha 22-24).
      * yf.download retorna poucas linhas (< 30) → [] (mesmo gate).
      * dados suficientes mas após calcular_indicadores+dropna restam
        < _WINDOW + 10 linhas → [] (linha 32-34).
      * fluxo feliz: histórico suficiente, analisar_ativo emite sinal em
        pelo menos uma janela → sinal enriquecido com data_sinal, hit_alvo1,
        hit_stop, max_return.
      * branch hit_alvo1 (future_premio >= alvo1) interrompe o loop forward.
      * branch hit_stop (future_premio <= stop) marca hit_stop sem dar break.
      * branch "nenhum target/stop atingido" no horizonte → hit_alvo1/hit_stop
        False e max_return é o maior retorno observado.
      * colunas de yf.download vindo como MultiIndex (tuplas) são normalizadas
        para nomes simples (linha 26).
      * analisar_ativo retornando None em todas as janelas → sinais_encontrados
        vazio mas execução completa sem erro.
  - exibir_relatorio_backtest:
      * lista vazia → apenas imprime mensagem, não lança.
      * lista com sinais → imprime relatório (cobre cálculo de win_rate,
        filtragem CALL/PUT, e leitura best-effort de planilha de referência
        ausente/sem coluna esperada, que cai no except).
"""
import numpy as np
import pandas as pd
import pytest

from backend.services import backtest as bt


def _make_raw_ohlcv(n: int, seed: int = 0, multiindex_cols: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 13.0 + np.cumsum(rng.normal(0, 0.12, n))
    close = np.maximum(close, 1.0)
    high = close * (1 + rng.uniform(0.002, 0.012, n))
    low = close * (1 - rng.uniform(0.002, 0.012, n))
    openp = close + rng.normal(0, 0.05, n)
    vol = rng.uniform(2_000_000, 5_000_000, n)
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {"Open": openp, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )
    if multiindex_cols:
        df.columns = pd.MultiIndex.from_product([df.columns, ["PETR4.SA"]])
    return df


# ── rodar_backtest: gates de dados insuficientes ────────────────────────────

def test_rodar_backtest_df_vazio_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: pd.DataFrame())
    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")
    assert out == []


def test_rodar_backtest_poucas_linhas_retorna_lista_vazia(monkeypatch):
    df = _make_raw_ohlcv(10)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)
    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")
    assert out == []


def test_rodar_backtest_insuficiente_apos_indicadores_e_dropna(monkeypatch):
    """len(df_full) >= 30 (passa o 1º gate) mas após calcular_indicadores+dropna
    restam menos que _WINDOW + 10 linhas (linha 32-34)."""
    df = _make_raw_ohlcv(35)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)
    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")
    assert out == []


def test_rodar_backtest_normaliza_colunas_multiindex(monkeypatch):
    """Colunas vindo como tuplas (yfinance multi-ticker) são reduzidas ao
    primeiro elemento (linha 26) antes de calcular indicadores."""
    df = _make_raw_ohlcv(35, multiindex_cols=True)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)
    # Não deve lançar KeyError/AttributeError ao tentar acessar "Close" etc.
    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")
    assert out == []  # ainda insuficiente após indicadores, mas não quebrou


# ── rodar_backtest: fluxo principal com analisar_ativo mockado ─────────────

def _sinal_base(strike_ref=14.0, premio_est=0.5, alvo1=0.6, stop=0.3, dte=20,
                 hv_20d=30.0, tipo_sinal="CALL"):
    return {
        "ticker": "PETR4.SA", "tipo_sinal": tipo_sinal, "score": 9,
        "strike_ref": strike_ref, "premio_est": premio_est,
        "alvo1": alvo1, "alvo2": alvo1 * 2, "alvo_final": alvo1 * 3, "stop": stop,
        "dte": dte, "hv_20d": hv_20d,
    }


def test_rodar_backtest_sem_sinais_retorna_lista_vazia(monkeypatch):
    """analisar_ativo retorna None em todas as janelas → loop completa sem
    adicionar nada a sinais_encontrados."""
    df = _make_raw_ohlcv(150)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)
    monkeypatch.setattr(bt, "analisar_ativo", lambda *a, **k: None)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert out == []


def test_rodar_backtest_emite_sinal_e_simula_hit_alvo1(monkeypatch):
    """analisar_ativo emite sinal na primeira janela avaliada; o forward
    simulation deve detectar hit_alvo1 quando estimar_premio_otm sobe o
    suficiente para cruzar o alvo1."""
    df = _make_raw_ohlcv(150)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)

    chamadas = {"n": 0}

    def _fake_analisar(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return _sinal_base(premio_est=0.5, alvo1=0.6, stop=0.3)
        return None

    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar)
    # Premio futuro sempre acima do alvo1 (0.6) → hit_alvo1 no primeiro passo
    monkeypatch.setattr(bt, "estimar_premio_otm", lambda *a, **k: 0.9)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert len(out) == 1
    sinal = out[0]
    assert sinal["hit_alvo1"] is True
    assert sinal["hit_stop"] is False
    assert sinal["max_return"] == pytest.approx((0.9 - 0.5) / 0.5)
    assert "data_sinal" in sinal


def test_rodar_backtest_emite_sinal_e_simula_hit_stop(monkeypatch):
    """estimar_premio_otm sempre abaixo do stop → hit_stop fica True; o loop
    não dá break (continua monitorando para max_return) mas não deve crashar."""
    df = _make_raw_ohlcv(150)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)

    chamadas = {"n": 0}

    def _fake_analisar(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return _sinal_base(premio_est=0.5, alvo1=0.6, stop=0.3)
        return None

    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar)
    monkeypatch.setattr(bt, "estimar_premio_otm", lambda *a, **k: 0.1)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert len(out) == 1
    sinal = out[0]
    assert sinal["hit_stop"] is True
    assert sinal["hit_alvo1"] is False
    # max_return parte de 0.0 e usa max(atual, retorno); como o retorno é
    # sempre negativo aqui, max_return permanece 0.0 (nunca supera o piso).
    assert sinal["max_return"] == 0.0


def test_rodar_backtest_sem_atingir_alvo_ou_stop_acumula_max_return(monkeypatch):
    """Premio futuro fica entre stop e alvo1 (não dispara nenhum dos dois);
    max_return reflete o maior retorno do horizonte simulado."""
    df = _make_raw_ohlcv(150)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)

    chamadas = {"n": 0}

    def _fake_analisar(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return _sinal_base(premio_est=0.5, alvo1=0.9, stop=0.1)
        return None

    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar)
    # Premio sobe levemente, sem cruzar nem alvo1 (0.9) nem stop (0.1)
    valores = iter([0.52, 0.55, 0.6, 0.58])

    def _fake_premio(*a, **k):
        return next(valores, 0.58)

    monkeypatch.setattr(bt, "estimar_premio_otm", _fake_premio)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert len(out) == 1
    sinal = out[0]
    assert sinal["hit_alvo1"] is False
    assert sinal["hit_stop"] is False
    assert sinal["max_return"] == pytest.approx((0.6 - 0.5) / 0.5)


def test_rodar_backtest_multiplos_sinais_em_janelas_diferentes(monkeypatch):
    """analisar_ativo emite em mais de uma janela → múltiplos sinais
    acumulados em sinais_encontrados."""
    df = _make_raw_ohlcv(150)
    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: df)

    chamadas = {"n": 0}

    def _fake_analisar(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] in (1, 5):
            return _sinal_base(premio_est=0.5, alvo1=0.6, stop=0.3)
        return None

    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar)
    monkeypatch.setattr(bt, "estimar_premio_otm", lambda *a, **k: 0.55)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert len(out) == 2


def test_rodar_backtest_horizonte_reduzido_no_final_da_serie(monkeypatch):
    """Quando o sinal ocorre perto do fim da série, o horizonte de forward
    simulation é truncado por `min(15, len(df_full) - i)` sem erro de índice.
    `calcular_indicadores` muta o DataFrame recebido, então cada chamada a
    rodar_backtest precisa de uma cópia/instância nova de yf.download."""
    n = 150

    # Descobre quantas janelas existirão após calcular indicadores: dispara
    # apenas na ÚLTIMA chamada possível, forçando horizonte mínimo.
    chamadas = {"n": 0}

    def _fake_analisar(*a, **k):
        chamadas["n"] += 1
        return None  # primeira passada só para contar quantas janelas existem

    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: _make_raw_ohlcv(n))
    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar)
    bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")
    total_janelas = chamadas["n"]
    assert total_janelas > 0

    chamadas2 = {"n": 0}

    def _fake_analisar_ultima(*a, **k):
        chamadas2["n"] += 1
        if chamadas2["n"] == total_janelas:  # última janela da série
            return _sinal_base(premio_est=0.5, alvo1=0.6, stop=0.3)
        return None

    monkeypatch.setattr(bt.yf, "download", lambda *a, **k: _make_raw_ohlcv(n))
    monkeypatch.setattr(bt, "analisar_ativo", _fake_analisar_ultima)
    monkeypatch.setattr(bt, "estimar_premio_otm", lambda *a, **k: 0.4)

    out = bt.rodar_backtest("PETR4.SA", "Petrobras", "2025-01-01", "2025-06-01")

    assert len(out) == 1
    assert out[0]["hit_alvo1"] is False
    assert out[0]["hit_stop"] is False


# ── exibir_relatorio_backtest ───────────────────────────────────────────────

def test_exibir_relatorio_backtest_lista_vazia_nao_lanca(capsys):
    bt.exibir_relatorio_backtest([])
    captured = capsys.readouterr()
    assert "Nenhum sinal encontrado" in captured.out


def test_exibir_relatorio_backtest_com_sinais_imprime_metricas(capsys):
    sinais = [
        {"data_sinal": pd.Timestamp("2025-03-01"), "ticker": "PETR4.SA",
         "tipo_sinal": "CALL", "score": 9, "strike_ref": 14.0,
         "hit_alvo1": True, "hit_stop": False, "max_return": 0.4},
        {"data_sinal": pd.Timestamp("2025-03-05"), "ticker": "PETR4.SA",
         "tipo_sinal": "PUT", "score": 7, "strike_ref": 13.0,
         "hit_alvo1": False, "hit_stop": True, "max_return": -0.2},
    ]
    bt.exibir_relatorio_backtest(sinais)
    captured = capsys.readouterr()
    assert "RELATÓRIO DE BACKTEST" in captured.out
    assert "Total de sinais emitidos: 2" in captured.out
    assert "Calls: 1" in captured.out
    assert "Puts: 1" in captured.out
    assert "Win Rate" in captured.out


def test_exibir_relatorio_backtest_planilha_referencia_ausente_nao_lanca(capsys, monkeypatch):
    """read_excel falhando (arquivo ausente) cai no except silencioso (linhas
    103-108) sem propagar exceção."""
    monkeypatch.setattr(bt.pd, "read_excel",
                        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("sem planilha")))
    sinais = [
        {"data_sinal": pd.Timestamp("2025-03-01"), "ticker": "PETR4.SA",
         "tipo_sinal": "CALL", "score": 9, "strike_ref": 14.0,
         "hit_alvo1": True, "hit_stop": False, "max_return": 0.4},
    ]
    bt.exibir_relatorio_backtest(sinais)  # não deve lançar
    captured = capsys.readouterr()
    assert "RELATÓRIO DE BACKTEST" in captured.out


def test_exibir_relatorio_backtest_planilha_referencia_sem_coluna_esperada(capsys, monkeypatch):
    """read_excel funciona mas sem a coluna 'CÓDIGO OPÇÃO' → branch do `if`
    não imprime a linha de info, mas também não lança."""
    monkeypatch.setattr(bt.pd, "read_excel",
                        lambda *a, **k: pd.DataFrame({"OUTRA_COLUNA": [1, 2]}))
    sinais = [
        {"data_sinal": pd.Timestamp("2025-03-01"), "ticker": "PETR4.SA",
         "tipo_sinal": "CALL", "score": 9, "strike_ref": 14.0,
         "hit_alvo1": True, "hit_stop": False, "max_return": 0.4},
    ]
    bt.exibir_relatorio_backtest(sinais)
    captured = capsys.readouterr()
    assert "Planilha de referência carregada" not in captured.out


def test_exibir_relatorio_backtest_planilha_referencia_com_coluna_esperada(capsys, monkeypatch):
    """read_excel retorna DataFrame com a coluna esperada → imprime linha de
    info de planilha de referência carregada (linha 105-106)."""
    monkeypatch.setattr(bt.pd, "read_excel",
                        lambda *a, **k: pd.DataFrame({"CÓDIGO OPÇÃO": ["PETRC405", "PETRC410"]}))
    sinais = [
        {"data_sinal": pd.Timestamp("2025-03-01"), "ticker": "PETR4.SA",
         "tipo_sinal": "CALL", "score": 9, "strike_ref": 14.0,
         "hit_alvo1": True, "hit_stop": False, "max_return": 0.4},
    ]
    bt.exibir_relatorio_backtest(sinais)
    captured = capsys.readouterr()
    assert "Planilha de referência carregada" in captured.out
