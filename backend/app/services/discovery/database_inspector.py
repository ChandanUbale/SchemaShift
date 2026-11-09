"""Read-only helpers for listing databases and inspecting a target connection."""

from typing import Any
from urllib.parse import unquote, urlparse

import pymysql
import pymysql.cursors
from pymongo import MongoClient

from app.services.discovery.connector_factory import ConnectorFactory
from app.services.discovery.dsn import resolve_dsn


def ensure_mysql_database(dsn: str) -> str:
    """Create the database named in a MySQL DSN if it does not exist yet."""
    resolved = resolve_dsn(dsn)
    parsed = urlparse(resolved.replace("mysql+pymysql", "mysql"))
    database = unquote(parsed.path.lstrip("/").split("?", 1)[0])
    if not database:
        raise ValueError("MySQL target connection string must include a database name.")
    if len(database) > 64 or "\x00" in database:
        raise ValueError("MySQL database names must be at most 64 characters and cannot contain NUL.")

    connection = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )
    try:
        identifier = database.replace("`", "``")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{identifier}` CHARACTER SET utf8mb4")
        connection.commit()
    finally:
        connection.close()
    return database


def list_databases(source_type: str, dsn: str) -> list[str]:
    """List databases visible to the credentials in a MySQL or MongoDB DSN."""
    resolved = resolve_dsn(dsn)
    engine = source_type.lower()

    if engine == "mysql":
        parsed = urlparse(resolved.replace("mysql+pymysql", "mysql"))
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password or "",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                return sorted(next(iter(row.values())) for row in cursor.fetchall())
        finally:
            connection.close()

    if engine == "mongodb":
        client = MongoClient(resolved, serverSelectionTimeoutMS=5000)
        try:
            return sorted(client.list_database_names())
        finally:
            client.close()

    raise ValueError(f"Unsupported source_type: {source_type}")


def inspect_connection(source_type: str, dsn: str) -> dict[str, Any]:
    """Connect read-only and return the selected database and its tables/collections."""
    engine = source_type.lower()
    parsed_dsn = dsn.replace("mysql+pymysql", "mysql") if engine == "mysql" else dsn
    database = urlparse(parsed_dsn).path.lstrip("/").split("?", 1)[0]
    connector = ConnectorFactory.get_connector(engine, dsn)
    try:
        connector.connect()
        return {"database": database, "entities": connector.list_entities()}
    finally:
        connector.disconnect()