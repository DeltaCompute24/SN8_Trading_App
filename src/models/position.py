from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from src.models.base import Base

class Position(Base):
    __tablename__ = "position"
    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(Integer, index=True)
    trade_pair = Column(String, index=True)
    leverage = Column(Float)
    entry_price = Column(Float)
    asset_type = Column(String)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    open_time = Column(DateTime, default=datetime.utcnow)
    close_time = Column(DateTime, nullable=True)
    status = Column(String, default="OPEN")
    order_type = Column(String)

    cumulative_leverage = Column(Float, default=0.0)
    cumulative_stop_loss = Column(Float, default=0.0)
    cumulative_take_profit = Column(Float, default=0.0)
    cumulative_order_type = Column(String, default="")
    operation_type = Column(String, default="initiate")