"""Shared schemas. All API JSON is camelCase."""
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional

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


class SignupIn(BaseSchema):
    """Customer self-signup. Staff accounts are never created this way."""
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    segment: Literal["SALARIED", "SELF_EMPLOYED", "STUDENT"]
    monthly_income: Decimal = Field(gt=0, le=100000000)
    existing_emi: Decimal = Field(default=Decimal("0"), ge=0, le=100000000)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v.strip()):
            raise ValueError("Please enter a valid email address")
        return v.strip()

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


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
