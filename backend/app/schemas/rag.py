"""Policy assistant (RAG) schemas."""
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class RagAskIn(BaseSchema):
    question: str = Field(min_length=3, max_length=500)
    loan_type: Optional[Literal["PERSONAL", "HOME", "VEHICLE", "EDUCATION"]] = None


class RagSource(BaseSchema):
    document: str
    section: str
    version: str
    effective_date: str


class RagAnswer(BaseSchema):
    answer: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    sources: list[RagSource]
    follow_up_required: bool


class LlmRagReply(BaseSchema):
    """What the LLM must return for a grounded answer."""
    found: bool
    answer: str
    used_sources: list[int] = []
