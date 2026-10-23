"""Application status state machine. All status changes go through set_status."""
from sqlalchemy import update

from app.core.audit import log_audit
from app.core.errors import AppError
from app.models import Application, StatusHistory, utcnow

# (from, to) -> roles allowed to make that move. Agents can never set APPROVED or REJECTED.
TRANSITIONS = {
    ("DRAFT", "SUBMITTED"): {"CUSTOMER"},
    ("SUBMITTED", "UNDER_VERIFICATION"): {"AGENT"},
    ("UNDER_VERIFICATION", "UNDER_REVIEW"): {"AGENT"},
    ("UNDER_REVIEW", "APPROVED"): {"ANALYST"},
    ("UNDER_REVIEW", "REJECTED"): {"ANALYST"},
    ("UNDER_REVIEW", "UNDER_VERIFICATION"): {"ANALYST"},  # request more documents
    ("APPROVED", "DISBURSED"): {"OFFICER"},
}


def is_transition_allowed(from_status: str, to_status: str, actor_role: str) -> bool:
    """True if actor_role may move an application from from_status to to_status."""
    return actor_role in TRANSITIONS.get((from_status, to_status), set())


def _actor(actor_role: str, actor_user_id) -> str:
    return f"user:{actor_user_id}" if actor_user_id else f"role:{actor_role}"


def set_status(db, app_id: int, new_status: str, actor_role: str, actor_user_id=None,
               note: str = "", expected_version=None) -> Application:
    """Validate the move, apply it with an atomic version check, record history + audit, commit once."""
    app = db.get(Application, app_id)
    if app is None:
        raise AppError(404, "NOT_FOUND", "Application not found")

    current = app.status
    entity = f"application:{app_id}"
    if not is_transition_allowed(current, new_status, actor_role):
        log_audit(db, action="STATUS_CHANGE_DENIED", status="DENIED", user_id=actor_user_id,
                  actor=_actor(actor_role, actor_user_id), entity=entity,
                  input={"from": current, "to": new_status, "actorRole": actor_role}, commit=True)
        raise AppError(409, "INVALID_TRANSITION",
                       f"Cannot move application from {current} to {new_status} as {actor_role}")

    version = expected_version if expected_version is not None else app.version
    result = db.execute(
        update(Application)
        .where(Application.id == app_id, Application.status == current, Application.version == version)
        .values(status=new_status, version=Application.version + 1, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        raise AppError(409, "STALE_VERSION", "This application was updated by someone else. Please refresh.")

    db.add(StatusHistory(application_id=app_id, from_status=current, to_status=new_status,
                         actor_role=actor_role, note=note or ""))
    log_audit(db, action="STATUS_CHANGE", user_id=actor_user_id, actor=_actor(actor_role, actor_user_id),
              entity=entity, input={"from": current, "to": new_status, "note": note})
    db.commit()
    db.refresh(app)
    return app
