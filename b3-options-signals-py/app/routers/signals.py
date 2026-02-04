from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from app.services.scanner import scanner
from app.core.database import get_db
from app.services import crud
from app.core.auth import verify_token
from typing import List
import asyncio

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.post("/scan/{ticker}")
async def trigger_scan(
    request: Request,
    ticker: str, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Trigger a manual scan for a specific ticker (e.g., PETR4).
    Runs strategies and sends alerts if opportunities are found.
    Persists results to database.
    
    **Rate Limit**: 10 requests/minute
    **Auth**: Requires Bearer token
    """
    # Rate limiting is handled by decorator in main.py via limiter
    from app.main import limiter
    limiter.limit("10/minute")(request)
    
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
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Scan multiple tickers simultaneously (batch operation).
    
    **Rate Limit**: 5 requests/minute
    **Auth**: Requires Bearer token
    """
    from app.main import limiter
    limiter.limit("5/minute")(request)
    
    # Scan all tickers in parallel
    results = await asyncio.gather(*[scanner.scan_ticker(t.upper()) for t in tickers])
    
    # Flatten and save to DB
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
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Retrieve recent signals stored in the database.
    
    **Rate Limit**: 30 requests/minute
    **Auth**: Requires Bearer token
    """
    from app.main import limiter
    limiter.limit("30/minute")(request)
    
    return crud.get_recent_signals(db, limit)

@router.get("/strategies")
def list_strategies():
    from app.core.risk_classifier import get_risk_info
    
    return {
        "active_strategies": [
            {
                "name": s.name,
                "description": s.description,
                "risk_level": s.risk_level,
                "risk_info": get_risk_info(s.name)
            } 
            for s in scanner.strategies
        ]
    }
