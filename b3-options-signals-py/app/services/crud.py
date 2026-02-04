from sqlalchemy.orm import Session
from app.core.models import SignalModel

def create_signal(db: Session, signal_data: dict):
    db_signal = SignalModel(
        ticker=signal_data['ticker'],
        strategy=signal_data['strategy'],
        option_symbol=signal_data['option_symbol'],
        signal_type=signal_data['signal_type'],
        spot_price=signal_data['spot_price'],
        strike=signal_data.get('strike', 0), # Some signals might not have strike cleanly mapped yet
        reason=signal_data['reason'],
        recommendation=signal_data.get('recommendation', ''),
        risk_level=signal_data['risk_level']
    )
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal

def get_recent_signals(db: Session, limit: int = 50):
    return db.query(SignalModel).order_by(SignalModel.timestamp.desc()).limit(limit).all()
