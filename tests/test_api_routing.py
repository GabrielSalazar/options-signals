"""Testes de resolução de rotas da API.

Garantem que cada caminho casa com o handler pretendido — em especial as rotas
literais sob /signals/scan/* que antes eram capturadas pela rota paramétrica
/signals/scan/{ticker} (bug de ordenação corrigido na refatoração em routers).

São testes de roteamento puro (não invocam handlers nem fazem I/O de rede).
"""
import os

import pytest
from starlette.routing import Match

os.environ.setdefault("ALLOWED_ORIGINS", "*")

from backend.api.main import app  # noqa: E402


def _resolve(method: str, path: str) -> str | None:
    """Retorna o nome do handler que casa com (method, path), ou None."""
    scope = {"type": "http", "method": method, "path": path, "headers": []}
    for route in app.router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "name", None)
    return None


@pytest.mark.parametrize("method,path,expected", [
    ("GET", "/health", "health"),
    ("GET", "/signals", "get_signals"),
    ("POST", "/signals/scan", "scan_batch"),
    # Rotas literais NÃO podem ser capturadas pela paramétrica /{ticker}:
    ("GET", "/signals/scan/stream", "scan_stream"),
    ("GET", "/signals/alerts/stream", "alerts_stream"),
    ("POST", "/signals/scan/all", "scan_all"),
    ("POST", "/signals/scan/all-b3", "scan_all_b3"),
    # Rota paramétrica continua atendendo tickers reais:
    ("POST", "/signals/scan/PETR4", "scan_ticker"),
    ("GET", "/signals/scan/PETR4", "scan_ticker_get"),
    ("GET", "/signals/history", "get_history"),
    ("GET", "/signals/watchlist", "get_watchlist"),
    ("GET", "/signals/analytics/PETR4", "analytics"),
    ("GET", "/signals/performance", "signals_performance"),
    ("GET", "/signals/strategies", "get_strategies"),
    ("GET", "/backtest/strategies", "backtest_strategies"),
    ("POST", "/backtest/run", "backtest_run"),
    ("GET", "/market", "get_market"),
    ("GET", "/market/opcoes", "get_market_options"),
    ("GET", "/market/opcoes/chain/PETR4", "get_options_chain"),
    ("GET", "/config/telegram", "get_telegram"),
    ("POST", "/config/telegram", "set_telegram"),
])
def test_route_resolves_to_expected_handler(method, path, expected):
    assert _resolve(method, path) == expected
