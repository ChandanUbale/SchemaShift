"""
services/migration/safety.py — Validates source vs target connections to prevent accidental overwrites.
"""

import urllib.parse
from fastapi import HTTPException

from app.config import settings


def _normalize_dsn(dsn: str) -> tuple[str, str, int, str]:
    """
    Parse a DSN into (engine, host, port, database).
    Handles mysql+pymysql prefixes and standardizes defaults.
    """
    # Standardize scheme for parsing
    clean_dsn = dsn.replace("mysql+pymysql", "mysql")
    parsed = urllib.parse.urlparse(clean_dsn)
    
    engine = parsed.scheme
    host = parsed.hostname or "localhost"
    
    port = parsed.port
    if engine == "mysql":
        port = port or 3306
    elif engine == "mongodb":
        port = port or 27017
        
    database = parsed.path.lstrip("/")
    
    if engine == "mongodb" and not database:
        database = settings.target_mongo_db
        
    return (engine, host, port, database)


def assert_distinct_targets(source_dsn: str, target_dsn: str, in_place: bool) -> None:
    """
    Ensure the source and target do not point to the exact same database,
    unless the user explicitly confirms in-place optimisation.
    Raises HTTP 400 if unsafe.
    """
    src_engine, src_host, src_port, src_db = _normalize_dsn(source_dsn)
    tgt_engine, tgt_host, tgt_port, tgt_db = _normalize_dsn(target_dsn)
    
    # Check if host, port, and database match exactly
    if (src_host, src_port, src_db) == (tgt_host, tgt_port, tgt_db):
        if not in_place:
            raise HTTPException(
                status_code=400, 
                detail="Source and target are the same database. Set in_place_optimisation=true to confirm."
            )
