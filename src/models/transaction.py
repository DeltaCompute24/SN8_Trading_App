from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime

from src.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trader_id = Column(Integer, nullable=False)
    trade_pair = Column(String, nullable=False)
    open_time = Column(DateTime, default=datetime.utcnow)
    entry_price = Column(Float, nullable=False)
    upward = Column(Float, default=-1, nullable=True)
    leverage = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    order_type = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)
    cumulative_leverage = Column(Float, nullable=False)
    cumulative_stop_loss = Column(Float, nullable=True)
    cumulative_take_profit = Column(Float, nullable=True)
    cumulative_order_type = Column(String, nullable=False)
    status = Column(String, default="OPEN", nullable=False)
    close_time = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    position_id = Column(Integer, nullable=False)
    trade_order = Column(Integer, nullable=False)
    modified_by = Column(String, default="", nullable=True)
