"""
services/discovery/connector_factory.py — Factory that returns the correct BaseConnector.

MVP connectors: MySQLConnector, MongoDBConnector.
Stretch/future: add PostgreSQLConnector, SQLServerConnector — no redesign required.
"""

from app.services.discovery.base_connector import BaseConnector
from app.services.discovery.mysql_connector import MySQLConnector
from app.services.discovery.mongodb_connector import MongoDBConnector


class ConnectorFactory:
    """
    Selects and instantiates the correct connector based on source_type.
    Usage:
        connector = ConnectorFactory.get_connector("mysql", dsn)
        connector.connect()
    """

    _registry: dict[str, type] = {
        "mysql": MySQLConnector,
        "mongodb": MongoDBConnector,
        # stretch: "postgresql": PostgreSQLConnector,
        # future:  "sqlserver": SQLServerConnector,
    }

    @classmethod
    def get_connector(cls, source_type: str, dsn: str, **kwargs) -> BaseConnector:
        """
        Return an instantiated (but not yet connected) BaseConnector.

        Args:
            source_type: "mysql" | "mongodb"
            dsn:         connection string or URI
            **kwargs:    extra args forwarded to the connector (e.g. db_name for MongoDB)

        Raises:
            ValueError if source_type is not registered.
        """
        connector_cls = cls._registry.get(source_type.lower())
        if connector_cls is None:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unsupported source_type '{source_type}'. "
                f"MVP supports: {supported}."
            )
        # MongoDB needs db_name separately; pass through kwargs
        return connector_cls(dsn, **kwargs)

    @classmethod
    def supported_types(cls) -> list[str]:
        """Return the list of registered source types."""
        return list(cls._registry.keys())
