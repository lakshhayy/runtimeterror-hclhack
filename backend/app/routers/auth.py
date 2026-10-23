"""Auth routes."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.security import create_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas.common import LoginIn, LoginOut, SignupIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db=Depends(get_db)):
    """Email + password -> JWT. Failures are audited."""
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        log_audit(db, action="LOGIN_FAILED", status="DENIED", user_id=user.id if user else None,
                  actor=f"user:{user.id}" if user else "anonymous", input={"email": email}, commit=True)
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    log_audit(db, action="LOGIN", user_id=user.id, input={"email": email}, commit=True)
    return LoginOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.post("/signup", response_model=LoginOut, status_code=201)
def signup(body: SignupIn, db=Depends(get_db)):
    """Create a CUSTOMER account and log it in. Staff roles can't be self-registered."""
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        log_audit(db, action="SIGNUP_FAILED", status="DENIED", actor="anonymous",
                  input={"email": email, "reason": "email already registered"}, commit=True)
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists. Please log in.")

    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name.strip(),
                role="CUSTOMER", segment=body.segment, monthly_income=body.monthly_income,
                existing_emi=body.existing_emi)
    db.add(user)
    db.flush()
    log_audit(db, action="SIGNUP", user_id=user.id, input={"email": email, "segment": body.segment})
    db.commit()
    db.refresh(user)
    return LoginOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The logged-in user."""
    return user
