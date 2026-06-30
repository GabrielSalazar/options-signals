"""Repositório de acesso à tabela `signals` no Supabase.

Centraliza as queries que antes eram feitas diretamente em
`backend/api/routers/signals.py`. Cada função recebe o cliente `supabase` já
obtido pelo chamador — o router é quem chama `get_supabase()`, decide se o
resultado é `None` (e usa o fallback em memória) e só invoca este
repositório quando o cliente está disponível. Isso preserva o ponto único de
monkeypatch usado pelos testes existentes (`routers.signals.get_supabase`).
"""


def fetch_signals(supabase, limit: int, offset: int, tipo: str | None, min_score: int):
    """Extraído de routers/signals.py::get_signals — query original preservada 1:1."""
    query = (supabase.table("signals")
             .select("*", count="exact")
             .order("timestamp", desc=True))
    if tipo:
        query = query.eq("tipo_sinal", tipo)
    if min_score > 0:
        query = query.gte("score", min_score)
    return query.range(offset, offset + limit - 1).execute()


def fetch_history(supabase, limit: int, offset: int, ticker: str | None, tipo_sinal: str | None):
    """Extraído de routers/signals.py::get_history — query original preservada 1:1."""
    query = supabase.table("signals").select("*").order("timestamp", desc=True)
    if ticker:
        query = query.eq("ticker", ticker.upper())
    if tipo_sinal:
        query = query.eq("tipo_sinal", tipo_sinal.upper())
    return query.range(offset, offset + limit - 1).execute()


def fetch_analytics(supabase, ticker_upper: str):
    """Extraído de routers/signals.py::analytics — query original preservada 1:1."""
    return (supabase.table("signals")
            .select("*")
            .eq("ticker", ticker_upper)
            .order("timestamp", desc=True)
            .limit(100)
            .execute())


def fetch_performance(supabase, cutoff_iso: str):
    """Extraído de routers/signals.py::signals_performance — query original preservada 1:1."""
    return (supabase.table("signals")
            .select("ticker, tipo_sinal, score, score_ponderado, ponderado_passou, entrada_max, alvo1, alvo2, alvo_final, stop, timestamp, greeks")
            .gte("timestamp", cutoff_iso)
            .order("timestamp", desc=True)
            .limit(2000)
            .execute())
