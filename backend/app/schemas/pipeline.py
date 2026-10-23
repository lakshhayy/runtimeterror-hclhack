"""Agent pipeline result schemas (also stored in agent_runs.result_json)."""
from typing import Optional

from app.schemas.applications import ApplicationOut
from app.schemas.common import BaseSchema


class CheckOut(BaseSchema):
    agent: str
    result: str
    detail: str


class PipelineResult(BaseSchema):
    application_id: str
    recommendation: str
    risk_band: str
    checks: list[CheckOut]
    missing_documents: list[str]
    customer_message: str
    requires_human_approval: bool
    audit_trail_id: str


class SubmitOut(BaseSchema):
    application: ApplicationOut
    pipeline: Optional[PipelineResult] = None
