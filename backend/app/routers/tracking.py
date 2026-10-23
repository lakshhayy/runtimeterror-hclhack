"""Tracking routes: application detail and re-running checks."""
from fastapi import APIRouter, Depends

from app.core.access import get_application_or_404
from app.core.errors import AppError
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.schemas.pipeline import PipelineResult
from app.schemas.tracking import ApplicationDetail
from app.services.tracking import build_application_detail

router = APIRouter(prefix="/applications", tags=["tracking"])


@router.get("/{app_id}", response_model=ApplicationDetail)
def application_detail(app_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    """Status, timeline, checks and next step (owner or staff)."""
    return build_application_detail(db, get_application_or_404(db, app_id, user))


@router.post("/{app_id}/recheck", response_model=PipelineResult)
def recheck(app_id: int, db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    """Customer re-runs the checks after uploading requested documents."""
    app = get_application_or_404(db, app_id, user)
    if app.user_id != user.id:
        raise AppError(404, "NOT_FOUND", "Application not found")
    if app.status != "UNDER_VERIFICATION":
        raise AppError(409, "RECHECK_NOT_ALLOWED", "Checks can only be re-run while documents are being verified")
    from app.agents.graph import run_pipeline

    return run_pipeline(db, app.id)
