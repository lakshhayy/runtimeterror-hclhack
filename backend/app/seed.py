"""Demo data. Run: python -m app.seed [--reset]

--reset drops every table and recreates it (clean demo). Without it, seeding only fills empty tables.
"""
import sys
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine, init_db
from app.models import LoanProduct, User

USERS = [
    dict(email="priya@loanlens.com", password="Customer@123", role="CUSTOMER", full_name="Priya Sharma",
         segment="SALARIED", monthly_income=60000, existing_emi=12000, pan_masked="XXXXX1234F"),
    dict(email="rahul@loanlens.com", password="Customer@123", role="CUSTOMER", full_name="Rahul Verma",
         segment="SELF_EMPLOYED", monthly_income=90000, existing_emi=40000, pan_masked="XXXXX5678K"),
    dict(email="officer@loanlens.com", password="Officer@123", role="OFFICER", full_name="Anil Mehta"),
    dict(email="analyst@loanlens.com", password="Analyst@123", role="ANALYST", full_name="Sneha Iyer"),
]

# (id, name, type, rate_min, rate_max, tenure_min, tenure_max, amount_min, amount_max, fee %, min score, segments, tags, description)
PRODUCTS = [
    ("PL-101", "Kestrel Personal Loan", "PERSONAL", "10.5", "16.0", 12, 60, 50000, 2500000, "1.5", 680, [],
     ["personal", "wedding", "travel", "medical"],
     "An unsecured loan for weddings, travel, medical bills or any personal need."),
    ("PL-102", "Kestrel Salary Plus Loan", "PERSONAL", "10.75", "15.0", 12, 72, 100000, 4000000, "1.0", 700,
     ["SALARIED"], ["salary", "personal"],
     "A higher-limit personal loan with lower fees for salaried customers."),
    ("HL-301", "Kestrel Home Loan", "HOME", "8.5", "9.75", 60, 360, 500000, 50000000, "0.5", 700,
     ["SALARIED", "SELF_EMPLOYED"], ["home", "house", "flat"],
     "Buy or build your home with long tenures of up to 30 years."),
    ("HL-302", "Kestrel Home Loan Self-Employed", "HOME", "9.0", "10.5", 60, 300, 500000, 30000000, "0.75", 700,
     ["SELF_EMPLOYED"], ["home", "business owner"],
     "A home loan designed for business owners and self-employed professionals."),
    ("VL-201", "Kestrel New Car Loan", "VEHICLE", "9.0", "11.5", 12, 84, 100000, 5000000, "1.0", 650, [],
     ["new car", "car"],
     "Finance up to the full on-road price of a new car."),
    ("VL-204", "Kestrel Pre-Owned Car Loan", "VEHICLE", "11.0", "14.0", 12, 60, 100000, 2000000, "1.5", 650, [],
     ["used car", "pre-owned", "second hand", "purani"],
     "Finance a used or pre-owned car with quick approval."),
    ("EL-401", "Kestrel Education Loan India", "EDUCATION", "9.5", "11.5", 12, 120, 50000, 2000000, "0", 650, [],
     ["education", "college", "study"],
     "Fund college or professional courses in India, with no processing fee."),
    ("EL-402", "Kestrel Global Education Loan", "EDUCATION", "10.0", "12.5", 12, 144, 500000, 15000000, "1.0", 650,
     [], ["abroad", "masters", "study abroad"],
     "Fund a degree abroad, covering tuition, living costs and travel."),
]


def _is_empty(db, model) -> bool:
    return db.scalar(select(func.count()).select_from(model)) == 0


def seed_users(db) -> int:
    """Insert demo users if the table is empty. Returns the number inserted."""
    if not _is_empty(db, User):
        return 0
    for u in USERS:
        data = dict(u)
        password = data.pop("password")
        for money in ("monthly_income", "existing_emi"):
            if money in data:
                data[money] = Decimal(data[money])
        db.add(User(password_hash=hash_password(password), **data))
    db.commit()
    return len(USERS)


def seed_products(db) -> int:
    """Insert the 8 loan products if the table is empty. Returns the number inserted."""
    if not _is_empty(db, LoanProduct):
        return 0
    for (pid, name, loan_type, rmin, rmax, tmin, tmax, amin, amax, fee, score, segments, tags, desc) in PRODUCTS:
        db.add(LoanProduct(
            id=pid, name=name, loan_type=loan_type, description=desc,
            rate_min=Decimal(rmin), rate_max=Decimal(rmax), tenure_min=tmin, tenure_max=tmax,
            amount_min=Decimal(amin), amount_max=Decimal(amax), processing_fee_pct=Decimal(fee),
            eligible_segments=segments, min_credit_score=score, tags=tags,
        ))
    db.commit()
    return len(PRODUCTS)


def seed_policies(db) -> str:
    """Ingest policy docs if the ingestion service exists yet (added in chunk 3.2)."""
    try:
        from app.services.ingest import ingest_policies

        return f"{ingest_policies(db)} policy chunks ingested"
    except Exception as exc:  # ImportError / NotImplementedError / LLM or file errors
        db.rollback()
        return f"Policy ingestion skipped: {exc or type(exc).__name__}"


def main(reset: bool = False) -> None:
    if reset:
        from app import models  # noqa: F401  (make sure every table is known before drop_all)

        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")
    init_db()
    with SessionLocal() as db:
        users = seed_users(db)
        products = seed_products(db)
        policies = seed_policies(db)
    print("Seed summary:")
    print(f"  users inserted:    {users}")
    print(f"  products inserted: {products}")
    print(f"  {policies}")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
