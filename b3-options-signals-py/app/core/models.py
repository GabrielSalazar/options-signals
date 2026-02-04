from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.core.database import Base

class SignalModel(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    strategy = Column(String)
    option_symbol = Column(String)
    signal_type = Column(String) # SELL CALL, BUY PUT etc
    spot_price = Column(Float)
    strike = Column(Float)
    reason = Column(String)
    recommendation = Column(String)
    risk_level = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
