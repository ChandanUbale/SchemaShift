"""
services/discovery/mysql_connector.py — MySQL source connector.

Driver: pymysql (MIT license)
Reads INFORMATION_SCHEMA for schema discovery.
Uses LIMIT for sampling (configurable via PROFILE_SAMPLE_SIZE).
"""

from typing import Any
import pymysql
import pymysql.cursors

from app.services.discovery.base_connector import BaseConnector


class MySQLConnector(BaseConnector):
    """
    Connects to a MySQL database and implements the BaseConnector interface.
    All operations are READ-ONLY.
    """

    def __init__(self, dsn: str) -> None:
        """
        dsn: mysql+pymysql://user:pass@host:port/dbname
        TODO: parse DSN into connection params for pymysql.connect()
        """
        self.dsn = dsn
        self._conn: pymysql.connections.Connection | None = None

    def connect(self) -> None:
        """
        Open a pymysql connection.
        TODO: parse self.dsn, call pymysql.connect(**params)
        """
        raise NotImplementedError("TODO: implement MySQLConnector.connect")

    def disconnect(self) -> None:
        """Close the pymysql connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def list_entities(self) -> list[str]:
        """
        Return all user table names from INFORMATION_SCHEMA.TABLES
        where TABLE_SCHEMA = current database.
        TODO: execute SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES ...
        """
        raise NotImplementedError("TODO: implement MySQLConnector.list_entities")

    def describe_entity(self, entity_name: str) -> dict[str, Any]:
        """
        Return columns, data types, nullability, keys, indexes, and FK relationships.
        TODO:
        - SELECT from INFORMATION_SCHEMA.COLUMNS
        - SELECT from INFORMATION_SCHEMA.KEY_COLUMN_USAGE for FKs
        - SELECT from INFORMATION_SCHEMA.STATISTICS for indexes
        """
        raise NotImplementedError("TODO: implement MySQLConnector.describe_entity")

    def fetch_sample(self, entity_name: str, n: int) -> list[dict[str, Any]]:
        """
        Return up to n rows using SELECT ... LIMIT n.
        For random sampling consider ORDER BY RAND() LIMIT n (acceptable at demo scale).
        TODO: execute SELECT * FROM `{entity_name}` LIMIT {n}
        """
        raise NotImplementedError("TODO: implement MySQLConnector.fetch_sample")

    def fetch_batch(self, entity_name: str, offset: int, limit: int) -> list[dict[str, Any]]:
        """
        Return a paginated batch for migration.
        TODO: SELECT * FROM `{entity_name}` LIMIT {limit} OFFSET {offset}
        Note: for large tables use a keyset cursor instead of OFFSET.
        """
        raise NotImplementedError("TODO: implement MySQLConnector.fetch_batch")

    def estimate_counts(self) -> dict[str, int]:
        """
        Return estimated row counts per table.
        TODO: SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES ...
        Note: TABLE_ROWS is an estimate for InnoDB; use COUNT(*) for exact counts.
        """
        raise NotImplementedError("TODO: implement MySQLConnector.estimate_counts")
