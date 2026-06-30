"""Testes do router backend/api/routers/backtest.py.

Cobre:
  - GET /backtest/strategies: lista estática.
  - Validação de BacktestParams: ticker inválido → 422; normalização
    (upper + remoção de ".SA") aplicada antes do regex.
  - POST /backtest/run:
      * sem sinais (lista vazia) → metrics=None.
      * com sinais e >1 trade_return → cálculo de win_rate, equity_curve,
        max_drawdown, sharpe/sortino/calmar/expectancy (branches sharpe>0,
        sortino>0 e ==0, calmar>0).
      * com exatamente 1 sinal → branch len(trade_returns) <= 1 (zera as
        métricas avançadas).
      * serialização de "data_sinal" com .isoformat() quando presente.
      * end_date default (vazio) usa data de hoje.

Estratégia: como `rodar_backtest` é importado localmente dentro da função
(`from backend.services.backtest import rodar_backtest`), o patch precisa
atingir o nome no módulo de origem `backend.services.backtest.rodar_backtest`
— não em `backend.api.routers.backtest`, que não tem esse nome até a função
rodar.
"""
import pandas as pd
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)

_SVC = "backend.services.backtest.rodar_backtest"


def test_backtest_strategies_retorna_lista_estatica():
    resp = client.get("/backtest/strategies")
    assert resp.status_code == 200
    assert resp.json() == {"strategies": ["momentum", "reversao", "breakout"]}


def test_backtest_run_ticker_invalido_retorna_422():
    resp = client.post("/backtest/run", json={"ticker": "@@@@"})
    assert resp.status_code == 422


def test_backtest_run_ticker_normaliza_lower_e_sufixo_sa():
    """ticker minúsculo com .SA deve ser aceito (normalizado para upper sem sufixo)."""
    with patch(_SVC, return_value=[]) as mock_run:
        resp = client.post("/backtest/run", json={"ticker": "petr4.sa"})
    assert resp.status_code == 200
    # rodar_backtest deve ter sido chamado com o ticker normalizado + .SA
    args = mock_run.call_args[0]
    assert args[0] == "PETR4.SA"


def test_backtest_run_sem_sinais_retorna_metrics_none():
    with patch(_SVC, return_value=[]):
        resp = client.post("/backtest/run", json={"ticker": "PETR4"})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"sinais": 0, "metrics": None, "equity_curve": [], "data": []}


def _sinal_bt(**over):
    base = {
        "ticker": "PETR4", "hit_alvo1": False, "hit_stop": False, "max_return": 0.0,
    }
    base.update(over)
    return base


def test_backtest_run_com_multiplos_sinais_calcula_metricas():
    sinais = [
        _sinal_bt(hit_alvo1=True, max_return=0.5),
        _sinal_bt(hit_alvo1=False, hit_stop=True),
        _sinal_bt(hit_alvo1=False, hit_stop=False, max_return=0.1),
        _sinal_bt(hit_alvo1=True, max_return=0.2),
    ]
    with patch(_SVC, return_value=sinais):
        resp = client.post(
            "/backtest/run",
            json={"ticker": "PETR4", "start_date": "2024-01-01", "end_date": "2024-06-01"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sinais"] == 4
    metrics = body["metrics"]
    assert metrics is not None
    assert metrics["trades"] == 4
    # win_rate = 2/4 = 50%
    assert metrics["win_rate"] == 50.0
    assert len(body["equity_curve"]) == 5  # equity inicial + 4 trades
    assert body["equity_curve"][0] == 10000.0
    assert isinstance(metrics["sharpe_ratio"], float)
    assert isinstance(metrics["max_drawdown"], float)
    assert isinstance(metrics["expectancy"], float)
    assert body["data"] == sinais


def test_backtest_run_com_um_unico_sinal_zera_metricas_avancadas():
    """len(trade_returns) <= 1 → sharpe/sortino/calmar/expectancy ficam 0.0."""
    sinais = [_sinal_bt(hit_alvo1=True, max_return=0.3)]
    with patch(_SVC, return_value=sinais):
        resp = client.post("/backtest/run", json={"ticker": "VALE3"})
    assert resp.status_code == 200
    metrics = resp.json()["metrics"]
    assert metrics["sharpe_ratio"] == 0.0
    assert metrics["sortino_ratio"] == 0.0
    assert metrics["calmar_ratio"] == 0.0
    assert metrics["expectancy"] == 0.0
    assert metrics["win_rate"] == 100.0


def test_backtest_run_serializa_data_sinal_timestamp():
    """data_sinal vindo como pandas.Timestamp deve ser convertido via isoformat()."""
    sinais = [_sinal_bt(data_sinal=pd.Timestamp("2024-03-15"), hit_alvo1=True, max_return=0.1)]
    with patch(_SVC, return_value=sinais):
        resp = client.post("/backtest/run", json={"ticker": "ITUB4"})
    assert resp.status_code == 200
    data_sinal = resp.json()["data"][0]["data_sinal"]
    assert data_sinal == pd.Timestamp("2024-03-15").isoformat()


def test_backtest_run_sem_end_date_usa_hoje():
    """end_date vazio no payload → função deve invocar rodar_backtest com a
    data de hoje (formatada %Y-%m-%d) como 4º argumento."""
    from datetime import datetime
    hoje = datetime.now().strftime("%Y-%m-%d")
    with patch(_SVC, return_value=[]) as mock_run:
        resp = client.post("/backtest/run", json={"ticker": "PETR4", "start_date": "2024-01-01"})
    assert resp.status_code == 200
    args = mock_run.call_args[0]
    assert args[3] == hoje


def test_backtest_run_apenas_perdas_avg_win_zero():
    """Todos os trades são stop/perda (sem ganhos) → avg_win fica 0.0
    (branch `any(r > 0 ...)` falso) e expectancy reflete só perdas."""
    sinais = [
        _sinal_bt(hit_alvo1=False, hit_stop=True),
        _sinal_bt(hit_alvo1=False, hit_stop=True),
        _sinal_bt(hit_alvo1=False, hit_stop=False, max_return=0.0),
    ]
    with patch(_SVC, return_value=sinais):
        resp = client.post("/backtest/run", json={"ticker": "BBAS3"})
    assert resp.status_code == 200
    metrics = resp.json()["metrics"]
    assert metrics["win_rate"] == 0.0
    assert metrics["expectancy"] <= 0.0
