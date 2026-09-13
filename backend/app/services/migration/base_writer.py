"""
services/migration/base_writer.py — Abstract base class for all target writers.

MVP implements: MySQLWriter, MongoWriter.
Stretch/future: PostgreSQLWriter — same interface, no redesign.

Writers are the ONLY components allowed to write to the target database.
They must never be called from discovery, profiling, recommendation, or dry_runner.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseWriter(ABC):
    """
    Minimum interface that every target writer must implement.
    """

    @abstractmethod
    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Set up the target schema before migration begins.
        e.g. CREATE TABLE ... (MySQL) or ensure collection exists (MongoDB).
        Called once before the first write_batch.
        """
        ...

    @abstractmethod
    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Write a batch of transformed rows/documents to the target.
        Returns the number of rows successfully written.
        """
        ...

    @abstractmethod
    def finalize(self) -> None:
        """
        Called after all batches are written.
        e.g. create indexes, update stats.
        """
        ...

    @abstractmethod
    def cleanup(self, job_id: str) -> None:
        """
        Drop all tables/collections created by this job.
        Used by the cleanup/reset action — no automatic rollback.
        """
        ...
