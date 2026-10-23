"""Loan application and document schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.models import DOC_LABELS, Application, Document
from app.schemas.common import BaseSchema, to_rupees


class ApplicationIn(BaseSchema):
    product_id: str = Field(min_length=1, max_length=20)
    amount: Decimal = Field(gt=0, le=1000000000)
    tenure_months: int = Field(gt=0, le=480)
    declared_income: Decimal = Field(gt=0, le=100000000)
    purpose: str = Field(default="", max_length=300)


class ApplicationOut(BaseSchema):
    id: int
    application_id: str
    product_id: str
    product_name: str
    amount: int
    tenure_months: int
    declared_income: int
    purpose: str
    status: str
    version: int
    created_at: datetime

    @field_validator("amount", "declared_income", mode="before")
    @classmethod
    def _money_to_int(cls, v):
        return to_rupees(v)

    @classmethod
    def from_app(cls, app: Application) -> "ApplicationOut":
        return cls(
            id=app.id, application_id=app.code, product_id=app.product_id, product_name=app.product.name,
            amount=app.amount, tenure_months=app.tenure_months, declared_income=app.declared_income,
            purpose=app.purpose, status=app.status, version=app.version, created_at=app.created_at,
        )


class DocumentOut(BaseSchema):
    id: int
    doc_type: str
    doc_label: str
    file_name: str
    uploaded_at: datetime

    @classmethod
    def from_doc(cls, doc: Document) -> "DocumentOut":
        return cls(id=doc.id, doc_type=doc.doc_type, doc_label=DOC_LABELS[doc.doc_type],
                   file_name=doc.file_name, uploaded_at=doc.uploaded_at)
