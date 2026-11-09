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
    c = ConnectorFactory.get_connector("mongodb", "mongodb://localhost:27017/inventory")
    assert isinstance(c, MongoDBConnector)
    assert c.db_name == "inventory"


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


def test_mongodb_walk_detects_embedded_objects_and_arrays():
    types: dict[str, set[str]] = {}
    nulls: set[str] = set()
    seen: dict[str, int] = {}
    nesting: set[str] = set()
    walk_doc(
        {"profile": {"address": {"city": "Ottawa"}}, "events": [{"kind": "created"}]},
        "", types, nulls, seen, nesting,
    )
    assert nesting == {"profile", "profile.address", "events"}
    assert types["profile"] == {"object"}
    assert types["events"] == {"array"}


def test_mongo_relationship_graph_embeds_orders_and_items():
    from app.services.discovery.relationship_mapper import RelationshipMapper

    schema = {
        "source_type": "mongodb",
        "entities": [{
            "name": "customers",
            "columns": [
                {"name": "_id"}, {"name": "name"}, {"name": "orders"},
                {"name": "orders.total"}, {"name": "orders.items"},
                {"name": "orders.items.price"},
            ],
            "nesting": [
                {"path": "orders", "type": "array"},
                {"path": "orders.items", "type": "array"},
            ],
        }],
    }
    graph = RelationshipMapper.build_graph(schema, "mongodb")
    ids = {n["id"] for n in graph["nodes"]}
    assert ids == {"customers", "customers.orders", "customers.orders.items"}
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert nodes["customers"]["nested_children"] == ["orders"]
    assert nodes["customers.orders"]["nested_children"] == ["items"]
    assert nodes["customers.orders.items"]["nested_children"] == []
    assert {"source": "customers", "target": "customers.orders", "label": "array: orders", "relationship": "array", "path": "orders"} in graph["edges"]
    assert {"source": "customers.orders", "target": "customers.orders.items", "label": "array: items", "relationship": "array", "path": "orders.items"} in graph["edges"]


def test_mysql_relationship_graph_qualifies_external_database_foreign_key():
    from app.services.discovery.relationship_mapper import RelationshipMapper

    graph = RelationshipMapper.build_graph({
        "database": "orders_db",
        "entities": [{
            "name": "orders",
            "columns": [{"name": "customer_id"}],
            "foreign_keys": [{
                "column": "customer_id",
                "ref_database": "accounts_db",
                "ref_table": "customers",
                "ref_column": "id",
            }],
        }],
    }, "mysql")
    node_ids = {node["id"] for node in graph["nodes"]}
    assert node_ids == {"orders", "accounts_db.customers"}
    assert graph["edges"][0]["target"] == "accounts_db.customers"
    assert graph["nodes"][1]["external"] is True


def test_mysql_connector_list_entities():
    pytest.skip("integration test — needs MySQL")


def test_mongodb_connector_list_entities():
    pytest.skip("integration test — needs MongoDB")
