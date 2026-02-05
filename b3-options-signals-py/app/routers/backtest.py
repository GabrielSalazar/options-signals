from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from app.core.backtester import VectorizedBacktester
from app.services.scanner import scanner # Using scanner to access initialized strategies
from app.core.auth import verify_token

router = APIRouter(prefix="/backtest", tags=["Backtest"])

class BacktestRequest(BaseModel):
    ticker: str
    strategy_name: str
    days: int = 252
    initial_capital: float = 10000.0

@router.post("/run")
async def run_backtest(
    request: Request,
    req: BacktestRequest
    # token: str = Depends(verify_token)  # Disabled for local development
):
    """
    Runs a backtest simulation for a specific strategy and ticker.
    
    **Rate Limit**: 5 requests/minute (computationally expensive)
    **Auth**: Public endpoint (auth disabled for development)
    """
    # Rate limiting is handled via decorators in main.py
    
    # 1. Find the strategy instance
    # Normalizes name comparison
    strategy = next((s for s in scanner.strategies if s.name == req.strategy_name), None)
    
    if not strategy:
        # Fallback: Try partial match or ID
        raise HTTPException(status_code=404, detail=f"Strategy '{req.strategy_name}' not found. Available: {[s.name for s in scanner.strategies]}")

    backtester = VectorizedBacktester()
    
    result = await backtester.run_backtest(
        strategy=strategy,
        ticker=req.ticker.upper(),
        days=req.days,
        initial_capital=req.initial_capital
    )
    
    if "error" in result:
         raise HTTPException(status_code=400, detail=result['error'])
         
    return {
        "message": "Backtest completed successfully",
        "parameters": req.dict(),
        "metrics": result
    }

@router.get("/strategies")
def get_backtest_strategies():
    return [s.name for s in scanner.strategies]
