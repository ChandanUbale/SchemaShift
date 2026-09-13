"""
services/migration/writer_factory.py — Factory that returns the correct BaseWriter.

MVP writers: MySQLWriter, MongoWriter.
Stretch/future: add PostgreSQLWriter — no redesign required.
"""

from app.services.migration.base_writer import BaseWriter
from app.services.migration.mysql_writer import MySQLWriter
from app.services.migration.mongo_writer import MongoWriter
from app.config import settings


class WriterFactory:

    _registry: dict[str, type] = {
        "mysql": MySQLWriter,
        "mongodb": MongoWriter,
        # stretch: "postgresql": PostgreSQLWriter,
    }

    @classmethod
    def get_writer(cls, target_type: str, dsn: str, **kwargs) -> BaseWriter:
        """
        Return an instantiated (but not yet prepared) BaseWriter.

        Args:
            target_type: "mysql" | "mongodb"
            dsn:         target connection string or URI
            **kwargs:    extra args (e.g. db_name for MongoDB)

        Raises:
            ValueError if target_type is not registered.
        """
        writer_cls = cls._registry.get(target_type.lower())
        if writer_cls is None:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unsupported target_type '{target_type}'. "
                f"MVP supports: {supported}."
            )
        return writer_cls(dsn, **kwargs)

    @classmethod
    def supported_types(cls) -> list[str]:
        return list(cls._registry.keys())
