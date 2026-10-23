"""Application detail schemas."""
from datetime import datetime
from typing import Optional

from app.schemas.applications import ApplicationOut, DocumentOut
from app.schemas.common import BaseSchema
from app.schemas.products import ProductOut


class StepOut(BaseSchema):
    step_order: int
    agent_name: str
    result: str
    detail: str
    tool_calls: list


class TimelineOut(BaseSchema):
    from_status: Optional[str] = None
    to_status: str
    actor_role: str
    note: str
    created_at: datetime


class DecisionOut(BaseSchema):
    decision: str
    comment: str
    created_at: datetime


class ApplicationDetail(BaseSchema):
    application: ApplicationOut
    product: ProductOut
    documents: list[DocumentOut]
    latest_run: Optional[dict] = None  # PipelineResult JSON
    latest_run_status: Optional[str] = None  # RUNNING / COMPLETED / FAILED
    steps: list[StepOut]
    timeline: list[TimelineOut]
    latest_decision: Optional[DecisionOut] = None
    missing_doc_types: list[str]
    next_step: str
