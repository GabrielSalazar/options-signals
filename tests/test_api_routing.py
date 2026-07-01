"""Testes de resolução de rotas da API.

Garantem que cada caminho casa com o handler pretendido — em especial as rotas
literais sob /signals/scan/* que antes eram capturadas pela rota paramétrica
/signals/scan/{ticker} (bug de ordenação corrigido na refatoração em routers).

São testes de roteamento puro (não invocam handlers nem fazem I/O de rede).
"""
import os

import pytest

os.environ.setdefault("ALLOWED_ORIGINS", "*")

from backend.api.main import app  # noqa: E402


def _iter_leaf_routes(routes):
    """Percorre a árvore de rotas devolvendo só as rotas-folha (endpoints).

    Necessário porque o FastAPI >= 0.138 mudou o comportamento de
    `include_router`: ele NÃO achata mais os routers incluídos em
    `app.router.routes`. Cada router vira um wrapper `_IncludedRouter`
    (sem path/methods/path_regex) cujas rotas reais ficam em
    `.original_router.routes`. No FastAPI antigo as rotas já vinham
    achatadas — os dois casos são cobertos aqui:
      - `_IncludedRouter`  -> recursa em `.original_router.routes`;
      - Mount/sub-router   -> recursa em `.routes`;
      - Route (folha)      -> devolve.
    """
    for route in routes:
        original = getattr(route, "original_router", None)
        if original is not None and hasattr(original, "routes"):
            yield from _iter_leaf_routes(original.routes)
            continue
        sub = getattr(route, "routes", None)
        if sub:
            yield from _iter_leaf_routes(sub)
            continue
        yield route


def _resolve(method: str, path: str) -> str | None:
    """Retorna o nome do handler que casa com (method, path), ou None.

    Resolve na ordem de registro das rotas (primeira que casa vence),
    exatamente como o roteador do Starlette faz — o que é justamente o que
    este teste precisa validar (rota literal não pode ser sombreada pela
    paramétrica /{ticker}).

    Usa os atributos estáveis `path_regex` e `methods` do Route (via
    `_iter_leaf_routes`) em vez de `route.matches(scope)`: a semântica de
    scope do `matches()` mudou no Starlette 1.x e passou a devolver
    Match.NONE para um scope montado à mão, quebrando este teste no CI
    (onde o pip instala versões mais novas de starlette/fastapi) enquanto
    passava localmente.
    """
    for route in _iter_leaf_routes(app.router.routes):
        path_regex = getattr(route, "path_regex", None)
        methods = getattr(route, "methods", None)
        if path_regex is None or methods is None:
            continue
        if path_regex.match(path) and method in methods:
            return route.name
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
