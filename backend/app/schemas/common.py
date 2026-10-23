"""Shared schemas. All API JSON is camelCase."""
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


def to_rupees(value):
    """Decimal money -> int rupees, rounded half-up. None stays None."""
    if value is None:
        return None
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class UserOut(BaseSchema):
    id: int
    email: str
    full_name: str
    role: str
    segment: Optional[str] = None
    monthly_income: Optional[int] = None
    existing_emi: int = 0
    pan_masked: Optional[str] = None

    @field_validator("monthly_income", "existing_emi", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)


class LoginIn(BaseSchema):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class LoginOut(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ErrorBody(BaseSchema):
    code: str
    message: str
    request_id: Optional[str] = None


class ErrorOut(BaseSchema):
    error: ErrorBody
