"""
models/migration.py — SQLAlchemy ORM model for migration job state and audit log.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean
from app.database import Base


class MigrationJob(Base):
    __tablename__ = "migration_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    source_connection_id = Column(Integer, nullable=False)
    target_connection_id = Column(Integer, nullable=False)
    plan_id = Column(String(36), nullable=True)              # recommendation / plan reference
    is_dry_run = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    status = Column(String(20), default="pending")           # pending | running | done | failed
    progress_pct = Column(Float, default=0.0)
    batches_total = Column(Integer, nullable=True)
    batches_done = Column(Integer, default=0)
    audit_log = Column(JSON, default=list)                   # list of batch results
    error = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # TODO: add cleanup/reset action tracking
