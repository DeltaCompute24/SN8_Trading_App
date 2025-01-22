from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RedisPosition(BaseModel):
    price: float = Field(..., description="Current price")
    profit_loss: float = Field(..., description="Profit/Loss value")
    profit_loss_without_fee: float = Field(..., description="Profit/Loss without fees")
    taoshi_profit_loss: float = Field(..., description="Taoshi Profit/Loss value")
    taoshi_profit_loss_without_fee: float = Field(..., description="Taoshi Profit/Loss without fees")
    uuid: str = Field(..., description="Position UUID")
    hot_key: str = Field(..., description="Hot key identifier")
    len_order: int = Field(..., description="Order length")
    average_entry_price: float = Field(..., description="Average entry price")
    closed: bool = Field(..., description="Position closed status")

    @classmethod
    def from_redis_array(cls, data: list):
        """
        Convert Redis array data to RedisPosition object
        Example input: ["2025-01-17 23:42:36.610644", 1.1099, -0.013864683755286933, ...]
        """
        return cls(
            price=data[0],
            profit_loss=data[1],
            profit_loss_without_fee=data[2],
            taoshi_profit_loss=data[3],
            taoshi_profit_loss_without_fee=data[4],
            uuid=data[5],
            hot_key=data[6],
            len_order=data[7],
            average_entry_price=data[8],
            closed=data[9]
        )
