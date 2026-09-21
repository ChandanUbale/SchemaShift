"""tests/test_migration.py — Unit tests for migration services."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.migration.writer_factory import WriterFactory
from app.services.migration.mysql_writer import MySQLWriter
from app.services.migration.mongo_writer import MongoWriter


def test_dry_runner_does_not_call_writer():
    pytest.skip("Task 7 — dry runner")

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

class _FakeConnector:
    def __init__(self, customers, orders=None, items=None):
        self.customers = customers
        self.orders = orders or []
        self.items = items or []

    def estimate_counts(self):
        return {"customers": len(self.customers), "orders": len(self.orders), "order_items": len(self.items)}

    def fetch_batch(self, name, offset, limit):
        rows = {"customers": self.customers, "orders": self.orders, "order_items": self.items}.get(name, [])
        return rows[offset:offset + limit]


class _FakeWriter:
    def __init__(self, fail_first=0):
        self.prepared = False
        self.finalized = False
        self.writes = []
        self._fail_left = fail_first

    def prepare(self, plan):
        self.prepared = True

    def write_batch(self, rows, entity_name):
        if self._fail_left > 0:
            self._fail_left -= 1
            raise RuntimeError("write failed")
        self.writes.append((entity_name, list(rows)))
        return len(rows)

    def finalize(self):
        self.finalized = True


def test_batch_executor_retries_on_failure():
    from app.jobs import JobStatus, get_job_status
    from app.services.migration.batch_executor import MAX_RETRIES, BatchExecutor
    from app.services.migration.transformer import Transformer

    writer = _FakeWriter(fail_first=2)
    result = BatchExecutor.run(
        "job-retry",
        _FakeConnector([{"id": 1, "name": "A", "email": "a@x.com", "created_at": "2023-01-01"}]),
        writer,
        Transformer({}),
        {"direction": "relational_to_document"},
        batch_size=1000,
    )
    assert writer.prepared and writer.finalized
    assert result["batches_total"] == 1
    assert result["batches_failed"] == 0
    assert result["audit_log"][0]["ok"] is True
    assert result["audit_log"][0]["attempts"] == 3
    assert MAX_RETRIES == 3
    assert get_job_status("job-retry")["status"] == JobStatus.DONE


def test_batch_executor_records_failed_batch_after_retries():
    from app.jobs import JobStatus, get_job_status
    from app.services.migration.batch_executor import BatchExecutor
    from app.services.migration.transformer import Transformer

    writer = _FakeWriter(fail_first=5)
    result = BatchExecutor.run(
        "job-fail",
        _FakeConnector([{"id": 1, "name": "A", "email": "a@x.com", "created_at": "2023-01-01"}]),
        writer,
        Transformer({}),
        {"direction": "relational_to_document"},
        batch_size=1000,
    )
    assert result["batches_failed"] == 1
    assert result["audit_log"][0]["ok"] is False
    assert get_job_status("job-fail")["status"] == JobStatus.FAILED
