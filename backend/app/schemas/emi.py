"""EMI calculator and what-if schemas."""
from decimal import Decimal
from typing import Optional

from pydantic import Field, field_validator, model_validator

from app.schemas.common import BaseSchema, to_rupees


class EmiIn(BaseSchema):
    principal: Decimal = Field(ge=10000, le=100000000)
    annual_rate: Decimal = Field(ge=0, le=36)
    tenure_months: int = Field(ge=1, le=480)


class WhatIfIn(EmiIn):
    monthly_income: Decimal = Field(gt=0, le=100000000)
    existing_emi: Decimal = Field(default=Decimal("0"), ge=0, le=100000000)
    tenure_min: int = Field(default=12, ge=1, le=480)
    tenure_max: int = Field(default=360, ge=1, le=480)

    @model_validator(mode="after")
    def _check_tenure_range(self):
        if self.tenure_min > self.tenure_max:
            raise ValueError("tenureMin must not be greater than tenureMax")
        return self


class ScheduleRow(BaseSchema):
    month: int
    emi: float
    interest: float
    principal: float
    balance: float

    @field_validator("emi", "interest", "principal", "balance", mode="before")
    @classmethod
    def _two_decimals(cls, v):
        return round(float(v), 2)


class EmiOut(BaseSchema):
    emi: int
    total_interest: int
    total_payment: int
    schedule: list[ScheduleRow]

    @field_validator("emi", "total_interest", "total_payment", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)


class Snapshot(BaseSchema):
    emi: int
    foir: float
    eligibility: str

    @field_validator("emi", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)

    @field_validator("foir", mode="before")
    @classmethod
    def _to_float(cls, v):
        return float(v)


class WhatIfOption(Snapshot):
    type: str
    tenure_months: int
    principal: int
    label: str
    interest_saved: Optional[int] = None

    @field_validator("principal", "interest_saved", mode="before")
    @classmethod
    def _rupees(cls, v):
        return to_rupees(v)


class WhatIfOut(BaseSchema):
    current: Snapshot
    options: list[WhatIfOption]
