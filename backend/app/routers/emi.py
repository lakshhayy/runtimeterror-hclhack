"""EMI routes."""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.emi import EmiIn, EmiOut, WhatIfIn, WhatIfOut
from app.services.emi import amortization_schedule, calculate_emi, what_if_options

router = APIRouter(prefix="/emi", tags=["emi"])


@router.post("/calculate", response_model=EmiOut)
def calculate(body: EmiIn, user=Depends(get_current_user)):
    """EMI, totals and the full repayment schedule."""
    schedule = amortization_schedule(body.principal, body.annual_rate, body.tenure_months)
    total_payment = sum(row["emi"] for row in schedule)
    return {
        "emi": calculate_emi(body.principal, body.annual_rate, body.tenure_months),
        "total_interest": total_payment - body.principal,
        "total_payment": total_payment,
        "schedule": schedule,
    }


@router.post("/what-if", response_model=WhatIfOut)
def what_if(body: WhatIfIn, user=Depends(get_current_user)):
    """Current FOIR/eligibility plus tenure or amount suggestions."""
    return what_if_options(
        body.principal, body.annual_rate, body.tenure_months, body.monthly_income, body.existing_emi,
        tenure_min=body.tenure_min, tenure_max=body.tenure_max,
    )
