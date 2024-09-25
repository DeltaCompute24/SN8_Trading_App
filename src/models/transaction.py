from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON

from src.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trader_id = Column(Integer, nullable=False)
    trade_pair = Column(String, nullable=False)
    open_time = Column(DateTime, default=datetime.utcnow)
    initial_price = Column(Float, default=0, nullable=True)
    entry_price = Column(Float, nullable=False)
    upward = Column(Float, default=-1, nullable=True)
    leverage = Column(Float, nullable=False)
    stop_loss = Column(Float, default=0, nullable=True)
    take_profit = Column(Float, default=0, nullable=True)
    order_type = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)
    cumulative_leverage = Column(Float, nullable=False)
    cumulative_stop_loss = Column(Float, nullable=True)
    cumulative_take_profit = Column(Float, nullable=True)
    cumulative_order_type = Column(String, nullable=False)
    average_entry_price = Column(Float, nullable=True)
    status = Column(String, default="OPEN", nullable=False)
    old_status = Column(String, default="OPEN", nullable=True)
    close_time = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    max_profit_loss = Column(Float, nullable=True)
    profit_loss_without_fee = Column(Float, nullable=True)
    taoshi_profit_loss = Column(Float, nullable=True)
    taoshi_profit_loss_without_fee = Column(Float, nullable=True)
    position_id = Column(Integer, nullable=False)
    trade_order = Column(Integer, nullable=False)
    challenge_level = Column(String, nullable=True)
    entry_price_list = Column(JSON, default=[])
    leverage_list = Column(JSON, default=[])
    order_type_list = Column(JSON, default=[])
    modified_by = Column(String, default="", nullable=True)
