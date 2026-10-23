"""Analyst review and officer schemas."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, to_rupees
from app.schemas.tracking import ApplicationDetail


class QueueItem(BaseSchema):
    id: int
    application_id: str
    customer_name: str
    product_name: str
    amount: int
    tenure_months: int
    status: str
    risk_band: Optional[str] = None
    recommendation: Optional[str] = None
    priority: bool = False
    created_at: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)


class CustomerOut(BaseSchema):
    full_name: str
    email: str
    segment: Optional[str] = None
    monthly_income: Optional[int] = None
    existing_emi: int = 0
    pan_masked: Optional[str] = None

    @field_validator("monthly_income", "existing_emi", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)


class AnalystDetail(ApplicationDetail):
    customer: CustomerOut
    indicative_emi: int


class DecisionIn(BaseSchema):
    decision: Literal["APPROVE", "REJECT", "REQUEST_DOCUMENTS"]
    comment: str = Field(min_length=5, max_length=500)
    version: int = Field(ge=1)
