"""Document file storage: local disk (dev) or a private Supabase Storage bucket (deployed).

STORAGE_BACKEND=local     -> files under UPLOAD_DIR (wiped on redeploy on most hosts)
STORAGE_BACKEND=supabase  -> files in bucket STORAGE_BUCKET; survive restarts and redeploys
"""
from pathlib import Path

import httpx

from app.config import settings
from app.core.errors import AppError

BACKEND_DIR = Path(__file__).resolve().parents[2]
SUPABASE_PREFIX = "supabase://"
TIMEOUT_SECONDS = 30

_bucket_ready = False


def _use_supabase() -> bool:
    return settings.STORAGE_BACKEND.strip().lower() == "supabase"


def _upload_root() -> Path:
    path = Path(settings.UPLOAD_DIR)
    return path if path.is_absolute() else BACKEND_DIR / path


def _headers() -> dict:
    key = settings.SUPABASE_SERVICE_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _storage_url(path: str) -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/{path}"


def _ensure_bucket() -> None:
    """Create the private bucket on first use (ignored if it already exists)."""
    global _bucket_ready
    if _bucket_ready:
        return
    resp = httpx.post(_storage_url("bucket"), headers=_headers(), timeout=TIMEOUT_SECONDS,
                      json={"id": settings.STORAGE_BUCKET, "name": settings.STORAGE_BUCKET, "public": False})
    if resp.status_code not in (200, 201) and "already exists" not in resp.text.lower():
        raise AppError(503, "STORAGE_UNAVAILABLE", "Document storage is unavailable. Please try again shortly.")
    _bucket_ready = True


def save_file(key: str, content: bytes, content_type: str) -> str:
    """Store bytes under key (e.g. '12/abc_payslip.pdf'); returns the reference to keep in documents.file_path."""
    if not _use_supabase():
        path = _upload_root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    _ensure_bucket()
    try:
        resp = httpx.post(_storage_url(f"object/{settings.STORAGE_BUCKET}/{key}"), content=content,
                          headers={**_headers(), "Content-Type": content_type, "x-upsert": "true"},
                          timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError:
        raise AppError(503, "STORAGE_UNAVAILABLE", "Document storage is unavailable. Please try again shortly.")
    if resp.status_code not in (200, 201):
        raise AppError(503, "STORAGE_UNAVAILABLE", "Couldn't store the document. Please try again.")
    return f"{SUPABASE_PREFIX}{settings.STORAGE_BUCKET}/{key}"


def delete_file(ref: str) -> None:
    """Best-effort delete of a stored file (used when a document is replaced)."""
    try:
        if ref.startswith(SUPABASE_PREFIX):
            bucket, _, key = ref[len(SUPABASE_PREFIX):].partition("/")
            httpx.request("DELETE", _storage_url(f"object/{bucket}"), headers=_headers(),
                          json={"prefixes": [key]}, timeout=TIMEOUT_SECONDS)
        else:
            Path(ref).unlink(missing_ok=True)
    except Exception:
        pass  # an orphaned file must never block the customer's upload
