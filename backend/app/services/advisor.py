"""AI Loan Advisor: the LLM only extracts fields from plain language; matching and maths are code."""
import re
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.guardrails import guard_user_text
from app.core.llm import chat_json
from app.models import LoanProduct
from app.schemas.advisor import AdvisorExtract, AdvisorResponse, Recommendation
from app.services.emi import calc_foir, calculate_emi, eligibility_from_foir, format_inr

EXTRACT_PROMPT = """You extract loan requirements from a bank customer's message (English or Hinglish).
Rules:
- "lakh"/"lac" = 100000, "crore"/"cr" = 10000000, "k" = 1000. Examples: "5 lakh" = 500000, "60k" = 60000, "1.2 crore" = 12000000.
- loanType: car / gaadi / bike / vehicle -> VEHICLE; house / flat / ghar / home -> HOME; college / study / masters / education -> EDUCATION; wedding / travel / medical / personal -> PERSONAL.
- purpose: a short noun phrase such as "used car", "new car", "home purchase", "masters abroad", "wedding".
- monthlyIncome: the customer's monthly income or salary, if stated.
- maxPreferredEmi: the highest monthly EMI the customer wants, if stated.
- Never calculate anything. Use null for anything not stated."""

TYPE_LABELS = {"PERSONAL": "Personal", "HOME": "Home", "VEHICLE": "Vehicle", "EDUCATION": "Education"}
CLARIFY_TYPE = "What is the loan for — car, home, education or personal?"
CLARIFY_AMOUNT = "How much would you like to borrow?"
CLARIFY_INCOME = "What is your monthly income?"


def _int(x) -> int | None:
    return None if x is None else int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def interpreted_requirement(ex: AdvisorExtract) -> str:
    """e.g. 'Used car loan of ₹5,00,000 with EMI below ₹12,000'."""
    purpose = re.sub(r"\s*loan$", "", (ex.purpose or "").strip(), flags=re.IGNORECASE)
    if purpose:
        subject = purpose[0].upper() + purpose[1:]
    elif ex.loan_type:
        subject = TYPE_LABELS[ex.loan_type]
    else:
        subject = "A"
    text = f"{subject} loan"
    if ex.loan_amount:
        text += f" of {format_inr(ex.loan_amount)}"
    if ex.max_preferred_emi:
        text += f" with EMI below {format_inr(ex.max_preferred_emi)}"
    return text


def _tag_score(product: LoanProduct, text: str) -> int:
    """Length of the longest product tag found in the text (so 'used car' beats 'car')."""
    return max((len(tag) for tag in product.tags if tag.lower() in text), default=0)


def match_products(db, ex: AdvisorExtract, user, message: str, limit: int = 2) -> list[LoanProduct]:
    """Products of the right type whose amount range fits and that allow the user's segment, best tag match first."""
    amount = Decimal(ex.loan_amount)
    products = db.scalars(select(LoanProduct).where(LoanProduct.loan_type == ex.loan_type)).all()
    fitting = [
        p for p in products
        if p.amount_min <= amount <= p.amount_max
        and (not p.eligible_segments or user.segment in p.eligible_segments)
    ]
    text = f"{message} {ex.purpose or ''}".lower()
    fitting.sort(key=lambda p: (-_tag_score(p, text), p.rate_min, p.id))
    return fitting[:limit]


def _candidate_tenures(tenure_min: int, tenure_max: int) -> list[int]:
    return sorted(set(range(tenure_min, tenure_max + 1, 12)) | {tenure_max})


def build_recommendation(product, amount, max_emi, income, existing_emi) -> Recommendation:
    """Pure: pick the shortest tenure that meets the EMI limit (or FOIR <= 40), else the longest. Templated reason."""
    rate = product.rate_min

    def evaluate(t):
        emi = calculate_emi(amount, rate, t)
        return emi, calc_foir(existing_emi, emi, income)

    tenures = _candidate_tenures(product.tenure_min, product.tenure_max)
    if max_emi:
        chosen = next((t for t in tenures if evaluate(t)[0] <= max_emi), tenures[-1])
    else:
        chosen = next((t for t in tenures if evaluate(t)[1] <= 40), tenures[-1])
    emi, foir = evaluate(chosen)
    share = f"total EMIs = {_int(foir)}% of income (limit 50%)"

    if max_emi and emi <= max_emi:
        reason = f"{chosen}-month tenure keeps EMI {format_inr(emi)} under your {format_inr(max_emi)} limit; {share}"
    elif max_emi:
        reason = f"Even at {chosen} months, EMI {format_inr(emi)} is above your {format_inr(max_emi)} limit; {share}"
    else:
        reason = f"{chosen}-month tenure gives EMI {format_inr(emi)}; {share}"

    return Recommendation(
        product_id=product.id, product_name=product.name, indicative_interest_rate=float(rate),
        tenure_months=chosen, estimated_emi=_int(emi), reason=reason,
        eligibility_indicator=eligibility_from_foir(foir),
    )


def _clarify(ex: AdvisorExtract, question: str, income=None) -> AdvisorResponse:
    return AdvisorResponse(
        interpreted_requirement=interpreted_requirement(ex), loan_amount=ex.loan_amount,
        monthly_income=_int(income), max_preferred_emi=ex.max_preferred_emi, clarifying_question=question,
    )


def advise(db, user, message: str) -> AdvisorResponse:
    """Guard -> extract -> fill from profile -> clarify or recommend -> audit."""
    masked = guard_user_text(db, user, message, where="advisor")
    ex = chat_json(EXTRACT_PROMPT, masked, AdvisorExtract)
    if ex is None:
        raise AppError(503, "AI_UNAVAILABLE",
                       "The AI advisor is unavailable right now. Please try the EMI calculator or try again shortly.")

    income = ex.monthly_income or user.monthly_income
    existing_emi = user.existing_emi or Decimal("0")

    if not ex.loan_type:
        response = _clarify(ex, CLARIFY_TYPE, income)
    elif not ex.loan_amount:
        response = _clarify(ex, CLARIFY_AMOUNT, income)
    elif not income:
        response = _clarify(ex, CLARIFY_INCOME)
    else:
        products = match_products(db, ex, user, masked)
        if not products:
            response = _clarify(ex, f"None of our {TYPE_LABELS[ex.loan_type].lower()} loans cover "
                                    f"{format_inr(ex.loan_amount)} for your profile. Could you try a different amount?",
                                income)
        else:
            response = AdvisorResponse(
                interpreted_requirement=interpreted_requirement(ex), loan_amount=ex.loan_amount,
                monthly_income=_int(income), max_preferred_emi=ex.max_preferred_emi,
                recommendations=[build_recommendation(p, ex.loan_amount, ex.max_preferred_emi, income, existing_emi)
                                 for p in products],
            )

    log_audit(db, action="ADVISOR_CHAT", user_id=user.id, input={"message": masked},
              output={"interpreted": response.interpreted_requirement,
                      "products": [r.product_id for r in response.recommendations],
                      "clarifyingQuestion": response.clarifying_question},
              commit=True)
    return response
