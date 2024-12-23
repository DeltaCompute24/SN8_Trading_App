from datetime import datetime

from pydantic import BaseModel

from src.schemas.user import ChallengeRead


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


class TournamentRead(TournamentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    challenges: list[ChallengeRead] = []

    class Config:
        orm_mode = True
