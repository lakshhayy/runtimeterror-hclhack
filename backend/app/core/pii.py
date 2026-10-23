"""Regex PII masking. Applied before any LLM call or log write."""
import re

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")


def _mask_pan(m: re.Match) -> str:
    return "XXXXX" + m.group()[5:]


def _mask_aadhaar(m: re.Match) -> str:
    return "XXXX XXXX " + re.sub(r"\s", "", m.group())[-4:]


def _mask_account(m: re.Match) -> str:
    digits = m.group()
    return "X" * (len(digits) - 4) + digits[-4:]


def mask_pii(text: str) -> str:
    """Mask PAN, Aadhaar and bank account numbers. Aadhaar runs before account numbers."""
    if not text:
        return text
    text = PAN_RE.sub(_mask_pan, text)
    text = AADHAAR_RE.sub(_mask_aadhaar, text)
    return ACCOUNT_RE.sub(_mask_account, text)


def mask_pii_in(obj):
    """Apply mask_pii to every string inside nested dicts/lists."""
    if isinstance(obj, str):
        return mask_pii(obj)
    if isinstance(obj, dict):
        return {k: mask_pii_in(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [mask_pii_in(v) for v in obj]
    return obj
