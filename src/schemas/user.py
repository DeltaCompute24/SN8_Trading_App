from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr


class UsersBase(BaseModel):
    trader_id: int = 0
    hot_key: str = ""


class UsersSchema(UsersBase):
    id: int
    created_at: datetime
    updated_at: datetime


# --------------- FirebaseUser Schemas ----------------------
class FirebaseUserBase(BaseModel):
    firebase_id: str


class ChallengeBase(BaseModel):
    trader_id: int = 0
    hot_key: str = ""
    active: str = ""
    status: Optional[str] = ""
    challenge: str = ""
    step: Optional[int] = ""
    phase: Optional[int] = ""


class ChallengeUpdate(BaseModel):
    trader_id: int = 0
    hot_key: str = ""


class ChallengeRead(ChallengeBase):
    id: int
    user_id: int
    message: Optional[str]
    response: Optional[dict]
    hotkey_status: Optional[str]
    draw_down: Optional[float]
    profit_sum: Optional[float]
    register_on_test_net: Optional[datetime]
    register_on_main_net: Optional[datetime]
    pass_the_challenge: Optional[datetime]
    pass_the_main_net_challenge: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ChallengeIdRead(BaseModel):
    id: int

    class Config:
        orm_mode = True


class FirebaseUserCreate(FirebaseUserBase):
    name: str
    email: str


class FirebaseUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class FirebaseUserRead(FirebaseUserBase):
    id: int
    name: Optional[str]
    username: Optional[str]
    email: Optional[str]
    created_at: datetime
    updated_at: datetime
    challenges: list[ChallengeRead] = []

    class Config:
        orm_mode = True


# --------------- Payment Schemas ----------------------
class PaymentBase(BaseModel):
    amount: float
    referral_code: Optional[str] = None
    challenge_id: Optional[int] = None


class PaymentCreate(BaseModel):
    firebase_id: str
    amount: float
    step: Literal[1, 2]
    phase: Literal[1, 2]
    referral_code: Optional[str] = None


class PaymentRead(PaymentBase):
    id: int
    firebase_id: str
    challenge: Optional[ChallengeRead] = None

    class Config:
        orm_mode = True


class PaymentIdRead(PaymentBase):
    id: int
    firebase_id: str
    challenge: Optional[ChallengeIdRead] = None

    class Config:
        orm_mode = True


class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    referral_code: Optional[str] = None
    challenge: Optional[ChallengeRead] = None

    class Config:
        orm_mode = True


# EMAIL SCHEMA
class EmailInput(BaseModel):
    email: EmailStr
    type: str
