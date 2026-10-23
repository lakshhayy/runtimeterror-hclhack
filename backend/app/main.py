"""LoanLens AI FastAPI app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.core.errors import register_error_handlers
from app.database import SessionLocal, init_db
from app.routers import advisor, analyst, applications, audit, auth, emi, products, rag, tracking


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup. If the DB is down, keep running so /health can report it."""
    try:
        init_db()
    except Exception as exc:
        print(f"Database init failed: {exc}")
    yield


app = FastAPI(title="LoanLens AI", lifespan=lifespan)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["health"])
def health():
    """Liveness check that also pings the database."""
    db_ok = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok}


# Order matters: applications before tracking, so /applications/mine isn't caught by /applications/{id}.
for router in (auth, products, emi, advisor, rag, applications, tracking, analyst, audit):
    app.include_router(router.router, prefix="/api/v1")
