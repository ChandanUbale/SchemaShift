"""
services/migration/mongo_writer.py — MongoDB target writer.

Driver: pymongo (Apache 2.0)
Writes transformed document rows to the MongoDB target database.
Uses insert_many() per batch for efficiency.
"""

from typing import Any
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.services.migration.base_writer import BaseWriter


class MongoWriter(BaseWriter):

    def __init__(self, uri: str, db_name: str) -> None:
        """
        uri:     mongodb://user:pass@host:port
        db_name: target database name (e.g. "migration_target")
        """
        self.uri = uri
        self.db_name = db_name
        self._client: MongoClient | None = None
        self._db = None
        self._plan: dict[str, Any] = {}
        self._collection_names: list[str] = []

    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Connect to the target MongoDB and ensure the database is accessible.
        Reads the target collection name from the plan's model_tree.
        Does NOT drop existing data — call cleanup() explicitly for that.
        """
        self._client = MongoClient(self.uri)
        self._db = self._client[self.db_name]

        # Validate connection with a ping
        self._client.admin.command("ping")

        # Store plan for use in finalize()
        self._plan = plan

        # Determine target collection name from plan
        model_tree = plan.get("model_tree") or {}
        collection_name = model_tree.get("collection", "customers")
        self._collection_names = [collection_name]

    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Insert a batch of documents into the `entity_name` collection.
        Uses insert_many() with ordered=False for efficiency.
        Returns count of documents written.
        """
        if not rows:
            return 0
        result = self._db[entity_name].insert_many(rows, ordered=False)
        return len(result.inserted_ids)

    def finalize(self) -> None:
        """
        Create post-migration indexes defined in the plan.
        Creates an index on 'email' if it appears in the model_tree fields.
        Silently ignores if the index already exists.
        """
        model_tree = self._plan.get("model_tree") or {}
        collection = model_tree.get("collection", "customers")
        fields = model_tree.get("fields", [])

        if "email" in fields or "name" in fields:
            try:
                self._db[collection].create_index("email")
            except OperationFailure:
                # Index already exists — safe to ignore
                pass

    def cleanup(self, job_id: str) -> None:
        """
        Drop all collections created by this job.
        """
        for name in self._collection_names:
            self._db[name].drop()
