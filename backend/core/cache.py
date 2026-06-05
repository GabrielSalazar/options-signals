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
import time
import json
import logging

logger = logging.getLogger("b3_cache")

_client = None
_unavailable = False  # set True after first failed connect to avoid retrying
_redis_url_configured = bool(os.getenv("REDIS_URL"))

# Fallback TTL in-process: usado quando o Redis não está disponível, para que o
# cache continue funcionando (evita rebaixar OHLCV/chains a cada scan → rate-limit). [P0]
_mem: dict = {}  # key -> (expiry_epoch, value)
_MEM_MAX = 1000  # teto de entradas; ao exceder, faz prune das expiradas


def _mem_get(key: str):
    item = _mem.get(key)
    if item is None:
        return None
    expiry, value = item
    if time.time() > expiry:
        _mem.pop(key, None)
        return None
    return value


def _mem_set(key: str, value, ttl: int):
    if len(_mem) >= _MEM_MAX:
        agora = time.time()
        for k in [k for k, (exp, _) in _mem.items() if exp <= agora]:
            _mem.pop(k, None)
    _mem[key] = (time.time() + ttl, value)


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
        return _mem_get(key)
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value, ttl: int = 300):
    r = _get_redis()
    if not r:
        _mem_set(key, value, ttl)
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_get_df(key: str):
    """Retorna DataFrame cacheado ou None."""
    r = _get_redis()
    if not r:
        df = _mem_get(key)
        return df.copy() if df is not None else None
    try:
        import pandas as pd
        from io import StringIO
        raw = r.get(key)
        return pd.read_json(StringIO(raw)) if raw else None
    except Exception:
        return None


def cache_set_df(key: str, df, ttl: int = 300):
    """Cacheia um DataFrame (objeto em memória; JSON no Redis)."""
    r = _get_redis()
    if not r:
        _mem_set(key, df.copy(), ttl)
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

