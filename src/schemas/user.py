from datetime import datetime
from typing import Dict

from pydantic import BaseModel


class UsersBase(BaseModel):
    trader_id: int
    current_challenge_level: str
    hot_key: Dict


class UsersSchema(UsersBase):
    id: int
    created_at: datetime
    updated_at: datetime
