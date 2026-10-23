"""Advisor routes."""
from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.database import get_db
from app.schemas.advisor import AdvisorIn, AdvisorResponse
from app.services.advisor import advise

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/chat", response_model=AdvisorResponse)
def chat(body: AdvisorIn, db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    """Plain-language loan need -> structured recommendations with indicative EMIs."""
    return advise(db, user, body.message)
