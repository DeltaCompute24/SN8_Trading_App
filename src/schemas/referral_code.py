from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.models.referral_code import ReferralCode
class ReferralCodeBase(BaseModel):
    id: int
    code: str = Field(..., min_length=7, max_length=7)
    discount_percentage: int = Field(..., ge=0, le=100)
    user_id: Optional[str] = None
    valid_from: date
    valid_to: date

class ReferralCodeCreate(ReferralCodeBase):
 
    @field_validator('valid_from')
    def validate_valid_from(cls, v):
      if v < date.today():
        raise ValueError('Valid-from date cannot be in the past')
      
      if v > cls.valid_to :
        raise ValueError('Valid-from date cannot be after valid to date')

    @field_validator('valid_to')
    def validate_valid_to(cls, v):
      if v < date.today():
        raise ValueError('Valid-to date cannot be in the past')
      
class ReferralCodeResponse(ReferralCodeBase):

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        orm_model=ReferralCode,
        json_encoders = {
            date: lambda v: v.isoformat()
        }
    )
