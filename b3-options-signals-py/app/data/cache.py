"""
Sistema de cache Redis para fallback de dados reais.

Armazena:
- Cotações (TTL 15min)
- Cadeias de opções (TTL 15min)
- Indicadores técnicos (TTL 5min)
- Históricos (TTL 1h)
"""

import redis.asyncio as redis
import json
import pandas as pd
from typing import Optional, Any, Dict
from datetime import timedelta
import logging
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Cliente Redis para cache de dados de mercado."""
    
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        # TTLs padrão
        self.ttl_cotacao = 900  # 15 minutos
        self.ttl_cadeia = 900   # 15 minutos
        self.ttl_technicals = 300  # 5 minutos
        self.ttl_historico = 3600  # 1 hora
    
    async def connect(self):
        """Conecta ao Redis."""
        if not self.enabled:
            logger.info("Redis cache desabilitado")
            return
        
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"Conectado ao Redis: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Não foi possível conectar ao Redis: {e}. Cache desabilitado.")
            self.enabled = False
            self.redis_client = None
    
    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Desconectado do Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Busca valor do cache."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar do cache {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int):
        """Armazena valor no cache."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"Erro ao salvar no cache {key}: {e}")
    
    async def delete(self, key: str):
        """Remove valor do cache."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Erro ao deletar do cache {key}: {e}")
    
    # Métodos específicos para dados de mercado
    
    async def get_cotacao(self, ticker: str) -> Optional[Dict]:
        """Busca cotação do cache."""
        key = f"cotacao:{ticker}"
        return await self.get(key)
    
    async def set_cotacao(self, ticker: str, data: Dict):
        """Armazena cotação no cache."""
        key = f"cotacao:{ticker}"
        await self.set(key, data, self.ttl_cotacao)
    
    async def get_cadeia_opcoes(self, ticker: str) -> Optional[pd.DataFrame]:
        """Busca cadeia de opções do cache."""
        key = f"cadeia:{ticker}"
        data = await self.get(key)
        
        if data:
            try:
                return pd.DataFrame(data)
            except Exception as e:
                logger.error(f"Erro ao converter cadeia do cache: {e}")
                return None
        return None
    
    async def set_cadeia_opcoes(self, ticker: str, df: pd.DataFrame):
        """Armazena cadeia de opções no cache."""
        key = f"cadeia:{ticker}"
        data = df.to_dict('records')
        await self.set(key, data, self.ttl_cadeia)
    
    async def get_technicals(self, ticker: str) -> Optional[Dict]:
        """Busca indicadores técnicos do cache."""
        key = f"technicals:{ticker}"
        return await self.get(key)
    
    async def set_technicals(self, ticker: str, data: Dict):
        """Armazena indicadores técnicos no cache."""
        key = f"technicals:{ticker}"
        await self.set(key, data, self.ttl_technicals)
    
    async def get_historico(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """Busca histórico do cache."""
        key = f"historico:{ticker}:{days}"
        data = await self.get(key)
        
        if data:
            try:
                df = pd.DataFrame(data)
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                return df
            except Exception as e:
                logger.error(f"Erro ao converter histórico do cache: {e}")
                return None
        return None
    
    async def set_historico(self, ticker: str, days: int, df: pd.DataFrame):
        """Armazena histórico no cache."""
        key = f"historico:{ticker}:{days}"
        
        # Reset index se for DatetimeIndex
        df_copy = df.copy()
        if isinstance(df_copy.index, pd.DatetimeIndex):
            df_copy = df_copy.reset_index()
        
        data = df_copy.to_dict('records')
        await self.set(key, data, self.ttl_historico)
    
    async def get_stats(self) -> Dict:
        """Retorna estatísticas do cache."""
        if not self.enabled or not self.redis_client:
            return {'enabled': False}
        
        try:
            info = await self.redis_client.info('stats')
            return {
                'enabled': True,
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1) * 100
            }
        except Exception as e:
            logger.error(f"Erro ao buscar stats do cache: {e}")
            return {'enabled': True, 'error': str(e)}


# Instância global
cache = RedisCache()
