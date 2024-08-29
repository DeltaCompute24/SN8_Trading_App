from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_price: Optional[float]
    order_type: str

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    order_id: int
    open_time: datetime
    entry_price: float
    operation_type: str
    cumulative_leverage: float
    cumulative_stop_loss: Optional[float]
    cumulative_take_profit: Optional[float]
    cumulative_order_type: str
    status: str
    close_time: Optional[datetime]
    close_price: Optional[float]
    profit_loss: Optional[float]
    position_id: int
    trade_order: int
    modified_by: Optional[str]

    class Config:
        orm_mode = True

class TradeResponse(BaseModel):
    message: str

class ProfitLossRequest(BaseModel):
    trader_id: int
    trade_pair: str
    asset_type: str
