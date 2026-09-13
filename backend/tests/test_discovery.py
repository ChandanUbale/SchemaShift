"""tests/test_discovery.py — Stubs for discovery service tests."""
import pytest

# TODO: import MySQLConnector, MongoDBConnector, ConnectorFactory

def test_connector_factory_returns_mysql():
    """ConnectorFactory.get_connector('mysql', dsn) returns a MySQLConnector."""
    raise NotImplementedError("TODO: implement test_connector_factory_returns_mysql")

def test_connector_factory_returns_mongodb():
    raise NotImplementedError("TODO: implement test_connector_factory_returns_mongodb")

def test_connector_factory_raises_for_unknown_type():
    raise NotImplementedError("TODO: implement test_connector_factory_raises_for_unknown_type")

def test_mysql_connector_list_entities():
    """Requires a running MySQL instance — mark as integration test."""
    pytest.skip("integration test — needs MySQL")

def test_mongodb_connector_list_entities():
    """Requires a running MongoDB instance — mark as integration test."""
    pytest.skip("integration test — needs MongoDB")
