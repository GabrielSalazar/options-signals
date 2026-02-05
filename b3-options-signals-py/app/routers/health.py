from fastapi import APIRouter
from app.data import B3RealData, cache
import logging

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health():
    """
    Verifica a saúde do sistema e das fontes de dados reais.
    
    Testa:
    - StatusInvest/Yahoo (via B3RealData)
    - Conexão Redis
    """
    health_status = {
        "status": "healthy",
        "data_source": "real",
        "components": {
            "api": "ok",
            "redis": "unknown",
            "market_data": "unknown"
        }
    }
    
    # 1. Verifica Redis
    try:
        await cache.connect()
        redis_stats = await cache.get_stats()
        if redis_stats.get('enabled') or redis_stats.get('error') is None:
             health_status["components"]["redis"] = "ok"
        else:
             health_status["components"]["redis"] = "degraded"
    except Exception as e:
        health_status["components"]["redis"] = "error"
        health_status["status"] = "degraded"
    
    # 2. Verifica Dados de Mercado (Yahoo Finance - Busca rápida cotação)
    try:
        client = B3RealData()
        # Tenta buscar uma cotação simples
        await client.get_cotacao("PETR4")
        health_status["components"]["market_data"] = "ok"
    except Exception as e:
        health_status["components"]["market_data"] = "error"
        health_status["status"] = "degraded"
        health_status["error"] = str(e)
        
    return health_status
