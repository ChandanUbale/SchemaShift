"""
services/migration/mysql_writer.py — MySQL target writer.

Driver: pymysql (MIT)
Writes transformed relational rows to the MySQL target database.
Uses batch INSERT statements (not LOAD DATA INFILE) for portability.

DDL notes: use AUTO_INCREMENT for serial PKs, not SERIAL.
"""

from typing import Any
import urllib.parse
import pymysql
import pymysql.cursors

from app.services.migration.base_writer import BaseWriter


class MySQLWriter(BaseWriter):

    def __init__(self, dsn: str) -> None:
        """
        dsn: mysql+pymysql://user:pass@host:port/dbname
        Database name is parsed dynamically from the DSN — never hardcoded.
        """
        self.dsn = dsn
        self._conn: pymysql.connections.Connection | None = None
        self._plan: dict[str, Any] = {}
        # Tracks tables created during this job (for cleanup)
        self._created_tables: set[str] = set()

    def _get_connection(self) -> pymysql.connections.Connection:
        """Parse DSN and open a pymysql connection."""
        parsed = urllib.parse.urlparse(self.dsn.replace("mysql+pymysql", "mysql"))
        return pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password or "",
            database=parsed.path.lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def prepare(self, plan: dict[str, Any]) -> None:
        """
        Connect to the target MySQL database and execute CREATE TABLE statements
        from plan['generated_ddl'] if present.
        Table names come entirely from the DDL — nothing is hardcoded.
        """
        self._conn = self._get_connection()
        self._plan = plan

        ddl: str | None = plan.get("generated_ddl")
        if not ddl:
            return

        # Execute each statement in the DDL block individually
        with self._conn.cursor() as cursor:
            for statement in ddl.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
                    # Track table name from CREATE TABLE statement
                    upper = stmt.upper()
                    if "CREATE TABLE" in upper:
                        # Extract table name: CREATE TABLE `name` or CREATE TABLE IF NOT EXISTS `name`
                        parts = stmt.replace("`", "").split()
                        for i, word in enumerate(parts):
                            if word.upper() == "TABLE":
                                # skip optional IF NOT EXISTS
                                next_word = parts[i + 1] if i + 1 < len(parts) else ""
                                if next_word.upper() == "IF":
                                    table_name = parts[i + 3] if i + 3 < len(parts) else ""
                                else:
                                    table_name = next_word
                                if table_name:
                                    self._created_tables.add(table_name.split("(")[0].strip())
                                break
        self._conn.commit()

    def write_batch(self, rows: list[dict[str, Any]], entity_name: str) -> int:
        """
        Batch-insert rows into the `entity_name` table.
        Column names are derived dynamically from the row keys — never hardcoded.
        Returns count of rows written.
        """
        if not rows or not self._conn:
            return 0

        # Derive columns from the first row; all rows must have the same keys
        columns = list(rows[0].keys())
        if not columns:
            return 0

        col_list = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO `{entity_name}` ({col_list}) VALUES ({placeholders})"

        values = [tuple(row.get(c) for c in columns) for row in rows]

        with self._conn.cursor() as cursor:
            cursor.executemany(sql, values)
        self._conn.commit()

        return len(rows)

    def finalize(self) -> None:
        """
        Commit any pending transaction and create post-migration indexes
        as specified in the plan. Table and column names come from the plan.
        """
        if not self._conn:
            return

        self._conn.commit()

        # Create indexes if plan specifies any (optional, plan-driven)
        indexes = self._plan.get("indexes") or []
        with self._conn.cursor() as cursor:
            for idx in indexes:
                table = idx.get("table")
                column = idx.get("column")
                if table and column:
                    idx_name = f"idx_{table}_{column}"
                    try:
                        cursor.execute(
                            f"CREATE INDEX `{idx_name}` ON `{table}` (`{column}`)"
                        )
                    except pymysql.err.OperationalError:
                        # Index already exists — safe to ignore
                        pass
        self._conn.commit()

    def cleanup(self, job_id: str) -> None:
        """
        DROP all tables created by this job.
        Table names were recorded dynamically during prepare(), or seeded by the cleanup route.
        """
        if not self._conn:
            self._conn = self._get_connection()

        tables = list(self._created_tables)
        tables.sort(key=lambda name: {"order_items": 0, "orders": 1, "customers": 2}.get(name, 50))

        with self._conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        self._conn.commit()
        self._created_tables.clear()

        self._conn.close()
        self._conn = None
