"""Prompt-injection guard for any free text that goes to the LLM."""
from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.pii import mask_pii

INJECTION_PATTERNS = [
    "ignore previous",
    "ignore all",
    "ignore the rules",
    "ignore your instructions",
    "disregard",
    "system prompt",
    "you are now",
    "developer mode",
    "jailbreak",
    "approve my loan",
    "override",
    "act as admin",
]


def check_injection(text: str) -> bool:
    """True if the text contains a known injection phrase (case-insensitive)."""
    lowered = (text or "").lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


def guard_user_text(db, user, text: str, where: str) -> str:
    """Block injections (audited as BLOCKED), otherwise return the PII-masked text."""
    masked = mask_pii(text)
    if check_injection(text):
        log_audit(
            db,
            action="INJECTION_BLOCKED",
            status="BLOCKED",
            user_id=getattr(user, "id", None),
            input={"text": masked, "where": where},
            commit=True,
        )
        raise AppError(
            400,
            "BLOCKED_BY_GUARDRAIL",
            "This request was blocked by our safety rules. Please ask about loan products or policies.",
        )
    return masked
