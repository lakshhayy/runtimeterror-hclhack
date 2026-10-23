"""Application detail for status tracking (customer) and review (staff)."""
from sqlalchemy import select

from app.models import DOC_LABELS, DOC_TYPES, AgentRun, AgentStep, Application, Decision, Document, StatusHistory
from app.schemas.applications import ApplicationOut, DocumentOut
from app.schemas.products import ProductOut
from app.schemas.tracking import ApplicationDetail, DecisionOut, StepOut, TimelineOut

NEXT_STEPS = {
    "DRAFT": "Upload your documents and submit.",
    "SUBMITTED": "Automated checks are starting.",
    "UNDER_REVIEW": "A credit analyst is reviewing your application.",
    "APPROVED": "Approved! The loan officer will schedule disbursal.",
    "REJECTED": "Not approved. See the analyst's note for the reason.",
    "DISBURSED": "Loan amount disbursed.",
}


def next_step(app: Application, missing_docs: list[str], docs_requested: bool = False) -> str:
    """Plain-language next step for the customer."""
    if app.status == "UNDER_VERIFICATION":
        if missing_docs:
            return f"Upload: {', '.join(missing_docs)}, then click 'Submit documents'."
        if docs_requested:
            return "Upload the documents the analyst asked for, then click 'Submit documents'."
        return "Automated checks in progress."
    return NEXT_STEPS.get(app.status, "")


def build_application_detail(db, app: Application) -> ApplicationDetail:
    docs = list(db.scalars(select(Document).where(Document.application_id == app.id).order_by(Document.doc_type)))
    uploaded = {d.doc_type for d in docs}
    missing_types = [t for t in DOC_TYPES if t not in uploaded]

    run = db.scalar(select(AgentRun).where(AgentRun.application_id == app.id)
                    .order_by(AgentRun.created_at.desc(), AgentRun.id.desc()))
    steps = []
    if run is not None:
        steps = list(db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_order)))
    history = list(db.scalars(select(StatusHistory).where(StatusHistory.application_id == app.id)
                              .order_by(StatusHistory.created_at, StatusHistory.id)))
    decision = db.scalar(select(Decision).where(Decision.application_id == app.id)
                         .order_by(Decision.created_at.desc(), Decision.id.desc()))

    docs_requested = bool(decision and decision.decision == "REQUEST_DOCUMENTS")
    return ApplicationDetail(
        application=ApplicationOut.from_app(app),
        product=ProductOut.model_validate(app.product),
        documents=[DocumentOut.from_doc(d) for d in docs],
        latest_run=run.result_json if run is not None and run.status == "COMPLETED" else None,
        latest_run_status=run.status if run is not None else None,
        steps=[StepOut.model_validate(s) for s in steps],
        timeline=[TimelineOut.model_validate(h) for h in history],
        latest_decision=DecisionOut.model_validate(decision) if decision else None,
        missing_doc_types=missing_types,
        next_step=next_step(app, [DOC_LABELS[t] for t in missing_types], docs_requested),
    )
