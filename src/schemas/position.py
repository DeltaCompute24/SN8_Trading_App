from pydantic import BaseModel
from datetime import datetime

class PositionBase(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    stop_loss: float
    take_profit: float
    order_type: str

class PositionCreate(PositionBase):
    pass

class Position(PositionBase):
    id: int
    entry_price: float = None
    current_price: float = None
    open_time: datetime
    close_time: datetime = None
    status: str

    cumulative_leverage: float
    cumulative_stop_loss: float
    cumulative_take_profit: float
    cumulative_order_type: str

    class Config:
        orm_mode = True

class TradeResponse(BaseModel):
    message: str
