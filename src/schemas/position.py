from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PositionBase(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    order_type: str

class PositionCreate(PositionBase):
    pass

class Position(PositionBase):
    id: int
    entry_price: float
    current_price: Optional[float]
    open_time: datetime
    close_time: Optional[datetime]
    status: str
    cumulative_leverage: float
    cumulative_stop_loss: float
    cumulative_take_profit: float
    cumulative_order_type: str
    operation_type: str
    close_price: Optional[float]
    profit_loss: Optional[float]

    class Config:
        orm_mode = True

class TradeResponse(BaseModel):
    message: str

class ProfitLossRequest(BaseModel):
    trader_id: int
    trade_pair: str
    asset_type: str
