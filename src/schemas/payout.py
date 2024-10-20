from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class PayoutFormType(str, Enum):
    crypto = "crypto"
    wire = "wire"


class PayoutSchema(BaseModel):
    type: PayoutFormType

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    bank_country: Optional[str] = None
    bic_swift_code: Optional[str] = None

    usdt_address: Optional[str] = None
    tao_address: Optional[str] = None

    # Alias generator allow values travel through the API in camelCase.
    # To disable it just need to remove alias_generator or define it as to_snake.
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    # Override json method to always use aliases (if not set) when dumping the model.
    # This allows API to handle camelCases in request payloads to a better fit with frontend.
    def model_dump_json(self, by_alias: Optional[bool] = None, **kwargs):
        # Ensure `by_alias=True` is always passed to the default `json` method
        if by_alias is None:
            kwargs["by_alias"] = True
        return super().model_dump_json(**kwargs)

    @model_validator(mode="before")
    def validate_based_on_type(cls, values):
        if isinstance(values, dict):
            payout_type = values.get("type")

            crypto_fields = ["taoAddress", "usdtAddress"]
            wire_fields = [
                "firstName",
                "lastName",
                "address",
                "iban",
                "bankName",
                "bankAddress",
                "bankCountry",
                "bicSwiftCode",
            ]

            if payout_type == PayoutFormType.crypto:
                # For `crypto`, either `tao_address` or `usdt_address` must be provided
                has_any_crypto_field = any(values.get(field) for field in crypto_fields)
                if not has_any_crypto_field:
                    raise ValueError(
                        "For crypto payout, either 'taoAddress' or 'usdtAddress' must be provided."
                    )

            elif payout_type == PayoutFormType.wire:
                # For `wire`, `tao_address` and `usdt_address` can be null, but bank fields cannot be null
                for field in wire_fields:
                    if values.get(field) is None:
                        raise ValueError(f"For wire payout, '{field}' cannot be null.")
            else:
                raise ValueError("Unknown payout type.")

        return values


class PayoutSaveSchema(PayoutSchema):
    firebase_id: str
