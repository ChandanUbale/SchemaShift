"""
services/discovery/mongodb_connector.py — MongoDB source connector.

Driver: pymongo (Apache 2.0)
Uses $sample aggregation for sampling.
Infers schema by sampling documents (no fixed schema).
"""

from typing import Any
from pymongo import MongoClient
from pymongo.database import Database

from app.services.discovery.base_connector import BaseConnector


class MongoDBConnector(BaseConnector):
    """
    Connects to a MongoDB database and implements the BaseConnector interface.
    All operations are READ-ONLY on the source database.
    """

    def __init__(self, uri: str, db_name: str) -> None:
        """
        uri:     mongodb://user:pass@host:port  (or SRV URI)
        db_name: e.g. "demo_source"
        """
        self.uri = uri
        self.db_name = db_name
        self._client: MongoClient | None = None
        self._db: Database | None = None

    def connect(self) -> None:
        """
        Open a pymongo MongoClient connection.
        TODO: self._client = MongoClient(self.uri); self._db = self._client[self.db_name]
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.connect")

    def disconnect(self) -> None:
        """Close the MongoClient."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    def list_entities(self) -> list[str]:
        """
        Return collection names (excluding system.* collections).
        TODO: self._db.list_collection_names()
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.list_entities")

    def describe_entity(self, entity_name: str) -> dict[str, Any]:
        """
        Infer schema by sampling up to PROFILE_SAMPLE_SIZE documents.
        Detect: field names, inferred types, nesting depth, array fields.
        TODO: use $sample aggregation and merge field maps from sampled docs.
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.describe_entity")

    def fetch_sample(self, entity_name: str, n: int) -> list[dict[str, Any]]:
        """
        Return up to n documents using the $sample aggregation stage.
        TODO: self._db[entity_name].aggregate([{"$sample": {"size": n}}])
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.fetch_sample")

    def fetch_batch(self, entity_name: str, offset: int, limit: int) -> list[dict[str, Any]]:
        """
        Return a paginated batch using skip + limit.
        TODO: self._db[entity_name].find().skip(offset).limit(limit)
        For large collections prefer cursor-based pagination over skip.
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.fetch_batch")

    def estimate_counts(self) -> dict[str, int]:
        """
        Return estimated document counts per collection.
        TODO: {col: self._db[col].estimated_document_count() for col in list_entities()}
        """
        raise NotImplementedError("TODO: implement MongoDBConnector.estimate_counts")
