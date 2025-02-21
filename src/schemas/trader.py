from pydantic import BaseModel
from typing import Optional, List

class TraderBase(BaseModel):
    hot_key: str
    name: str = None
    email: str = None
    username: str = None
    rank: str
    trader_pairs: str
    sortino_ratio: str
    omega_ratio: str
    sharpe_ratio: str
    all_time_returns: str

class TraderCreate(TraderBase):
    pass

class TraderUpdate(TraderBase):
    pass

class TraderRead(TraderBase):
    class Config:
        orm_mode = True