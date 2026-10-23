"""Loan product schemas."""
from pydantic import field_validator

from app.schemas.common import BaseSchema, to_rupees


class ProductOut(BaseSchema):
    id: str
    name: str
    loan_type: str
    description: str
    rate_min: float
    rate_max: float
    tenure_min: int
    tenure_max: int
    amount_min: int
    amount_max: int
    processing_fee_pct: float
    eligible_segments: list[str]
    min_credit_score: int
    tags: list[str]

    @field_validator("amount_min", "amount_max", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)

    @field_validator("rate_min", "rate_max", "processing_fee_pct", mode="before")
    @classmethod
    def _rate_to_float(cls, v):
        return float(v)
