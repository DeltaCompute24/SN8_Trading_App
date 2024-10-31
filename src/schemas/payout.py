from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, field_validator
from pydantic.alias_generators import to_camel
from src.models.payout import Payout


class PayoutFormType(str, Enum):
    CRYPTO = "crypto"
    WIRE = "wire"


class PayoutSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  
        alias_generator=to_camel,
        populate_by_name=True,
        orm_model=Payout
    )

    # Define all fields that match your Payout model
    type: PayoutFormType
    user_id: str
    
    # Wire transfer fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    bank_country: Optional[str] = None
    bic_swift_code: Optional[str] = None

    # Crypto fields
    usdt_address: Optional[str] = None
    tao_address: Optional[str] = None

    @field_validator('type')
    def validate_type(cls, v):
        if v not in PayoutFormType.__members__.values():
            raise ValueError('Invalid payout type')
        return v

    @model_validator(mode='after')
    def validate_based_on_type(cls, values):
        if 'type' not in values:
            return values

        payout_type = values.get('type')

        crypto_fields = {'usdt_address', 'tao_address'}
        wire_fields = {
            'first_name', 'last_name', 'address', 'iban',
            'bank_name', 'bank_address', 'bank_country', 'bic_swift_code'
        }

        if payout_type == PayoutFormType.CRYPTO:
            if not any(values.get(field) for field in crypto_fields):
                raise ValueError("For crypto payout, either 'tao_address' or 'usdt_address' must be provided")
        elif payout_type == PayoutFormType.WIRE:
            for field in wire_fields:
                if not values.get(field):
                    raise ValueError(f"For wire payout, '{field}' cannot be null")

        return values

