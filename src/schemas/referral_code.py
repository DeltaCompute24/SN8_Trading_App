from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from src.models.referral_code import ReferralCode
from src.schemas.user import FirebaseUserBase



class ReferralCodeValidate(BaseModel):
    code: str
    user_id: str

class ReferralCodeBase(BaseModel):
    code: Optional[str] = Field(None, min_length=7, max_length=30)
    discount_percentage: int = Field(..., ge=0, le=100)
    valid_from: date
    valid_to: date
    multiple_use: bool = Field(default=False)
   


class ReferralCodeCreate(ReferralCodeBase):
    auto_generate: bool = Field(default=False)
    generated_by_id: Optional[str]
    
    @field_validator('valid_from')  
    def validate_valid_from(cls, v):  
        if v < date.today():
            raise ValueError('Valid-from date cannot be in the past')
        return v

    @field_validator('valid_to')
    def validate_valid_to(cls, v):
        if v < date.today():
            raise ValueError('Valid-to date cannot be in the past')
        return v

    @model_validator(mode='after')
    def validate_valid_dates(cls, v):
        if v.valid_from > v.valid_to:
            raise ValueError('Valid-to date cannot be before valid-from date')
        return v
    
class ReferralCodeResponse(ReferralCodeBase):
    id: Optional[int] = None
    generated_by_id: Optional[str] = None
    is_valid: Optional[bool] = True

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        orm_model=ReferralCode,
        json_encoders = {
            date: lambda v: v.isoformat()
        }
    )

class ReferralCodeListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codes: List[ReferralCodeResponse] = Field(default_factory=list)
    users: Optional[List[FirebaseUserBase]] = Field(default_factory=list)
