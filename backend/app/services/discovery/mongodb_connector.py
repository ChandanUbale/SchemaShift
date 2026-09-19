"""
MongoDB source connector — READ-ONLY.

Infers nested schema from sampled documents and returns the handshake Schema JSON
entity shape (columns + nesting).
"""

from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

from app.services.discovery.base_connector import BaseConnector

_SCHEMA_SAMPLE = 100


def _db_from_uri(uri: str) -> str:
    return urlparse(uri).path.lstrip("/").split("?")[0]


def _type_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (datetime, date)):
        return "date"
    if isinstance(value, ObjectId):
        return "objectid"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__.lower()


def _jsonable(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def walk_doc(
    doc: dict[str, Any],
    prefix: str,
    types: dict[str, set[str]],
    nulls: set[str],
    seen: dict[str, int],
    nesting: set[str],
) -> None:
    """Flatten one document into dotted paths. Arrays of objects go into nesting."""
    for key, value in doc.items():
        path = f"{prefix}.{key}" if prefix else key
        seen[path] = seen.get(path, 0) + 1
        if value is None:
            nulls.add(path)
            types.setdefault(path, set())
            continue
        types.setdefault(path, set()).add(_type_of(value))
        if isinstance(value, dict):
            walk_doc(value, path, types, nulls, seen, nesting)
        elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
            nesting.add(path)
            for item in value:
                if isinstance(item, dict):
                    walk_doc(item, path, types, nulls, seen, nesting)


class MongoDBConnector(BaseConnector):
    """Read-only MongoDB connector. db_name may be omitted if the URI path has it."""

    def __init__(self, uri: str, db_name: str = "", **_: Any) -> None:
        self.uri = uri
        self.db_name = db_name or _db_from_uri(uri)
        self._client: MongoClient | None = None
        self._db: Database | None = None

    def connect(self) -> None:
        if not self.db_name:
            raise ValueError("MongoDB db_name is required (URI path or db_name=)")
        self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        self._db = self._client[self.db_name]
        self._client.admin.command("ping")

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    def _col(self, name: str):
        if self._db is None:
            raise RuntimeError("MongoDBConnector is not connected")
        return self._db[name]

    def list_entities(self) -> list[str]:
        if self._db is None:
            raise RuntimeError("MongoDBConnector is not connected")
        return [n for n in self._db.list_collection_names() if not n.startswith("system.")]

    def describe_entity(self, entity_name: str) -> dict[str, Any]:
        raw = list(self._col(entity_name).aggregate([{"$sample": {"size": _SCHEMA_SAMPLE}}]))
        types: dict[str, set[str]] = {}
        nulls: set[str] = set()
        seen: dict[str, int] = {}
        nesting: set[str] = set()
        for doc in raw:
            if isinstance(doc, dict):
                walk_doc(doc, "", types, nulls, seen, nesting)

        n = len(raw)
        columns = []
        for path in sorted(seen):
            tset = types.get(path, set())
            data_type = "mixed" if len(tset) > 1 else (next(iter(tset)) if tset else "null")
            columns.append({
                "name": path,
                "data_type": data_type,
                "nullable": path in nulls or seen.get(path, 0) < n,
                "primary_key": path == "_id",
                "auto_increment": False,
            })
        return {
            "name": entity_name,
            "entity_kind": "collection",
            "estimated_count": self._col(entity_name).estimated_document_count(),
            "columns": columns,
            "indexes": [],
            "foreign_keys": [],
            "nesting": [{"path": p, "type": "array"} for p in sorted(nesting)],
        }

    def fetch_sample(self, entity_name: str, n: int) -> list[dict[str, Any]]:
        if n < 1:
            return []
        return [_jsonable(d) for d in self._col(entity_name).aggregate([{"$sample": {"size": n}}])]

    def fetch_batch(self, entity_name: str, offset: int, limit: int) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        cursor = self._col(entity_name).find().skip(max(offset, 0)).limit(limit)
        return [_jsonable(d) for d in cursor]

    def estimate_counts(self) -> dict[str, int]:
        if self._db is None:
            raise RuntimeError("MongoDBConnector is not connected")
        return {col: self._db[col].estimated_document_count() for col in self.list_entities()}
