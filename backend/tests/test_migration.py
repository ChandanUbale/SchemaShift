"""tests/test_migration.py — Unit tests for migration services."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.migration.writer_factory import WriterFactory
from app.services.migration.mysql_writer import MySQLWriter
from app.services.migration.mongo_writer import MongoWriter


def test_dry_runner_does_not_call_writer():
    """DryRunner.run must not invoke any writer.write_batch method."""
    raise NotImplementedError("TODO: DryRunner.run not yet implemented")

def test_transformer_relational_to_document():
    from app.services.migration.transformer import Transformer

    tables = {
        "customers": [{"id": 1, "name": "Alice", "email": "a@x.com", "created_at": "2023-01-01", "extra": "drop"}],
        "orders": [
            {"id": 10, "customer_id": 1, "order_date": "2023-02-01", "total": 100.5, "status": "paid"},
            {"id": 11, "customer_id": 1, "order_date": "2023-02-02", "total": 20.0, "status": "paid"},
        ],
        "order_items": [
            {"id": 100, "order_id": 10, "product_id": 1, "product_name": "A", "quantity": 2, "price": 25.0},
            {"id": 101, "order_id": 10, "product_id": 2, "product_name": "B", "quantity": 1, "price": 50.5},
            {"id": 102, "order_id": 11, "product_id": 1, "product_name": "A", "quantity": 1, "price": 20.0},
        ],
    }
    docs = Transformer({}).transform_batch(tables, "relational_to_document")
    assert len(docs) == 1
    assert docs[0]["name"] == "Alice"
    assert "extra" not in docs[0]
    assert len(docs[0]["orders"]) == 2
    assert len(docs[0]["orders"][0]["items"]) == 2
    assert len(docs[0]["orders"][1]["items"]) == 1
    lone = Transformer({}).transform_row({"id": 1, "name": "Alice"}, "relational_to_document")
    assert lone["orders"] == []


def test_transformer_document_to_relational():
    pytest.skip("Task 6 — document_to_relational")

def test_writer_factory_returns_mysql_writer():
    """WriterFactory.get_writer('mysql', dsn) returns a MySQLWriter instance."""
    writer = WriterFactory.get_writer("mysql", "mysql+pymysql://user:pass@localhost:3306/testdb")
    assert isinstance(writer, MySQLWriter)

def test_writer_factory_returns_mongo_writer():
    """WriterFactory.get_writer('mongodb', dsn) returns a MongoWriter instance."""
    writer = WriterFactory.get_writer("mongodb", "mongodb://localhost:27017/testdb", db_name="testdb")
    assert isinstance(writer, MongoWriter)

def test_writer_factory_raises_for_unknown_type():
    """WriterFactory.get_writer raises ValueError for unsupported target types."""
    with pytest.raises(ValueError, match="Unsupported target_type"):
        WriterFactory.get_writer("postgresql", "postgresql://localhost/testdb")

def test_batch_executor_retries_on_failure():
    """BatchExecutor retries a failed batch up to MAX_RETRIES times."""
    raise NotImplementedError("TODO: batch loop not yet implemented")
