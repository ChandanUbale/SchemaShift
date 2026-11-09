"""routers/connections.py — CRUD + test endpoints for source/target connections."""

import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connection import Connection
from app.schemas.connection import ConnectionCreate, ConnectionProbe, ConnectionRead, ConnectionTestResult
from app.services.discovery.connector_factory import ConnectorFactory
from app.services.discovery.database_inspector import ensure_mysql_database, inspect_connection, list_databases

router = APIRouter()


@router.post("/databases")
def discover_databases(payload: ConnectionProbe):
    """List databases visible through an unsaved connection string."""
    try:
        return {"databases": list_databases(payload.source_type, payload.dsn)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _open_connector(conn_model: Connection):
    if conn_model.source_type == "mysql":
        return ConnectorFactory.get_connector("mysql", conn_model.dsn)
    if conn_model.source_type == "mongodb":
        parsed = urlparse(conn_model.dsn)
        db_name = parsed.path.lstrip("/")
        return ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=db_name)
    raise ValueError(f"Unsupported source_type: {conn_model.source_type}")


@router.post("/", response_model=ConnectionRead, status_code=201)
def create_connection(payload: ConnectionCreate, db: Session = Depends(get_db)):
    row = Connection(
        name=payload.name,
        source_type=payload.source_type,
        dsn=payload.dsn,
        is_source=payload.is_source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/", response_model=list[ConnectionRead])
def list_connections(db: Session = Depends(get_db)):
    return db.query(Connection).order_by(Connection.id.desc()).all()


@router.get("/{connection_id}", response_model=ConnectionRead)
def get_connection(connection_id: int, db: Session = Depends(get_db)):
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    return row


@router.delete("/{connection_id}", status_code=204)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(row)
    db.commit()


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
def test_connection(connection_id: int, db: Session = Depends(get_db)):
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    started = time.perf_counter()
    connector = None
    try:
        if not row.is_source and row.source_type == "mysql":
            ensure_mysql_database(row.dsn)
        connector = _open_connector(row)
        connector.connect()
        latency = (time.perf_counter() - started) * 1000
        return ConnectionTestResult(success=True, message="Connected", latency_ms=round(latency, 1))
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000
        return ConnectionTestResult(success=False, message=str(exc), latency_ms=round(latency, 1))
    finally:
        if connector is not None:
            try:
                connector.disconnect()
            except Exception:
                pass


@router.post("/{connection_id}/inspect")
def inspect_saved_connection(connection_id: int, db: Session = Depends(get_db)):
    """Connect read-only and list existing tables or collections in the saved database."""
    row = db.query(Connection).filter(Connection.id == connection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        return inspect_connection(row.source_type, row.dsn)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
