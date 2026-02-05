from fastapi import APIRouter, BackgroundTasks, Depends, Request, Query
from sqlalchemy.orm import Session
from app.services.scanner import scanner
from app.core.database import get_db
from app.services import crud
from app.core.auth import verify_token
from typing import List, Optional
import asyncio

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.get("")
async def get_signals(
    request: Request,
    ativos: List[str] = Query(default=["PETR4", "VALE3", "BOVA11"]),
    min_confidence: float = Query(default=60.0, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para buscar sinais filtrados com DADOS REAIS.
    
    - Busca cotações e cadeias de opções reais
    - Calcula indicadores técnicos
    - Aplica todas as estratégias
    - Filtra por confiança mínima
    """
    # Executa scan para todos os ativos em paralelo
    results = await asyncio.gather(*[scanner.scan_ticker(t.upper()) for t in ativos])
    
    # Flatten results
    all_signals = []
    for ticker_res in results:
        all_signals.extend(ticker_res)
    
    # Filtra por score de confiabilidade
    filtered_signals = [
        s for s in all_signals 
        if s.get('confidence_score', 0) >= min_confidence
    ]
    
    # Persiste sinais encontrados
    for signal in filtered_signals:
        try:
            crud.create_signal(db, signal)
        except Exception as e:
            print(f"Erro ao salvar sinal no DB: {e}")

    return {
        "metadata": {
            "data_source": "real",
            "tickers_scanned": ativos,
            "total_signals": len(filtered_signals),
            "min_confidence": min_confidence
        },
        "signals": filtered_signals
    }

@router.post("/scan/{ticker}")
async def trigger_scan(
    request: Request,
    ticker: str, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Trigger a manual scan for a specific ticker (e.g., PETR4).
    """
    results = await scanner.scan_ticker(ticker.upper())
    
    # Save to DB
    for signal in results:
        crud.create_signal(db, signal)

    return {
        "message": f"Scan completed for {ticker}",
        "signals_found": len(results),
        "results": results
    }

@router.post("/scan")
async def batch_scan(
    request: Request,
    tickers: List[str],
    db: Session = Depends(get_db)
):
    """
    Scan multiple tickers simultaneously (batch operation).
    """
    results = await asyncio.gather(*[scanner.scan_ticker(t.upper()) for t in tickers])
    
    all_signals = []
    for ticker_results in results:
        for signal in ticker_results:
            crud.create_signal(db, signal)
            all_signals.append(signal)
    
    return {
        "message": f"Batch scan completed for {len(tickers)} tickers",
        "tickers": [t.upper() for t in tickers],
        "total_signals": len(all_signals),
        "signals_by_ticker": {
            tickers[i].upper(): len(results[i]) for i in range(len(tickers))
        }
    }

@router.get("/watchlist")
def get_watchlist():
    """
    Get the configured watchlist (public endpoint).
    """
    from app.core.watchlist import get_watchlist
    return {"watchlist": get_watchlist()}

@router.get("/history")
def get_signal_history(
    request: Request,
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    """
    Retrieve recent signals stored in the database.
    """
    return crud.get_recent_signals(db, limit)

@router.get("/strategies")
def list_strategies():
    try:
        from app.core.risk_classifier import get_risk_info
        
        strategies_list = []
        for s in scanner.strategies:
            try:
                risk_info = get_risk_info(s.name)
                strategies_list.append({
                    "name": s.name,
                    "description": getattr(s, 'description', s.name), # Fallback seguro
                    "risk_level": s.risk_level,
                    "risk_info": risk_info
                })
            except Exception as e:
                print(f"Error processing strategy {s.name}: {e}")
                strategies_list.append({
                    "name": s.name,
                    "description": s.name,
                    "risk_level": s.risk_level,
                    "risk_info": {"level": "MEDIUM", "icon": "🟡", "max_loss": "N/A", "description": "Error loading risk info"}
                })
        
        return {"active_strategies": strategies_list}
    except Exception as e:
        print(f"FATAL ERROR in list_strategies: {e}")
        import traceback
        traceback.print_exc()
        raise
