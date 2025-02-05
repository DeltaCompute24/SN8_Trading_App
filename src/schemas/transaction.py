from datetime import datetime
from typing import Optional
from src.models.transaction import Status
from pydantic import BaseModel, model_validator


class TransactionBase(BaseModel):
    trader_id: int
    trade_pair: str
    leverage: float
    asset_type: str
    trailing: Optional[bool] = False
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_price: Optional[float] = 0.0 #in Dollars, used as a fixed point
    limit_order: Optional[float] = 0.0 #In percentage, used for trailing
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

class TransactionUpdateDatabase(BaseModel):
    operation_type : str
    order_type : str 
    cumulative_leverage : float
    cumulative_stop_loss : float
    cumulative_take_profit : float
    stop_loss : float
    take_profit : float
    status : Status
    old_status : Status
    leverage : float
    
    
class TransactionUpdateDatabaseGen(BaseModel):
    
    trader_id: Optional[int] = None
    trade_pair: Optional[str] = None
    leverage: Optional[float] = None
    asset_type: Optional[str] = None
    trailing: Optional[bool] = False
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    limit_order: Optional[float] = 0.0 #In percentage, used for trailing
    order_type: Optional[str] = None
    order_id: Optional[int] = None
    open_time: Optional[datetime] = None
    initial_price: Optional[float] = None
    entry_price: Optional[float] = None
    operation_type: Optional[str] = None
    cumulative_leverage: Optional[float] = None
    cumulative_stop_loss: Optional[float] = None
    cumulative_take_profit: Optional[float] = None
    average_entry_price: Optional[float] = None
    cumulative_order_type: Optional[str] = None
    status: Optional[str] = None
    old_status: Optional[str] = None
    adjust_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_without_fee: Optional[float] = None
    max_profit_loss: Optional[float] = None
    fee: Optional[float] = None
    position_id: Optional[int] = None
    trade_order: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    uuid: Optional[str] = None
    hot_key: Optional[str] = None
    modified_by: Optional[str] = None
    upward: Optional[float] = None
    source: Optional[str] = None


class Transaction(TransactionBase):
    order_id: int
    open_time: datetime
    initial_price: Optional[float]
    entry_price: Optional[float]
    operation_type: str
    cumulative_leverage: float
    cumulative_stop_loss: Optional[float]
    cumulative_take_profit: Optional[float]
    average_entry_price: Optional[float]
    cumulative_order_type: str
    status: str
    old_status: Optional[str]
    adjust_time: Optional[datetime]
    close_time: Optional[datetime]
    close_price: Optional[float]
    profit_loss: Optional[float]
    profit_loss_without_fee: Optional[float] = None
    max_profit_loss: Optional[float] = None
    fee: Optional[float] = None
    position_id: int
    trade_order: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    uuid: Optional[str]
    hot_key: Optional[str]
    modified_by: Optional[str]
    upward: Optional[float]
    source: Optional[str]

    class Config:
        orm_mode = True

    @model_validator(mode="before")
    @classmethod
    def replace_zero_with_null(cls, values):
        keys_to_check = [
            'entry_price', 'initial_price', 'close_price', 'profit_loss',
            'profit_loss_without_fee', 'max_profit_loss',
            'fee', 'min_price', 'max_price'
        ]
        for key in keys_to_check:
            if hasattr(values, key) and getattr(values, key) == 0:
                setattr(values, key, None)
        return values


class TradeResponse(BaseModel):
    message: str


class ProfitLossRequest(BaseModel):
    trader_id: int
    trade_pair: str
    asset_type: str
