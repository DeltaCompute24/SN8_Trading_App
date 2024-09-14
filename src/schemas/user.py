from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class UsersBase(BaseModel):
    trader_id: int
    current_challenge_level: str
    hot_key: Dict


class UsersSchema(UsersBase):
    id: int
    created_at: datetime
    updated_at: datetime


# --------------- FirebaseUser Schemas ----------------------
class FirebaseUserBase(BaseModel):
    firebase_id: str


class ChallengeBase(BaseModel):
    trader_id: int
    hot_key: str
    status: str
    challenge: str


class ChallengeRead(ChallengeBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class FirebaseUserCreate(FirebaseUserBase):
    challenges: Optional[list[ChallengeBase]] = []


class FirebaseUserUpdate(FirebaseUserBase):
    firebase_id: Optional[str] = ""
    challenges: Optional[list[ChallengeBase]] = []


class FirebaseUserRead(FirebaseUserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    challenges: list[ChallengeRead] = []

    class Config:
        orm_mode = True
