"""Database models (SQLAlchemy 2.0 typed style). No protected attributes anywhere."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base

ROLES = ("CUSTOMER", "OFFICER", "ANALYST")
SEGMENTS = ("SALARIED", "SELF_EMPLOYED", "STUDENT")
LOAN_TYPES = ("PERSONAL", "HOME", "VEHICLE", "EDUCATION")
APP_STATUSES = ("DRAFT", "SUBMITTED", "UNDER_VERIFICATION", "UNDER_REVIEW", "APPROVED", "REJECTED", "DISBURSED")
DOC_TYPES = ("IDENTITY", "ADDRESS", "INCOME")
DOC_LABELS = {"IDENTITY": "Identity proof", "ADDRESS": "Address proof", "INCOME": "Income proof"}
RUN_STATUSES = ("RUNNING", "COMPLETED", "FAILED")
DECISIONS = ("APPROVE", "REJECT", "REQUEST_DOCUMENTS")
POLICY_LOAN_TYPES = LOAN_TYPES + ("ALL",)
POLICY_SEGMENTS = ("ALL",) + SEGMENTS
AUDIENCES = ("CUSTOMER", "INTERNAL")
AUDIT_STATUSES = ("SUCCESS", "DENIED", "BLOCKED", "ERROR")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def check_in(column: str, values: tuple, name: str) -> CheckConstraint:
    """CHECK (column IN ('A','B',...))."""
    allowed = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=name)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        check_in("role", ROLES, "ck_users_role"),
        check_in("segment", SEGMENTS, "ck_users_segment"),
        CheckConstraint("monthly_income >= 0", name="ck_users_income"),
        CheckConstraint("existing_emi >= 0", name="ck_users_existing_emi"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    segment: Mapped[Optional[str]] = mapped_column(String(20))
    monthly_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    existing_emi: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    pan_masked: Mapped[Optional[str]] = mapped_column(String(10))
    created_at: Mapped[datetime] = created_at_col()


class LoanProduct(Base):
    __tablename__ = "loan_products"
    __table_args__ = (
        check_in("loan_type", LOAN_TYPES, "ck_products_loan_type"),
        CheckConstraint("rate_min <= rate_max", name="ck_products_rate"),
        CheckConstraint("tenure_min <= tenure_max", name="ck_products_tenure"),
        CheckConstraint("amount_min <= amount_max", name="ck_products_amount"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. VL-204
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rate_min: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    rate_max: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    tenure_min: Mapped[int] = mapped_column(Integer, nullable=False)
    tenure_max: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_min: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_max: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    processing_fee_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    eligible_segments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [] = all segments
    min_credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        check_in("status", APP_STATUSES, "ck_applications_status"),
        CheckConstraint("amount > 0", name="ck_applications_amount"),
        CheckConstraint("tenure_months > 0", name="ck_applications_tenure"),
        CheckConstraint("declared_income > 0", name="ck_applications_income"),
        Index("ix_applications_user_id", "user_id"),
        Index("ix_applications_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("loan_products.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    declared_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # optimistic locking
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship()
    product: Mapped["LoanProduct"] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="application")

    @property
    def code(self) -> str:
        """Customer-facing ID, e.g. LA-2026-00001."""
        return f"LA-2026-{self.id:05d}"


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = created_at_col()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (check_in("doc_type", DOC_TYPES, "ck_documents_doc_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="documents")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (check_in("status", RUN_STATUSES, "ck_agent_runs_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    recommendation: Mapped[Optional[str]] = mapped_column(String(40))
    risk_band: Mapped[Optional[str]] = mapped_column(String(10))
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    result_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(60), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_calls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = created_at_col()


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (check_in("decision", DECISIONS, "ck_decisions_decision"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    analyst_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_col()


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    __table_args__ = (
        check_in("loan_type", POLICY_LOAN_TYPES, "ck_policy_chunks_loan_type"),
        check_in("customer_segment", POLICY_SEGMENTS, "ck_policy_chunks_segment"),
        check_in("audience", AUDIENCES, "ck_policy_chunks_audience"),
        Index("ix_policy_chunks_loan_type_audience", "loan_type", "audience"),
        Index("ix_policy_chunks_doc_key", "doc_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_key: Mapped[str] = mapped_column(String(100), nullable=False)
    doc_title: Mapped[str] = mapped_column(String(200), nullable=False)
    section: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    loan_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_segment: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")
    audience: Mapped[str] = mapped_column(String(20), nullable=False, default="CUSTOMER")
    embedding = mapped_column(Vector(settings.EMBED_DIM), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (check_in("status", AUDIT_STATUSES, "ck_audit_logs_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    actor: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. user:3, agent:CreditAssessmentAgent
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity: Mapped[Optional[str]] = mapped_column(String(80))  # e.g. application:12
    input_masked: Mapped[Optional[dict]] = mapped_column(JSONB)
    output: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
