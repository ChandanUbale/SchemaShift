"""
main.py — FastAPI application entry point.

Responsibilities:
- Create the FastAPI app instance with lifespan context
- Create all SQLite tables on startup (dev convenience; Alembic owns schema in prod)
- Configure CORS for the Vite dev server
- Mount all routers under /api/
- Expose a /health liveness probe
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import connections, discovery, migration, profiling, recommendation, validation


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (idempotent; skips existing tables)."""
    Base.metadata.create_all(bind=engine)
    yield
    # Nothing to tear down for SQLite; add cleanup here if needed.


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SchemaShift",
    description="Schema Migration Intelligence Platform — MySQL ↔ MongoDB",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any same-origin prod deployment
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:8000",   # FastAPI itself (for same-origin requests)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(connections.router,    prefix="/api/connections",    tags=["connections"])
app.include_router(discovery.router,      prefix="/api/discovery",      tags=["discovery"])
app.include_router(profiling.router,      prefix="/api/profiling",      tags=["profiling"])
app.include_router(recommendation.router, prefix="/api/recommendation", tags=["recommendation"])
app.include_router(migration.router,      prefix="/api/migration",      tags=["migration"])
app.include_router(validation.router,     prefix="/api/validation",     tags=["validation"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
def health_check():
    """Liveness probe — returns 200 if the API is up."""
    return {"status": "ok"}
