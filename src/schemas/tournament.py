from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.schemas.user import ChallengeIdRead, ChallengeRead


class TournamentBase(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime


class TournamentCreate(TournamentBase):
    name: str
    start_time: datetime
    end_time: datetime


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class TournamentRead(BaseModel):
    id: int
    name: str
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime

    challenge: Optional[ChallengeRead] = None

    class Config:
        orm_mode = True
