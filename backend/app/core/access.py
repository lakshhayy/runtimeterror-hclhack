"""Ownership checks for applications."""
from app.core.errors import AppError
from app.models import Application, User

STAFF_ROLES = ("OFFICER", "ANALYST")


def get_application_or_404(db, app_id: int, user: User) -> Application:
    """Return the application if the user owns it or is staff. Otherwise 404 (not 403), so we don't reveal it exists."""
    app = db.get(Application, app_id)
    if app is None or (app.user_id != user.id and user.role not in STAFF_ROLES):
        raise AppError(404, "NOT_FOUND", "Application not found")
    return app
