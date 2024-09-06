from sqlalchemy import Column, Integer, String, Float, UniqueConstraint

from src.database import Base


class MonitoredPosition(Base):
    __tablename__ = "monitored_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, nullable=False)
    order_id = Column(Integer, nullable=False)
    trader_id = Column(Integer, nullable=False)
    trade_pair = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)  # Add this line
    cumulative_leverage = Column(Float, nullable=False)
    cumulative_order_type = Column(String, nullable=False)
    cumulative_stop_loss = Column(Float, nullable=True)
    cumulative_take_profit = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint('position_id', 'order_id', name='_position_order_uc'),)
