"""
models/connection.py — SQLAlchemy ORM model for source/target connection metadata.

Stores the connection string (DSN) and type for both source and target.
Connection strings are stored in plain text for the hackathon demo.
Production: encrypt at rest + use a secrets manager.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from app.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)          # human-readable label
    source_type = Column(String(50), nullable=False)    # "mysql" | "mongodb"
    dsn = Column(String(1024), nullable=False)          # connection string — NOT encrypted
    is_source = Column(Boolean, default=True)           # True = source, False = target
    schema_json = Column(JSON, nullable=True)           # Added for discovery schema
    created_at = Column(DateTime, default=datetime.utcnow)

    # TODO: add relationship to ProfilingJob, MigrationJob once those models exist
