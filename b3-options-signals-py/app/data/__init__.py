"""
Módulo de dados reais da B3.

Integra múltiplas fontes:
- StatusInvest (cadeia de opções)
- Yahoo Finance (cotações e histórico)
- Redis (cache/fallback)
"""

from .real_time import B3RealData
from .technicals import TechnicalIndicators
from .cache import RedisCache, cache

__all__ = ['B3RealData', 'TechnicalIndicators', 'RedisCache', 'cache']
