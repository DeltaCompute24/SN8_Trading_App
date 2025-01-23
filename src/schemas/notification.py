from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class NotificationBase(BaseModel):
    type: str
    trader_id: Optional[int] = None
    trader_pair: Optional[str] = None
    message: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id:  Optional[str] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True