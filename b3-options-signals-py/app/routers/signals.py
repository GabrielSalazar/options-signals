from fastapi import APIRouter, BackgroundTasks
from app.services.scanner import scanner

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.post("/scan/{ticker}")
async def trigger_scan(ticker: str, background_tasks: BackgroundTasks):
    """
    Trigger a manual scan for a specific ticker (e.g., PETR4).
    Runs strategies and sends alerts if opportunities are found.
    """
    # Run in background to not block response
    # For demo, we await it to return results immediately, but usually this is async
    results = await scanner.scan_ticker(ticker.upper())
    
    return {
        "message": f"Scan completed for {ticker}",
        "signals_found": len(results),
        "results": results
    }

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
