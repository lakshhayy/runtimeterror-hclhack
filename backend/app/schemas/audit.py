"""Audit log schemas."""
from datetime import datetime
from typing import Any, Optional

from app.schemas.common import BaseSchema


class AuditEntry(BaseSchema):
    id: int
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    actor: str
    action: str
    entity: Optional[str] = None
    input_masked: Optional[Any] = None
    output: Optional[Any] = None
    status: str
    created_at: datetime


class GuardrailResult(BaseSchema):
    test: str
    blocked: bool
    message: str


class GuardrailTestOut(BaseSchema):
    results: list[GuardrailResult]
