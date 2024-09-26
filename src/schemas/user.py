from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UsersBase(BaseModel):
    trader_id: int = 0
    hot_key: str = ""


class UsersSchema(UsersBase):
    id: int
    created_at: datetime
    updated_at: datetime


# --------------- FirebaseUser Schemas ----------------------
class FirebaseUserBase(BaseModel):
    firebase_id: str = ""


class ChallengeBase(BaseModel):
    trader_id: int = 0
    hot_key: str = ""
    active: str = ""
    status: Optional[str] = ""
    challenge: str = ""


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
