"""tests/test_discovery.py — Connector factory + Mongo schema inference."""
import pytest
from bson import ObjectId

from app.services.discovery.connector_factory import ConnectorFactory
from app.services.discovery.mongodb_connector import MongoDBConnector, walk_doc
from app.services.discovery.mysql_connector import MySQLConnector


def test_connector_factory_returns_mysql():
    c = ConnectorFactory.get_connector("mysql", "mysql+pymysql://root:root@localhost:3306/demo")
    assert isinstance(c, MySQLConnector)


def test_connector_factory_returns_mongodb():
    c = ConnectorFactory.get_connector("mongodb", "mongodb://localhost:27017/demo_source")
    assert isinstance(c, MongoDBConnector)
    assert c.db_name == "demo_source"


def test_connector_factory_raises_for_unknown_type():
    with pytest.raises(ValueError, match="Unsupported source_type"):
        ConnectorFactory.get_connector("postgres", "postgresql://localhost/db")


def test_mongodb_walk_detects_nested_orders_and_items():
    types: dict[str, set[str]] = {}
    nulls: set[str] = set()
    seen: dict[str, int] = {}
    nesting: set[str] = set()
    walk_doc(
        {
            "_id": ObjectId(),
            "name": "Alice",
            "orders": [
                {
                    "total": 100.5,
                    "items": [{"product_name": "Widget A", "price": 25.0}],
                }
            ],
        },
        "",
        types,
        nulls,
        seen,
        nesting,
    )
    assert "orders" in nesting
    assert "orders.items" in nesting
    assert types["name"] == {"string"}
    assert types["_id"] == {"objectid"}
    assert "orders.total" in types
    assert "orders.items.price" in types


def test_mysql_connector_list_entities():
    pytest.skip("integration test — needs MySQL")


def test_mongodb_connector_list_entities():
    pytest.skip("integration test — needs MongoDB")
