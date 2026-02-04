from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.services.scanner import scanner
from app.core.database import get_db
from app.services import crud

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.post("/scan/{ticker}")
async def trigger_scan(ticker: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger a manual scan for a specific ticker (e.g., PETR4).
    Runs strategies and sends alerts if opportunities are found.
    Persists results to database.
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

@router.get("/history")
def get_signal_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieve recent signals stored in the database.
    """
    return crud.get_recent_signals(db, limit)

@router.get("/strategies")
def list_strategies():
    return {
        "active_strategies": [
            {
                "name": s.name,
                "description": s.description,
                "risk_level": s.risk_level
            } 
            for s in scanner.strategies
        ]
    }
