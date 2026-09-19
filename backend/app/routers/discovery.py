"""routers/discovery.py — Schema discovery endpoints (read-only, no target access)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.database import get_db
from app.models.connection import Connection
from app.services.discovery.connector_factory import ConnectorFactory
from app.services.discovery.relationship_mapper import RelationshipMapper

router = APIRouter()


@router.post("/{connection_id}/discover")
def discover_schema(connection_id: int, db: Session = Depends(get_db)):
    """
    Discover tables/collections, columns/fields, data types, constraints,
    indexes, and FK relationships for the given connection.
    """
    conn_model = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn_model:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    try:
        if conn_model.source_type == "mysql":
            connector = ConnectorFactory.get_connector("mysql", conn_model.dsn)
            parsed = urlparse(conn_model.dsn.replace("mysql+pymysql", "mysql"))
            database_name = parsed.path.lstrip("/")
        elif conn_model.source_type == "mongodb":
            parsed = urlparse(conn_model.dsn)
            database_name = parsed.path.lstrip("/")
            connector = ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=database_name)
        else:
            raise HTTPException(status_code=400, detail="Unsupported source_type")

        connector.connect()
        entities_schema = []
        entity_names = connector.list_entities()
        counts = connector.estimate_counts()
        
        for name in entity_names:
            entity_metadata = connector.describe_entity(name)
            entity_metadata["estimated_count"] = counts.get(name, 0)
            entities_schema.append(entity_metadata)
            
        schema_json = {
            "source_type": conn_model.source_type,
            "database": database_name,
            "entities": entities_schema
        }
        
        conn_model.schema_json = schema_json
        db.commit()
        connector.disconnect()
        return schema_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connection_id}/schema")
def get_schema(connection_id: int, db: Session = Depends(get_db)):
    """Return the last-discovered schema JSON for a connection (from SQLite cache)."""
    conn_model = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn_model:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    if not conn_model.schema_json:
        raise HTTPException(status_code=404, detail="Schema not discovered yet")
        
    return conn_model.schema_json


@router.get("/{connection_id}/relationships")
def get_relationships(connection_id: int, db: Session = Depends(get_db)):
    """
    Return FK graph (MySQL) or embedded/reference patterns (MongoDB).
    Used by SchemaGraph.tsx to render the FK/relationship visualization.
    """
    conn_model = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn_model:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    if not conn_model.schema_json:
        raise HTTPException(status_code=404, detail="Schema not discovered yet")
        
    return RelationshipMapper.build_graph(conn_model.schema_json, conn_model.source_type)
