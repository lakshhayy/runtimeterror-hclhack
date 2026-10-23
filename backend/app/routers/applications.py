"""Applications routes: create, list, upload documents, submit."""
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from app.config import settings
from app.core.access import get_application_or_404
from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.security import get_current_user, require_role
from app.core.status import set_status
from app.database import get_db
from app.models import DOC_TYPES, Application, Document, LoanProduct, StatusHistory
from app.schemas.applications import ApplicationIn, ApplicationOut, DocumentOut
from app.schemas.pipeline import SubmitOut
from app.services.emi import format_inr

router = APIRouter(prefix="/applications", tags=["applications"])

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
UPLOAD_STATUSES = ("DRAFT", "UNDER_VERIFICATION")


def upload_root() -> Path:
    path = Path(settings.UPLOAD_DIR)
    return path if path.is_absolute() else BACKEND_DIR / path


def get_own_application(db, app_id: int, user) -> Application:
    """Owner-only access (staff can view elsewhere, but can't act for the customer)."""
    app = get_application_or_404(db, app_id, user)
    if app.user_id != user.id:
        raise AppError(404, "NOT_FOUND", "Application not found")
    return app


def _validate_against_product(body: ApplicationIn, product: LoanProduct) -> None:
    if not product.amount_min <= body.amount <= product.amount_max:
        raise AppError(400, "AMOUNT_OUT_OF_RANGE",
                       f"Amount must be between {format_inr(product.amount_min)} and "
                       f"{format_inr(product.amount_max)} for this product")
    if not product.tenure_min <= body.tenure_months <= product.tenure_max:
        raise AppError(400, "TENURE_OUT_OF_RANGE",
                       f"Tenure must be between {product.tenure_min} and {product.tenure_max} months for this product")


@router.post("", response_model=ApplicationOut)
def create_application(body: ApplicationIn, db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    """Create a DRAFT application after checking the product's limits."""
    product = db.get(LoanProduct, body.product_id)
    if product is None:
        raise AppError(400, "INVALID_PRODUCT", "Please choose a valid loan product")
    _validate_against_product(body, product)

    app = Application(user_id=user.id, product_id=product.id, amount=body.amount, tenure_months=body.tenure_months,
                      declared_income=body.declared_income, purpose=body.purpose.strip(), status="DRAFT")
    db.add(app)
    db.flush()
    db.add(StatusHistory(application_id=app.id, from_status=None, to_status="DRAFT", actor_role="CUSTOMER",
                         note="Application created"))
    log_audit(db, action="APP_CREATE", user_id=user.id, entity=f"application:{app.id}",
              input=body.model_dump(by_alias=True))
    db.commit()
    db.refresh(app)
    return ApplicationOut.from_app(app)


@router.get("/mine", response_model=list[ApplicationOut])
def my_applications(db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    apps = db.scalars(select(Application).where(Application.user_id == user.id)
                      .order_by(Application.created_at.desc(), Application.id.desc()))
    return [ApplicationOut.from_app(a) for a in apps]


@router.post("/{app_id}/documents", response_model=DocumentOut)
def upload_document(app_id: int, doc_type: str = Form(alias="docType"), file: UploadFile = File(...),
                    db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    """Upload (or replace) one document type. Only while DRAFT or UNDER_VERIFICATION."""
    app = get_own_application(db, app_id, user)
    if doc_type not in DOC_TYPES:
        raise AppError(400, "INVALID_DOC_TYPE", "Document type must be IDENTITY, ADDRESS or INCOME")
    if app.status not in UPLOAD_STATUSES:
        raise AppError(409, "DOCUMENTS_LOCKED", "Documents can't be changed at this stage")

    original = Path(file.filename or "").name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(400, "INVALID_FILE_TYPE", "Only PDF, JPG or PNG files are allowed")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppError(400, "FILE_TOO_LARGE", "File must be 5 MB or smaller")
    if not content:
        raise AppError(400, "EMPTY_FILE", "The file is empty")

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original)[-100:]
    folder = upload_root() / str(app.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}_{safe_name}"
    path.write_bytes(content)

    old = db.scalar(select(Document).where(Document.application_id == app.id, Document.doc_type == doc_type))
    if old is not None:
        Path(old.file_path).unlink(missing_ok=True)
        db.delete(old)
    doc = Document(user_id=user.id, application_id=app.id, doc_type=doc_type, file_name=safe_name,
                   file_path=str(path))
    db.add(doc)
    log_audit(db, action="DOC_UPLOAD", user_id=user.id, entity=f"application:{app.id}",
              input={"docType": doc_type, "fileName": safe_name, "bytes": len(content), "replaced": old is not None})
    db.commit()
    db.refresh(doc)
    return DocumentOut.from_doc(doc)


@router.get("/{app_id}/documents", response_model=list[DocumentOut])
def list_documents(app_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    app = get_application_or_404(db, app_id, user)
    docs = db.scalars(select(Document).where(Document.application_id == app.id).order_by(Document.doc_type))
    return [DocumentOut.from_doc(d) for d in docs]


@router.post("/{app_id}/submit", response_model=SubmitOut)
def submit_application(app_id: int, db=Depends(get_db), user=Depends(require_role("CUSTOMER"))):
    """DRAFT -> SUBMITTED, then run the agent pipeline. A second submit gets 409, so it's safe to double-click."""
    app = get_own_application(db, app_id, user)
    if app.status != "DRAFT":
        raise AppError(409, "ALREADY_SUBMITTED", "This application has already been submitted")
    app = set_status(db, app.id, "SUBMITTED", "CUSTOMER", actor_user_id=user.id, note="Submitted by customer")

    pipeline = None
    try:
        from app.agents.graph import run_pipeline

        pipeline = run_pipeline(db, app.id)
    except AppError as exc:
        print(f"Pipeline did not complete for application {app.id}: {exc.message}")
    db.refresh(app)
    return SubmitOut(application=ApplicationOut.from_app(app), pipeline=pipeline)
