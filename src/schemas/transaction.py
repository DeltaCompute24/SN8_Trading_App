from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    initial_price: Optional[float]
    entry_price: float
    operation_type: str
    cumulative_leverage: float
    cumulative_stop_loss: Optional[float]
    cumulative_take_profit: Optional[float]
    average_entry_price: Optional[float]
    cumulative_order_type: str
    status: str
    old_status: Optional[str]
    close_time: Optional[datetime]
    close_price: Optional[float]
    profit_loss: Optional[float]
    position_id: int
    trade_order: int
    modified_by: Optional[str]
    upward: Optional[float]
    challenge_level: Optional[str]
    fees: Optional[float]
    entry_price_list: Optional[list]
    leverage_list: Optional[list]
    order_type_list: Optional[list]

    class Config:
        orm_mode = True


class TradeResponse(BaseModel):
    message: str


class ProfitLossRequest(BaseModel):
    trader_id: int
    trade_pair: str
    asset_type: str
