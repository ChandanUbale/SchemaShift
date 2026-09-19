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
        db_name: target database name — parsed from the target connection DSN at call site
        """
        self.uri = uri
        self.db_name = db_name
        self._client: MongoClient | None = None
        self._db = None
        self._plan: dict[str, Any] = {}
        # Tracks every collection written to during this job (for cleanup)
        self._collection_names: set[str] = set()

    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Connect to the target MongoDB and ensure the database is accessible.
        Collection names are tracked dynamically when write_batch() is called —
        nothing is hardcoded here.
        Does NOT drop existing data — call cleanup() explicitly for that.
        """
        self._client = MongoClient(self.uri)
        self._db = self._client[self.db_name]

        # Validate connection with a ping
        self._client.admin.command("ping")

        # Store plan for use in finalize()
        self._plan = plan

    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Insert a batch of documents into the `entity_name` collection.
        entity_name is always passed in by the caller (batch_executor) —
        it comes from the source schema's entity list, never hardcoded here.
        Uses insert_many() with ordered=False for efficiency.
        Returns count of documents written.
        """
        if not rows:
            return 0
        # Track collection so cleanup() can drop it later
        self._collection_names.add(entity_name)
        result = self._db[entity_name].insert_many(rows, ordered=False)
        return len(result.inserted_ids)

    def finalize(self) -> None:
        """
        Create post-migration indexes on collections written during this job.
        Only creates an 'email' index if the plan explicitly lists 'email' in fields.
        Silently ignores if the index already exists.
        """
        model_tree = self._plan.get("model_tree") or {}
        fields = model_tree.get("fields", [])

        if "email" in fields:
            # Apply index to every collection written in this job
            for collection_name in self._collection_names:
                try:
                    self._db[collection_name].create_index("email")
                except OperationFailure:
                    # Index already exists — safe to ignore
                    pass

    def cleanup(self, job_id: str) -> None:
        """
        Drop all collections written during this job.
        Collection names were recorded dynamically in write_batch().
        """
        for name in self._collection_names:
            self._db[name].drop()
        self._collection_names.clear()
