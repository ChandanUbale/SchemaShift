"""
services/discovery/base_connector.py — Abstract base class for all source connectors.

MVP implements: MySQLConnector, MongoDBConnector.
Stretch/future: PostgreSQLConnector, SQLServerConnector — same interface, no redesign.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """
    Minimum interface that every source connector must implement.
    Connectors are READ-ONLY — they must never write to the source database.
    """

    @abstractmethod
    def connect(self) -> None:
        """Open and validate the database connection."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close the database connection."""
        ...

    @abstractmethod
    def list_entities(self) -> list[str]:
        """Return a list of table names (MySQL) or collection names (MongoDB)."""
        ...

    @abstractmethod
    def describe_entity(self, entity_name: str) -> dict[str, Any]:
        """
        Return schema metadata for a single table/collection.
        MySQL: columns, data types, constraints, indexes, FK relationships.
        MongoDB: inferred field names, types, nesting depth.
        """
        ...

    @abstractmethod
    def fetch_sample(self, entity_name: str, n: int) -> list[dict[str, Any]]:
        """
        Return up to n rows/documents from the entity.
        MySQL: LIMIT n (or ORDER BY RAND() LIMIT n for random sample).
        MongoDB: $sample aggregation.
        Sampling logic stays INSIDE the connector.
        """
        ...

    @abstractmethod
    def fetch_batch(self, entity_name: str, offset: int, limit: int) -> list[dict[str, Any]]:
        """Return a paginated batch of rows/documents for migration."""
        ...

    @abstractmethod
    def estimate_counts(self) -> dict[str, int]:
        """Return estimated row/document counts per table/collection."""
        ...
