"""Audit trail: every important action writes one masked row to audit_logs."""
from datetime import date, datetime
from decimal import Decimal

from app.core.errors import request_id_var
from app.core.pii import mask_pii_in
from app.models import AuditLog


def to_json_safe(obj):
    """Decimal -> float, date/datetime -> isoformat, recursively; other unknowns -> str."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(v) for v in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def log_audit(db, action, status="SUCCESS", user_id=None, actor=None, entity=None,
              input=None, output=None, commit=False) -> AuditLog:
    """Add an audit row (input/output masked). Commits only when commit=True."""
    entry = AuditLog(
        request_id=request_id_var.get(),
        user_id=user_id,
        actor=actor or (f"user:{user_id}" if user_id else "system"),
        action=action,
        entity=entity,
        input_masked=to_json_safe(mask_pii_in(input)) if input is not None else None,
        output=to_json_safe(mask_pii_in(output)) if output is not None else None,
        status=status,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
