"""EMI maths in Decimal. The LLM never does arithmetic; everything numeric comes from here."""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

STANDARD_TENURES = [12, 24, 36, 48, 60, 72, 84, 96, 120, 180, 240, 300, 360]
FOIR_TARGET = Decimal("40")
ELIGIBILITY_LABELS = {"LIKELY_ELIGIBLE": "Likely eligible", "BORDERLINE": "Borderline", "UNLIKELY": "Unlikely"}

ONE = Decimal("1")
CENT = Decimal("0.01")


def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _rupee(x: Decimal) -> Decimal:
    return x.quantize(ONE, rounding=ROUND_HALF_UP)


def _monthly_rate(annual_rate) -> Decimal:
    return _d(annual_rate) / Decimal("1200")


def format_inr(amount) -> str:
    """500000 -> ₹5,00,000 (Indian digit grouping)."""
    digits = str(int(_rupee(_d(amount))))
    sign = "-" if digits.startswith("-") else ""
    digits = digits.lstrip("-")
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"₹{sign}{digits}"


def calculate_emi(principal, annual_rate, months: int) -> Decimal:
    """EMI = P·r·(1+r)^n / ((1+r)^n − 1), r = annual/1200; P/n when r = 0. Rounded half-up to the rupee."""
    p, r, n = _d(principal), _monthly_rate(annual_rate), int(months)
    if r == 0:
        return _rupee(p / n)
    growth = (ONE + r) ** n
    return _rupee(p * r * growth / (growth - ONE))


def amortization_schedule(principal, annual_rate, months: int) -> list[dict]:
    """Month-by-month split of each EMI; the last row is adjusted so the balance ends at exactly 0."""
    p, r, n = _d(principal), _monthly_rate(annual_rate), int(months)
    emi = calculate_emi(p, annual_rate, n)
    balance = p
    rows = []
    for month in range(1, n + 1):
        interest = (balance * r).quantize(CENT, rounding=ROUND_HALF_UP)
        if month == n:
            principal_part = balance
            payment = principal_part + interest
        else:
            payment = emi
            principal_part = payment - interest
        balance = balance - principal_part
        rows.append({"month": month, "emi": payment, "interest": interest,
                     "principal": principal_part, "balance": balance})
    return rows


def total_interest(principal, annual_rate, months: int) -> Decimal:
    """Total interest paid over the loan, from the schedule."""
    return sum((row["interest"] for row in amortization_schedule(principal, annual_rate, months)), Decimal("0"))


def calc_foir(existing_emi, new_emi, monthly_income) -> Decimal:
    """FOIR = (existing EMI + new EMI) / income × 100, to 1 decimal."""
    income = _d(monthly_income)
    if income <= 0:
        raise ValueError("Monthly income must be greater than 0")
    foir = (_d(existing_emi) + _d(new_emi)) / income * Decimal("100")
    return foir.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def eligibility_from_foir(foir) -> str:
    foir = _d(foir)
    if foir <= 40:
        return "LIKELY_ELIGIBLE"
    if foir <= 50:
        return "BORDERLINE"
    return "UNLIKELY"


def max_affordable_principal(monthly_income, existing_emi, annual_rate, months: int, foir_limit=FOIR_TARGET) -> Decimal:
    """Largest loan whose EMI keeps FOIR within foir_limit, rounded DOWN to the nearest ₹10,000 (0 if none)."""
    room = _d(monthly_income) * _d(foir_limit) / Decimal("100") - _d(existing_emi)
    if room <= 0:
        return Decimal("0")
    r, n = _monthly_rate(annual_rate), int(months)
    if r == 0:
        principal = room * n
    else:
        growth = (ONE + r) ** n
        principal = room * (growth - ONE) / (r * growth)
    step = Decimal("10000")
    return (principal / step).quantize(ONE, rounding=ROUND_DOWN) * step


def _snapshot(principal, annual_rate, months, monthly_income, existing_emi) -> dict:
    emi = calculate_emi(principal, annual_rate, months)
    foir = calc_foir(existing_emi, emi, monthly_income)
    return {"emi": emi, "foir": foir, "eligibility": eligibility_from_foir(foir)}


def _candidate_tenures(tenure_min: int, tenure_max: int) -> list[int]:
    return sorted({t for t in STANDARD_TENURES if tenure_min <= t <= tenure_max} | {tenure_max})


def _option(kind, tenure, principal, annual_rate, monthly_income, existing_emi, label_fn) -> dict:
    snap = _snapshot(principal, annual_rate, tenure, monthly_income, existing_emi)
    option = {"type": kind, "tenureMonths": tenure, "principal": _d(principal), **snap}
    option["label"] = label_fn(option)
    return option


def what_if_options(principal, annual_rate, months: int, monthly_income, existing_emi,
                    tenure_min: int = 12, tenure_max: int = 360) -> dict:
    """Current EMI/FOIR plus simple suggestions.

    Not yet likely eligible -> TENURE (shortest longer tenure with FOIR <= 40) and AMOUNT (max affordable now).
    Already likely eligible -> SAVE (shortest shorter tenure still at FOIR <= 40, with interest saved).
    """
    principal, months = _d(principal), int(months)
    current = _snapshot(principal, annual_rate, months, monthly_income, existing_emi)
    tenures = _candidate_tenures(tenure_min, tenure_max)
    options = []

    def fits(t, p=principal):
        return _snapshot(p, annual_rate, t, monthly_income, existing_emi)["foir"] <= FOIR_TARGET

    if current["eligibility"] != "LIKELY_ELIGIBLE":
        longer = next((t for t in tenures if t > months and fits(t)), None)
        if longer:
            options.append(_option("TENURE", longer, principal, annual_rate, monthly_income, existing_emi,
                                   lambda o: f"Choose {o['tenureMonths']} months → EMI {format_inr(o['emi'])} → "
                                             f"{ELIGIBILITY_LABELS[o['eligibility']]}"))
        affordable = max_affordable_principal(monthly_income, existing_emi, annual_rate, months)
        if 0 < affordable < principal:
            options.append(_option("AMOUNT", months, affordable, annual_rate, monthly_income, existing_emi,
                                   lambda o: f"Borrow {format_inr(o['principal'])} over {o['tenureMonths']} months → "
                                             f"EMI {format_inr(o['emi'])} → {ELIGIBILITY_LABELS[o['eligibility']]}"))
    else:
        shorter = next((t for t in tenures if t < months and fits(t)), None)
        if shorter:
            saved = total_interest(principal, annual_rate, months) - total_interest(principal, annual_rate, shorter)
            option = _option("SAVE", shorter, principal, annual_rate, monthly_income, existing_emi,
                             lambda o: f"Choose {o['tenureMonths']} months → EMI {format_inr(o['emi'])} → "
                                       f"save {format_inr(saved)} interest")
            option["interestSaved"] = _rupee(saved)
            options.append(option)

    return {"current": current, "options": options}
