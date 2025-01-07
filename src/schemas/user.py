from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, List , Dict
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UsersBase(BaseModel):
    trader_id: int = 0
    hot_key: str = ""


class UsersSchema(UsersBase):
    id: int
    created_at: datetime
    updated_at: datetime


class FirebaseUserBase(BaseModel):
    firebase_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    username: Optional[str] = None
    favorite_trade_pairs: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    )

# --------------- FirebaseUser Schemas ----------------------
class FavoriteTradePairs(BaseModel):
    email: str
    trade_pair :str
   



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


class TournamentBase(BaseModel):
    id: int
    name: str
    cost: float
    prize: float
    active: bool = True
    start_time: datetime
    end_time: datetime
    
    class Config:
        orm_mode = True
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
    challenge_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    tournament : Optional[TournamentBase] = None

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


# --------------------------- GENERATE PDF SCHEMA ---------------------------

class GeneratePdfSchema(BaseModel):
    firebase_id: str
    step: int
    phase: int
    hot_key: str


# --------------------------- USER BALANCE SCHEMA ---------------------------

class CreateUserBalanceSchema(BaseModel):
    trader_id: int
    hot_key: str
    balance: Decimal
    balance_as_on: datetime


class UserBalanceSchema(CreateUserBalanceSchema):
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
