"""AI Loan Advisor schemas."""
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import BaseSchema

LoanTypeLiteral = Literal["PERSONAL", "HOME", "VEHICLE", "EDUCATION"]


class AdvisorIn(BaseSchema):
    message: str = Field(min_length=3, max_length=500)


class AdvisorExtract(BaseSchema):
    """What the LLM extracts from the customer's message. It never calculates."""
    loan_type: Optional[LoanTypeLiteral] = None
    purpose: Optional[str] = None
    loan_amount: Optional[int] = Field(default=None, gt=0)
    monthly_income: Optional[int] = Field(default=None, gt=0)
    max_preferred_emi: Optional[int] = Field(default=None, gt=0)


class Recommendation(BaseSchema):
    product_id: str
    product_name: str
    indicative_interest_rate: float
    tenure_months: int
    estimated_emi: int
    reason: str
    eligibility_indicator: Literal["LIKELY_ELIGIBLE", "BORDERLINE", "UNLIKELY"]


class AdvisorResponse(BaseSchema):
    interpreted_requirement: str
    loan_amount: Optional[int] = None
    monthly_income: Optional[int] = None
    max_preferred_emi: Optional[int] = None
    currency: str = "INR"
    recommendations: list[Recommendation] = []
    disclaimer: str = "Indicative only. Final approval is subject to credit assessment."
    clarifying_question: Optional[str] = None
