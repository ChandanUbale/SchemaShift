"""
services/migration/mysql_writer.py — MySQL target writer.

Driver: pymysql (MIT)
Writes transformed relational rows to the MySQL target database.
Uses batch INSERT statements (not LOAD DATA INFILE) for portability.

DDL notes: use AUTO_INCREMENT for serial PKs, not SERIAL.
"""

from typing import Any
import pymysql

from app.services.migration.base_writer import BaseWriter


class MySQLWriter(BaseWriter):

    def __init__(self, dsn: str) -> None:
        """
        dsn: mysql+pymysql://user:pass@host:port/dbname
        TODO: parse DSN for pymysql.connect()
        """
        self.dsn = dsn
        self._conn: pymysql.connections.Connection | None = None

    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Connect to the target and execute CREATE TABLE statements from plan['generated_ddl'].
        Uses AUTO_INCREMENT PKs.
        TODO: parse generated_ddl, execute via cursor.
        """
        raise NotImplementedError("TODO: implement MySQLWriter.prepare")

    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Batch-insert rows into `entity_name` table.
        Use executemany() for efficiency.
        Returns count of rows written.
        TODO: build INSERT INTO `{entity_name}` (...) VALUES (%s, ...) and executemany().
        """
        raise NotImplementedError("TODO: implement MySQLWriter.write_batch")

    def finalize(self) -> None:
        """
        Commit the transaction and create any post-migration indexes.
        TODO: self._conn.commit(); create indexes from plan.
        """
        raise NotImplementedError("TODO: implement MySQLWriter.finalize")

    def cleanup(self, job_id: str) -> None:
        """
        DROP tables created by this job.
        TODO: track tables created in prepare(), issue DROP TABLE IF EXISTS.
        """
        raise NotImplementedError("TODO: implement MySQLWriter.cleanup")
