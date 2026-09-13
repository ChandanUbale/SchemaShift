"""routers/discovery.py — Schema discovery endpoints (read-only, no target access)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.post("/{connection_id}/discover")
def discover_schema(connection_id: int, db: Session = Depends(get_db)):
    """
    Discover tables/collections, columns/fields, data types, constraints,
    indexes, and FK relationships for the given connection.

    - MySQL: reads INFORMATION_SCHEMA
    - MongoDB: samples documents to infer schema

    Returns a structured JSON with the discovered schema.
    TODO: call ConnectorFactory → connector.list_entities() + describe_entity()
    """
    raise NotImplementedError("TODO: implement discover_schema")


@router.get("/{connection_id}/schema")
def get_schema(connection_id: int, db: Session = Depends(get_db)):
    """Return the last-discovered schema JSON for a connection (from SQLite cache)."""
    raise NotImplementedError("TODO: implement get_schema")


@router.get("/{connection_id}/relationships")
def get_relationships(connection_id: int, db: Session = Depends(get_db)):
    """
    Return FK graph (MySQL) or embedded/reference patterns (MongoDB).
    Used by SchemaGraph.tsx to render the FK/relationship visualization.
    TODO: call relationship_mapper.build_graph(schema_json)
    """
    raise NotImplementedError("TODO: implement get_relationships")
