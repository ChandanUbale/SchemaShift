"""routers/connections.py — CRUD + test endpoints for source/target connections."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.connection import ConnectionCreate, ConnectionRead, ConnectionTestResult

router = APIRouter()


@router.post("/", response_model=ConnectionRead, status_code=201)
def create_connection(payload: ConnectionCreate, db: Session = Depends(get_db)):
    """
    Save a new source or target connection (DSN) to SQLite.
    TODO: validate DSN format, persist Connection model, return read schema.
    """
    raise NotImplementedError("TODO: implement create_connection")


@router.get("/", response_model=list[ConnectionRead])
def list_connections(db: Session = Depends(get_db)):
    """List all saved connections."""
    raise NotImplementedError("TODO: implement list_connections")


@router.get("/{connection_id}", response_model=ConnectionRead)
def get_connection(connection_id: int, db: Session = Depends(get_db)):
    """Fetch a single connection by ID."""
    raise NotImplementedError("TODO: implement get_connection")


@router.delete("/{connection_id}", status_code=204)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """Delete a connection record."""
    raise NotImplementedError("TODO: implement delete_connection")


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
def test_connection(connection_id: int, db: Session = Depends(get_db)):
    """
    Attempt to open a real connection to the database and return latency.
    Uses ConnectorFactory (MySQL or MongoDB) — read-only, no writes.
    TODO: call ConnectorFactory.get_connector(source_type, dsn).connect()
    """
    raise NotImplementedError("TODO: implement test_connection")
