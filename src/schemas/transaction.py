from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionBase(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    trailing: Optional[bool] = False
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_price: Optional[float] = 0.0
    limit_order: Optional[float] = 0.0
    order_type: str


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    trailing: Optional[bool] = False  # trailing stop loss default value will be false if user didn't submit
    stop_loss: Optional[float]
    take_profit: Optional[float]


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
    profit_loss_without_fee: Optional[float] or 0.0
    max_profit_loss: Optional[float] or 0.0
    fee: Optional[float] or 0.0
    position_id: int
    trade_order: int
    min_price: Optional[float] = 0.0
    max_price: Optional[float] = 0.0
    uuid: Optional[str]
    hot_key: Optional[str]
    modified_by: Optional[str]
    upward: Optional[float]
    source: Optional[str]

    class Config:
        orm_mode = True


class TradeResponse(BaseModel):
    message: str


class ProfitLossRequest(BaseModel):
    trader_id: int
    trade_pair: str
    asset_type: str
