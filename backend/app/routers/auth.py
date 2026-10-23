"""Auth routes."""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.security import create_token, get_current_user, verify_password
from app.database import get_db
from app.models import User
from app.schemas.common import LoginIn, LoginOut, UserOut

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


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The logged-in user."""
    return user
