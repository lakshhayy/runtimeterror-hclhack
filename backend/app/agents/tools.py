"""Agent tools. Agents reach data ONLY through these, via call_tool. Results are plain JSON values."""
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.agents.registry import register_tool
from app.core.status import set_status
from app.models import Application, Document, User
from app.services import mock_bank
from app.services.emi import calc_foir as foir_of
from app.services.emi import calculate_emi


def _app(db, application_id: int) -> Application:
    return db.get(Application, application_id)


@register_tool("get_documents")
def get_documents(db, application_id: int) -> list[str]:
    """Uploaded document types, e.g. ["IDENTITY", "INCOME"]."""
    return sorted(db.scalars(select(Document.doc_type).where(Document.application_id == application_id)))


@register_tool("verify_income")
def verify_income(db, application_id: int) -> dict:
    """Compare declared income with the 'verified' income (simulated from the salary slip = profile income)."""
    app = _app(db, application_id)
    declared = Decimal(app.declared_income)
    verified = app.user.monthly_income
    if not verified:
        return {"declared": int(declared), "verified": None, "mismatchPct": None, "ok": False,
                "source": "simulated from salary slip"}
    mismatch = (abs(declared - verified) / verified * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {"declared": int(declared), "verified": int(verified), "mismatchPct": float(mismatch),
            "ok": mismatch <= 10, "source": "simulated from salary slip"}


@register_tool("get_credit_score")
def get_credit_score(db, user_id: int) -> dict:
    user = db.get(User, user_id)
    score = mock_bank.credit_score_for(user.email)
    band, band_range = mock_bank.score_band(score)
    return {"score": score, "band": band, "bandRange": band_range}


@register_tool("calc_foir")
def calc_foir(db, application_id: int) -> dict:
    """EMI at the product's starting rate, and FOIR using declared income + existing EMIs."""
    app = _app(db, application_id)
    emi = calculate_emi(app.amount, app.product.rate_min, app.tenure_months)
    foir = foir_of(app.user.existing_emi or 0, emi, app.declared_income)
    return {"emi": int(emi), "foir": float(foir), "limit": 50}


@register_tool("get_kyc_status")
def get_kyc_status(db, user_id: int) -> dict:
    return {"status": mock_bank.kyc_status_for(db.get(User, user_id).email)}


@register_tool("policy_lookup")
def policy_lookup(db, loan_type: str):
    """Top eligibility policy source for this loan type, or None if unavailable."""
    try:
        from app.database import SessionLocal
        from app.services.rag import retrieve

        # Separate short session: a failed lookup can't break the pipeline's transaction.
        with SessionLocal() as lookup_db:
            rows = retrieve(lookup_db, "eligibility criteria minimum credit score", "OFFICER", loan_type, k=1)
        if not rows:
            return None
        top = rows[0]
        return {"document": top["doc_title"], "section": top["section"], "version": top["version"]}
    except Exception:
        return None


@register_tool("update_application_status")
def update_application_status(db, application_id: int, new_status: str, note: str = "") -> str:
    """Status changes go through the state machine as role AGENT (which can never approve or reject)."""
    return set_status(db, application_id, new_status, actor_role="AGENT", note=note).status
