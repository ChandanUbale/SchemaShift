"""
main.py — FastAPI application entry point.

Responsibilities:
- Create the FastAPI app instance
- Configure CORS
- Mount all routers
- SSE progress endpoint (delegated to routers/migration.py)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import connections, discovery, profiling, recommendation, migration, validation

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SchemaShift",
    description="Schema Migration Intelligence Platform — MySQL ↔ MongoDB",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS (allow Vite dev server and same-origin prod)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(connections.router, prefix="/api/connections", tags=["connections"])
app.include_router(discovery.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(profiling.router, prefix="/api/profiling", tags=["profiling"])
app.include_router(recommendation.router, prefix="/api/recommendation", tags=["recommendation"])
app.include_router(migration.router, prefix="/api/migration", tags=["migration"])
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
def health_check():
    """Liveness probe — returns 200 if the API is up."""
    return {"status": "ok"}
