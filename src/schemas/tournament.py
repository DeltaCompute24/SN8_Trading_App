from datetime import datetime
from pydantic import BaseModel
from typing import List , Union ,Dict , Optional


class TournamentBase(BaseModel):
    name: str
    cost: float
    prize: float
    active: bool = True
    start_time: datetime
    end_time: datetime


class TournamentCreate(TournamentBase):
    name: str
    start_time: datetime
    end_time: datetime

class TournamentRegister(BaseModel):
    tournament_id: int
    firebase_id: str
    amount: float
    referral_code: str = None,

class TournamentUpdate(BaseModel):
    name: str = None
    cost: float = None
    prize: float = None
    active: bool = None
    start_time: datetime = None
    end_time: datetime = None


class ChallengeRead(BaseModel):
    id: int
    user_id: int
    hotkey_status: Optional[str]
    draw_down: Optional[float]
    profit_sum: Optional[float]
    register_on_test_net: Optional[datetime]
    register_on_main_net: Optional[datetime]
    pass_the_challenge: Optional[datetime]
    pass_the_main_net_challenge: Optional[datetime]
    challenge_name: Optional[str]
    

    class Config:
        orm_mode = True
class TournamentRead(TournamentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    challenges: list[ChallengeRead] = []

    class Config:
        orm_mode = True

class TournamentScore(BaseModel):
   tournament: Union[TournamentRead, Dict] = {}
   statistic: List[dict]
   class Config:
       orm_mode = True
       arbitrary_types_allowed = True  # Allow arbitrary types
  