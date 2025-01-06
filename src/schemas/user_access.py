from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, field_validator, EmailStr
from pydantic.alias_generators import to_camel
from src.models.payout import Payout


class UserAccessSchema(BaseModel):
  
  from_user : EmailStr
  to: EmailStr 
  trader_id: int
  

  class Config:
        from_attributes = True