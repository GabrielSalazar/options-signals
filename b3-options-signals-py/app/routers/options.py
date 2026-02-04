from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.math_service import OptionMath

router = APIRouter(prefix="/options", tags=["Options"])

class PricingRequest(BaseModel):
    type: str # 'call' or 'put'
    S: float  # Spot price
    K: float  # Strike price
    t: float  # Time to expiration (years)
    r: float  # Risk-free rate (decimal, e.g. 0.1375 for 13.75%)
    sigma: float # Volatility (decimal, e.g. 0.30 for 30%)

@router.post("/calculate")
def calculate_option(request: PricingRequest):
    """
    Calculate theoretical price and Greeks for an option.
    """
    flag = request.type.lower()[0] # 'c' or 'p'
    
    price = OptionMath.calculate_price(flag, request.S, request.K, request.t, request.r, request.sigma)
    greeks = OptionMath.calculate_greeks(flag, request.S, request.K, request.t, request.r, request.sigma)
    
    if greeks is None:
        raise HTTPException(status_code=500, detail="Error calculating Greeks")

    return {
        "price": price,
        "greeks": greeks
    }
