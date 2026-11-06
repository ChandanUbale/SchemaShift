"""routers/connections.py — CRUD + test endpoints for source/target connections."""

import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connection import Connection
from app.schemas.connection import ConnectionCreate, ConnectionRead, ConnectionTestResult
from app.services.discovery.connector_factory import ConnectorFactory

router = APIRouter()


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
