"""Password hashing, JWT tokens, current-user and role checks."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.audit import log_audit
from app.core.errors import AppError
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: User) -> str:
    """HS256 JWT with the user id (sub), role and expiry."""
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)) -> User:
    """Resolve the Bearer token to a User, or 401."""
    unauthorized = AppError(401, "UNAUTHORIZED", "Please log in again")
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_role(*roles: str):
    """Dependency factory: allow only the given roles; denials are audited."""

    def checker(request: Request, user: User = Depends(get_current_user), db=Depends(get_db)) -> User:
        if user.role not in roles:
            log_audit(db, action="ACCESS_DENIED", status="DENIED", user_id=user.id,
                      entity=request.url.path, input={"role": user.role, "allowed": list(roles)}, commit=True)
            raise AppError(403, "FORBIDDEN", "You don't have permission for this action")
        return user

    return checker
