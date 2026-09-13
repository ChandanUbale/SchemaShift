"""
services/migration/mongo_writer.py — MongoDB target writer.

Driver: pymongo (Apache 2.0)
Writes transformed document rows to the MongoDB target database.
Uses insert_many() per batch for efficiency.
"""

from typing import Any
from pymongo import MongoClient

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

    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Connect to the target MongoDB and ensure the database is accessible.
        Collections are created lazily on first insert_many().
        TODO: self._client = MongoClient(self.uri); validate connection.
        """
        raise NotImplementedError("TODO: implement MongoWriter.prepare")

    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Insert a batch of documents into the `entity_name` collection.
        Uses insert_many() for efficiency.
        Returns count of documents written.
        TODO: result = self._client[self.db_name][entity_name].insert_many(rows)
              return len(result.inserted_ids)
        """
        raise NotImplementedError("TODO: implement MongoWriter.write_batch")

    def finalize(self) -> None:
        """
        Create any post-migration indexes defined in the plan.
        TODO: iterate plan['model_tree'] index hints and call create_index().
        """
        raise NotImplementedError("TODO: implement MongoWriter.finalize")

    def cleanup(self, job_id: str) -> None:
        """
        Drop collections created by this job.
        TODO: track collection names in prepare(), call drop() on each.
        """
        raise NotImplementedError("TODO: implement MongoWriter.cleanup")
