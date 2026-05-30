"""
Redis cache wrapper com fallback gracioso.
Se REDIS_URL não estiver configurado ou Redis estiver indisponível,
todas as operações são no-op — o app funciona normalmente sem cache.

Funções públicas:
  cache_get / cache_set      — valores JSON (dict, list, str, etc.)
  cache_get_df / cache_set_df — DataFrames pandas
  redis_status               — dict com estado da conexão (para /health)
"""
import os
import json
import logging

logger = logging.getLogger("b3_cache")

_client = None
_unavailable = False  # set True after first failed connect to avoid retrying
_redis_url_configured = bool(os.getenv("REDIS_URL"))


def _get_redis():
    global _client, _unavailable
    if _unavailable:
        return None
    if _client is not None:
        return _client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        _client = r
        logger.info("Redis conectado")
        return _client
    except Exception as e:
        logger.warning(f"Redis indisponível ({e}). Cache desabilitado.")
        _unavailable = True
        return None


def cache_get(key: str):
    r = _get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value, ttl: int = 300):
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_get_df(key: str):
    """Retorna DataFrame cacheado ou None."""
    r = _get_redis()
    if not r:
        return None
    try:
        import pandas as pd
        raw = r.get(key)
        return pd.read_json(raw) if raw else None
    except Exception:
        return None


def cache_set_df(key: str, df, ttl: int = 300):
    """Cacheia um DataFrame como JSON."""
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, df.to_json())
    except Exception:
        pass


def redis_status() -> dict:
    """
    Retorna um dict descrevendo o estado atual da conexão Redis.
    Útil para expor no endpoint /health sem forçar uma nova tentativa de conexão.

    Campos retornados:
      - enabled  (bool): True se REDIS_URL está configurada na env.
      - connected (bool): True se a conexão está ativa e o ping respondeu.
      - status   (str):  'connected' | 'disabled' | 'unavailable' | 'not_initialized'
    """
    global _client, _unavailable
    if not _redis_url_configured:
        return {"enabled": False, "connected": False, "status": "disabled"}
    if _client is not None:
        try:
            _client.ping()
            return {"enabled": True, "connected": True, "status": "connected"}
        except Exception:
            return {"enabled": True, "connected": False, "status": "unavailable"}
    if _unavailable:
        return {"enabled": True, "connected": False, "status": "unavailable"}
    # ainda não tentou conectar nesta sessão
    return {"enabled": True, "connected": False, "status": "not_initialized"}

