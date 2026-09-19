"""
services/discovery/mysql_connector.py — MySQL source connector.

Driver: pymysql (MIT license)
Reads INFORMATION_SCHEMA for schema discovery.
Uses LIMIT for sampling (configurable via PROFILE_SAMPLE_SIZE).
"""

from typing import Any
import pymysql
import pymysql.cursors
import urllib.parse

from app.services.discovery.base_connector import BaseConnector


class MySQLConnector(BaseConnector):
    """
    Connects to a MySQL database and implements the BaseConnector interface.
    All operations are READ-ONLY.
    """

    def __init__(self, dsn: str) -> None:
        """
        dsn: mysql+pymysql://user:pass@host:port/dbname
        """
        self.dsn = dsn
        self._conn: pymysql.connections.Connection | None = None

    def connect(self) -> None:
        """
        Open a pymysql connection.
        """
        parsed = urllib.parse.urlparse(self.dsn.replace("mysql+pymysql", "mysql"))
        user = parsed.username
        password = parsed.password or ""
        host = parsed.hostname
        port = parsed.port or 3306
        database = parsed.path.lstrip("/")

        self._conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor
        )

    def disconnect(self) -> None:
        """Close the pymysql connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def list_entities(self) -> list[str]:
        """
        Return all user table names from INFORMATION_SCHEMA.TABLES
        where TABLE_SCHEMA = current database.
        """
        if not self._conn:
            raise RuntimeError("Not connected")
        with self._conn.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            return [row["TABLE_NAME"] for row in cursor.fetchall()]

    def describe_entity(self, entity_name: str) -> dict[str, Any]:
        """
        Return columns, data types, nullability, keys, indexes, and FK relationships.
        """
        if not self._conn:
            raise RuntimeError("Not connected")
        
        schema: dict[str, Any] = {
            "name": entity_name,
            "entity_kind": "table",
            "columns": [],
            "indexes": [],
            "foreign_keys": [],
            "nesting": []
        }

        with self._conn.cursor() as cursor:
            # Columns
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (entity_name,))
            for row in cursor.fetchall():
                col = {
                    "name": row["COLUMN_NAME"],
                    "data_type": row["DATA_TYPE"],
                    "nullable": row["IS_NULLABLE"] == 'YES'
                }
                if row["COLUMN_KEY"] == 'PRI':
                    col["primary_key"] = True
                if 'auto_increment' in row["EXTRA"]:
                    col["auto_increment"] = True
                schema["columns"].append(col)

            # Foreign Keys
            cursor.execute("""
                SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (entity_name,))
            for row in cursor.fetchall():
                schema["foreign_keys"].append({
                    "column": row["COLUMN_NAME"],
                    "ref_table": row["REFERENCED_TABLE_NAME"],
                    "ref_column": row["REFERENCED_COLUMN_NAME"]
                })

            # Indexes
            cursor.execute("""
                SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, (entity_name,))
            
            index_dict = {}
            for row in cursor.fetchall():
                idx_name = row["INDEX_NAME"]
                if idx_name not in index_dict:
                    index_dict[idx_name] = {
                        "name": idx_name,
                        "columns": [],
                        "unique": (row["NON_UNIQUE"] == 0)
                    }
                index_dict[idx_name]["columns"].append(row["COLUMN_NAME"])
            
            schema["indexes"] = list(index_dict.values())

        return schema

    def fetch_sample(self, entity_name: str, n: int) -> list[dict[str, Any]]:
        """
        Return up to n rows using SELECT ... LIMIT n.
        """
        if not self._conn:
            raise RuntimeError("Not connected")
        if entity_name not in self.list_entities():
            raise ValueError(f"Unknown table: {entity_name}")

        with self._conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{entity_name}` LIMIT %s", (n,))
            return cursor.fetchall()

    def fetch_batch(self, entity_name: str, offset: int, limit: int) -> list[dict[str, Any]]:
        """
        Return a paginated batch for migration.
        """
        if not self._conn:
            raise RuntimeError("Not connected")
        if entity_name not in self.list_entities():
            raise ValueError(f"Unknown table: {entity_name}")

        with self._conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{entity_name}` LIMIT %s OFFSET %s", (limit, offset))
            return cursor.fetchall()

    def estimate_counts(self) -> dict[str, int]:
        """
        Return estimated row counts per table.
        """
        if not self._conn:
            raise RuntimeError("Not connected")
        with self._conn.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
            """)
            return {row["TABLE_NAME"]: (row["TABLE_ROWS"] or 0) for row in cursor.fetchall()}
