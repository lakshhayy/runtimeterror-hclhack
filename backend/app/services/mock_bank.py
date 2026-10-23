"""Mocked credit bureau and KYC (no real external APIs)."""

MOCK_CREDIT_SCORES = {"priya@loanlens.com": 742, "rahul@loanlens.com": 640}
MOCK_KYC = {"priya@loanlens.com": "VERIFIED", "rahul@loanlens.com": "PENDING"}
DEFAULT_SCORE = 700
DEFAULT_KYC = "VERIFIED"


def credit_score_for(email: str) -> int:
    return MOCK_CREDIT_SCORES.get(email.lower(), DEFAULT_SCORE)


def kyc_status_for(email: str) -> str:
    return MOCK_KYC.get(email.lower(), DEFAULT_KYC)


def score_band(score: int) -> tuple[str, str]:
    """Credit band label and range, e.g. 742 -> ("GOOD", "720-759")."""
    if score < 650:
        return "POOR", "300-649"
    if score < 720:
        return "FAIR", "650-719"
    if score < 760:
        return "GOOD", "720-759"
    return "EXCELLENT", "760-900"
