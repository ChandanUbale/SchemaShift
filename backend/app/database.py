"""
database.py — SQLAlchemy engine + session factory for the SQLite app-metadata store.

This database stores:
- Connection records (source + target DSNs)
- Job / progress state
- Profiling results
- Migration audit logs
- Validation reports

It does NOT store customer data — only SchemaShift operational metadata.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_engine(
    settings.sqlite_db_url,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session per request
# ---------------------------------------------------------------------------

def get_db():
    """Yield a SQLAlchemy session; close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# TODO: call Base.metadata.create_all(bind=engine) on startup
#       OR rely on Alembic migrations (preferred for production-like usage).
# ---------------------------------------------------------------------------
