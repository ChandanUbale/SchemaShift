"""
models/profiling.py — SQLAlchemy ORM model for profiling job results.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from app.database import Base


class ProfilingJob(Base):
    __tablename__ = "profiling_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)   # UUID string
    connection_id = Column(Integer, nullable=False)          # FK → connections.id
    status = Column(String(20), default="pending")           # pending | running | done | failed
    progress_pct = Column(Float, default=0.0)
    risk_label = Column(String(10), nullable=True)           # low | medium | high
    risk_score = Column(Float, nullable=True)
    results = Column(JSON, nullable=True)                    # profiling output JSON
    error = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
