"""Analyst and officer routes (/analyst/... and /officer/...)."""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.security import require_role
from app.core.status import set_status
from app.database import get_db
from app.models import AgentRun, Application, Decision
from app.schemas.analyst import AnalystDetail, CustomerOut, DecisionIn, QueueItem
from app.schemas.applications import ApplicationOut
from app.services.emi import calculate_emi
from app.services.tracking import build_application_detail

router = APIRouter(tags=["analyst"])

DECISION_TO_STATUS = {"APPROVE": "APPROVED", "REJECT": "REJECTED", "REQUEST_DOCUMENTS": "UNDER_VERIFICATION"}
RISK_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
HIGH_VALUE_AMOUNT = Decimal("1000000")


def _latest_runs(db, app_ids: list[int]) -> dict[int, AgentRun]:
    """Latest COMPLETED run per application."""
    runs = {}
    if not app_ids:
        return runs
    for run in db.scalars(select(AgentRun).where(AgentRun.application_id.in_(app_ids), AgentRun.status == "COMPLETED")
                          .order_by(AgentRun.created_at, AgentRun.id)):
        runs[run.application_id] = run
    return runs


def _priority(app: Application, run: AgentRun | None) -> bool:
    """Priority = amount > ₹10L, or risk not LOW, or any check not PASS."""
    if run is None or not run.result_json:
        return app.amount > HIGH_VALUE_AMOUNT
    checks = run.result_json.get("checks", [])
    return app.amount > HIGH_VALUE_AMOUNT or run.risk_band != "LOW" or any(c["result"] != "PASS" for c in checks)


def _queue_item(app: Application, run: AgentRun | None) -> QueueItem:
    return QueueItem(
        id=app.id, application_id=app.code, customer_name=app.user.full_name, product_name=app.product.name,
        amount=app.amount, tenure_months=app.tenure_months, status=app.status,
        risk_band=run.risk_band if run else None, recommendation=run.recommendation if run else None,
        priority=_priority(app, run), created_at=app.created_at,
    )


@router.get("/analyst/queue", response_model=list[QueueItem])
def review_queue(db=Depends(get_db), user=Depends(require_role("ANALYST"))):
    """Applications waiting for a human decision: priority first, then HIGH > MEDIUM > LOW risk, then oldest."""
    apps = list(db.scalars(select(Application).where(Application.status == "UNDER_REVIEW")))
    runs = _latest_runs(db, [a.id for a in apps])
    items = [_queue_item(a, runs.get(a.id)) for a in apps]
    items.sort(key=lambda i: (not i.priority, RISK_ORDER.get(i.risk_band, 3), i.created_at, i.id))
    return items


@router.get("/analyst/applications/{app_id}", response_model=AnalystDetail)
def review_detail(app_id: int, db=Depends(get_db), user=Depends(require_role("ANALYST"))):
    app = db.get(Application, app_id)
    if app is None:
        raise AppError(404, "NOT_FOUND", "Application not found")
    detail = build_application_detail(db, app)
    return AnalystDetail(
        **detail.model_dump(),
        customer=CustomerOut.model_validate(app.user),
        indicative_emi=int(calculate_emi(app.amount, app.product.rate_min, app.tenure_months)),
    )


@router.post("/analyst/decision/{app_id}", response_model=ApplicationOut)
def decide(app_id: int, body: DecisionIn, db=Depends(get_db), user=Depends(require_role("ANALYST"))):
    """Human decision. The version check means a stale screen gets 409 instead of overwriting someone else."""
    app = set_status(db, app_id, DECISION_TO_STATUS[body.decision], actor_role="ANALYST", actor_user_id=user.id,
                     note=body.comment.strip(), expected_version=body.version)
    db.add(Decision(application_id=app.id, analyst_id=user.id, decision=body.decision, comment=body.comment.strip()))
    log_audit(db, action="DECISION", user_id=user.id, entity=f"application:{app.id}",
              input={"decision": body.decision, "comment": body.comment.strip(), "version": body.version},
              output={"status": app.status})
    db.commit()
    db.refresh(app)
    return ApplicationOut.from_app(app)


@router.get("/officer/applications", response_model=list[QueueItem])
def all_applications(db=Depends(get_db), user=Depends(require_role("OFFICER", "ANALYST"))):
    """Every application, newest first (read-only view)."""
    apps = list(db.scalars(select(Application).order_by(Application.created_at.desc(), Application.id.desc())))
    runs = _latest_runs(db, [a.id for a in apps])
    return [_queue_item(a, runs.get(a.id)) for a in apps]
