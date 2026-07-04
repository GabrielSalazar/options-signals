"""Taxa livre de risco (SELIC meta anual) via BCB/SGS com cache de 24h e fallback.

Série SGS 432 = meta Selic definida pelo Copom (% a.a.). Convertida para decimal.
Mantém a camada de domínio (greeks.py) pura: a taxa é injetada nos call sites.
"""
import logging
import time

from bcb import sgs

from backend.domain.greeks import RISK_FREE_RATE_DEFAULT

logger = logging.getLogger("b3_api")

_SGS_SELIC_META = 432
_TTL_SEGUNDOS = 24 * 3600

_cache_valor: float | None = None
_cache_ts: float = 0.0


def _invalidate_cache() -> None:
    """Uso em testes: zera o cache em memória."""
    global _cache_valor, _cache_ts
    _cache_valor = None
    _cache_ts = 0.0


def get_selic_anual() -> float:
    """Retorna a SELIC meta anual em decimal (ex.: 0.15). Fallback: RISK_FREE_RATE_DEFAULT."""
    global _cache_valor, _cache_ts
    agora = time.time()
    if _cache_valor is not None and (agora - _cache_ts) < _TTL_SEGUNDOS:
        return _cache_valor
    try:
        df = sgs.get({"selic": _SGS_SELIC_META}, last=1)
        valor_percent = float(df["selic"].iloc[-1])
        taxa = valor_percent / 100.0
        _cache_valor = taxa
        _cache_ts = agora
        return taxa
    except Exception as e:
        logger.warning(f"SELIC via BCB indisponível ({e}); usando fallback {RISK_FREE_RATE_DEFAULT}")
        return RISK_FREE_RATE_DEFAULT
