"""
models/validation.py — SQLAlchemy ORM model for validation report.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from app.database import Base


class ValidationReport(Base):
    __tablename__ = "validation_reports"

    id = Column(Integer, primary_key=True, index=True)
    migration_job_id = Column(Integer, nullable=False)       # FK → migration_jobs.id
    count_match_pct = Column(Float, nullable=True)           # e.g. 99.8
    aggregate_match = Column(String(10), nullable=True)      # "yes" | "no"
    sample_matched = Column(String(20), nullable=True)       # e.g. "100/100"
    relationship_checks = Column(String(20), nullable=True)  # "passed" | "failed"
    details = Column(JSON, nullable=True)                    # full report payload
    html_report_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
