"""AppError, request IDs and the single error format: {"error": {"code", "message", "requestId"}}."""
import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("loanlens")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

HTTP_CODES = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


class AppError(Exception):
    """Raise this for any expected error; the handler turns it into the standard JSON."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Gives every request a uuid4, stores it in a contextvar and returns it as X-Request-ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard error body (also sets X-Request-ID, since 500s skip the middleware)."""
    request_id = getattr(request.state, "request_id", None) or request_id_var.get()
    body = {"error": {"code": code, "message": message, "requestId": request_id}}
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _readable_validation_message(exc: RequestValidationError) -> str:
    """e.g. 'amount: input should be greater than 0'."""
    parts = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
        msg = err.get("msg", "invalid value")
        msg = msg[0].lower() + msg[1:] if msg else msg
        parts.append(f"{'.'.join(loc)}: {msg}" if loc else msg)
    return "; ".join(parts) or "Invalid request"


def register_error_handlers(app: FastAPI) -> None:
    """Attach the request-ID middleware and all exception handlers."""
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        code = HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return error_response(request, 422, "VALIDATION_ERROR", _readable_validation_message(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return error_response(request, 500, "INTERNAL_ERROR", "Something went wrong. Please try again.")
