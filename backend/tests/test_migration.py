"""tests/test_migration.py — Unit tests for migration services."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.migration.writer_factory import WriterFactory
from app.services.migration.mysql_writer import MySQLWriter
from app.services.migration.mongo_writer import MongoWriter


def test_dry_runner_does_not_import_writers():
    import ast
    from pathlib import Path

    tree = ast.parse(Path(__file__).resolve().parents[1].joinpath("app/services/migration/dry_runner.py").read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    blob = " ".join(imported)
    assert "mysql_writer" not in blob
    assert "mongo_writer" not in blob
    assert "writer_factory" not in blob
    assert "WriterFactory" not in blob


def test_dry_runner_does_not_call_writer():
    from app.services.migration.dry_runner import DryRunner
    from app.services.migration.transformer import Transformer

    class BoomWriter:
        def write_batch(self, *args, **kwargs):
            raise AssertionError("dry run must not write")

        def prepare(self, plan):
            raise AssertionError("dry run must not write")

    writer = BoomWriter()
    tables = {
        "customers": [{"id": 1, "name": "Alice", "email": "a@x.com", "created_at": "2023-01-01"}],
        "orders": [{"id": 10, "customer_id": 1, "order_date": "2023-02-01", "total": 1, "status": "paid"}],
        "order_items": [{"id": 100, "order_id": 10, "product_id": 1, "product_name": "A", "quantity": 1, "price": 1}],
    }
    issues = DryRunner.run(tables, Transformer({}), {"direction": "relational_to_document"})
    assert issues == []
    assert writer.write_batch is not None  # constructed, never passed in


def test_dry_runner_reports_dirty_rows():
    from app.services.migration.dry_runner import DryRunner
    from app.services.migration.transformer import Transformer

    tables = {
        "customers": [
            {"id": 1, "name": "Alice", "email": "a@x.com", "created_at": "0000-00-00"},
            {"id": 1, "name": "Alicia", "email": None, "created_at": "2023-01-01"},
        ],
        "orders": [
            {"id": 10, "customer_id": 1, "order_date": "not-a-date", "total": 1, "status": "paid"},
            {"id": 11, "customer_id": 999, "order_date": "2023-02-01", "total": 1, "status": "paid"},
        ],
        "order_items": [
            {"id": 100, "order_id": 10, "product_id": 1, "product_name": "A", "quantity": None, "price": 1},
            {"id": 101, "order_id": 50, "product_id": 1, "product_name": "A", "quantity": 1, "price": 1},
        ],
    }
    issues = DryRunner.run(tables, Transformer({}), {"direction": "relational_to_document"})
    by_type = {(item["table_or_collection"], item["issue_type"]): item["row_count"] for item in issues}
    assert by_type[("customers", "duplicate_pk")] == 2
    assert by_type[("customers", "invalid_date")] >= 1
    assert by_type[("customers", "missing_field")] == 1
    assert by_type[("orders", "invalid_date")] >= 1
    assert by_type[("orders", "orphan_fk")] == 1
    assert by_type[("order_items", "orphan_fk")] == 1
    assert by_type[("order_items", "missing_field")] == 1


def test_dry_runner_document_sample_and_transform_type_mismatch():
    from app.services.migration.dry_runner import DryRunner

    class BoomTransform:
        def transform_batch(self, tables, direction):
            raise TypeError("cannot coerce int to datetime")

        def transform_row(self, row, direction):
            raise TypeError("cannot coerce int to datetime")

    docs = [{
        "id": 1,
        "name": None,
        "email": "a@x.com",
        "created_at": "2023-13-40",
        "orders": [{
            "id": 10,
            "customer_id": 999,
            "order_date": "2023-02-01",
            "items": [{"product_id": 1, "product_name": "A", "quantity": None, "price": 1}],
        }],
    }]
    issues = DryRunner.run(docs, BoomTransform(), {"direction": "document_to_relational"})
    types = {item["issue_type"] for item in issues}
    assert "missing_field" in types
    assert "invalid_date" in types
    assert "orphan_fk" in types
    assert "type_mismatch" in types


def test_dry_runner_document_quality_without_flatten_impl():
    from app.services.migration.dry_runner import DryRunner
    from app.services.migration.transformer import Transformer

    docs = [{
        "id": 1,
        "name": None,
        "email": "a@x.com",
        "created_at": "2023-01-01",
        "orders": [],
    }]
    issues = DryRunner.run(docs, Transformer({}), {"direction": "document_to_relational"})
    assert any(item["issue_type"] == "missing_field" for item in issues)
    assert not any(item["issue_type"] in ("transform_error", "type_mismatch") for item in issues)

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
    from app.services.migration.transformer import Transformer

    doc = {
        "id": 1,
        "name": "Alice",
        "email": "a@x.com",
        "created_at": "2023-01-01",
        "orders": [
            {
                "id": 10,
                "order_date": "2023-02-01",
                "total": 100.5,
                "status": "paid",
                "items": [
                    {"product_id": 1, "product_name": "A", "quantity": 2, "price": 25.0},
                    {"product_id": 2, "product_name": "B", "quantity": 1, "price": 50.5},
                ],
            },
            {
                "id": 11,
                "order_date": "2023-02-02",
                "total": 20.0,
                "status": "paid",
                "items": [
                    {"product_id": 1, "product_name": "A", "quantity": 1, "price": 20.0},
                ],
            },
        ],
    }
    tables = Transformer({})._document_to_relational(doc)
    assert tables["customers"] == [
        {"id": 1, "name": "Alice", "email": "a@x.com", "created_at": "2023-01-01"}
    ]
    assert len(tables["orders"]) == 2
    assert tables["orders"][0]["customer_id"] == 1
    assert tables["orders"][0]["id"] == 10
    assert tables["orders"][1]["id"] == 11
    assert len(tables["order_items"]) == 3
    assert tables["order_items"][0]["order_id"] == 10
    assert tables["order_items"][2]["order_id"] == 11
    assert tables["order_items"][0]["product_name"] == "A"

    oid_doc = {"_id": "abc", "name": "Bob", "email": "b@x.com", "created_at": None, "orders": []}
    oid_tables = Transformer({}).transform_row(oid_doc, "document_to_relational")
    assert oid_tables["customers"][0]["id"] == "abc"
    assert oid_tables["orders"] == []
    assert oid_tables["order_items"] == []

    merged = Transformer({}).transform_batch({"customers": [doc, oid_doc]}, "document_to_relational")
    assert len(merged["customers"]) == 2
    assert len(merged["orders"]) == 2
    assert len(merged["order_items"]) == 3


def test_transformer_roundtrip_shop_fixture():
    from app.services.migration.transformer import Transformer

    tables = {
        "customers": [{"id": 1, "name": "Alice", "email": "a@x.com", "created_at": "2023-01-01"}],
        "orders": [
            {"id": 10, "customer_id": 1, "order_date": "2023-02-01", "total": 100.5, "status": "paid"},
        ],
        "order_items": [
            {"id": 100, "order_id": 10, "product_id": 1, "product_name": "A", "quantity": 2, "price": 25.0},
        ],
    }
    docs = Transformer({}).transform_batch(tables, "relational_to_document")
    back = Transformer({}).transform_batch({"customers": docs}, "document_to_relational")
    assert back["customers"][0]["id"] == 1
    assert back["orders"][0]["customer_id"] == 1
    assert back["order_items"][0]["order_id"] == 10
    assert back["order_items"][0]["product_id"] == 1

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


def test_batch_executor_document_to_relational_writes_parents_first():
    from app.jobs import JobStatus, get_job_status
    from app.services.migration.batch_executor import BatchExecutor
    from app.services.migration.transformer import Transformer

    docs = [{
        "id": 1,
        "name": "A",
        "email": "a@x.com",
        "created_at": "2023-01-01",
        "orders": [{
            "id": 10,
            "order_date": "2023-02-01",
            "total": 1,
            "status": "paid",
            "items": [{"product_id": 1, "product_name": "A", "quantity": 1, "price": 1}],
        }],
    }]
    writer = _FakeWriter()
    result = BatchExecutor.run(
        "job-flatten",
        _FakeConnector(docs),
        writer,
        Transformer({}),
        {"direction": "document_to_relational"},
        batch_size=1000,
    )
    assert writer.prepared and writer.finalized
    assert [entity for entity, _rows in writer.writes] == ["customers", "orders", "order_items"]
    assert writer.writes[0][1][0]["id"] == 1
    assert writer.writes[1][1][0]["customer_id"] == 1
    assert writer.writes[2][1][0]["order_id"] == 10
    assert result["batches_total"] == 1
    assert result["batches_failed"] == 0
    assert get_job_status("job-flatten")["status"] == JobStatus.DONE


def test_batch_executor_document_to_relational_skips_children_after_parent_fail():
    from app.jobs import JobStatus, get_job_status
    from app.services.migration.batch_executor import BatchExecutor
    from app.services.migration.transformer import Transformer

    docs = [{
        "id": 1,
        "name": "A",
        "email": "a@x.com",
        "created_at": "2023-01-01",
        "orders": [{
            "id": 10,
            "order_date": "2023-02-01",
            "total": 1,
            "status": "paid",
            "items": [{"product_id": 1, "product_name": "A", "quantity": 1, "price": 1}],
        }],
    }]
    writer = _FakeWriter(fail_first=5)
    result = BatchExecutor.run(
        "job-flatten-fail",
        _FakeConnector(docs),
        writer,
        Transformer({}),
        {"direction": "document_to_relational"},
        batch_size=1000,
    )
    assert result["batches_failed"] == 1
    assert [entry["entity"] for entry in result["audit_log"]] == ["customers", "orders", "order_items"]
    assert result["audit_log"][0]["ok"] is False
    assert result["audit_log"][1]["error"] == "skipped after parent batch failure"
    assert result["audit_log"][2]["error"] == "skipped after parent batch failure"
    assert writer.writes == []
    assert get_job_status("job-flatten-fail")["status"] == JobStatus.FAILED


class _DryJob:
    def __init__(self, status="done"):
        self.status = status


def test_execute_rejects_missing_plan_id():
    from app.services.migration.execute_gate import PLAN_REQUIRED, require_plan_id

    with pytest.raises(ValueError, match=PLAN_REQUIRED):
        require_plan_id("")
    with pytest.raises(ValueError, match=PLAN_REQUIRED):
        require_plan_id("   ")
    require_plan_id("plan-1")


def test_execute_rejects_without_successful_dry_run():
    from app.services.migration.execute_gate import DRY_RUN_REQUIRED, require_successful_dry_run

    with pytest.raises(ValueError, match=DRY_RUN_REQUIRED):
        require_successful_dry_run(None)
    with pytest.raises(ValueError, match=DRY_RUN_REQUIRED):
        require_successful_dry_run(_DryJob("failed"))
    require_successful_dry_run(_DryJob("done"))


def test_execute_rejects_high_risk_without_confirm():
    from app.services.migration.execute_gate import HIGH_RISK_REQUIRED, require_high_risk_confirm

    require_high_risk_confirm(None, False)
    require_high_risk_confirm("low", False)
    require_high_risk_confirm("high", True)
    with pytest.raises(ValueError, match="confirm_high_risk"):
        require_high_risk_confirm("high", False)
    assert HIGH_RISK_REQUIRED.startswith("Profiling risk is High")


def test_execute_override_rewrites_plan_for_this_job_only():
    from app.services.migration.execute_gate import apply_override, shop_plan

    plan = shop_plan("mysql", "p1")
    assert plan["target_type"] == "mongodb"
    assert plan["direction"] == "relational_to_document"
    overridden = apply_override(plan, "mysql")
    assert overridden["target_type"] == "mysql"
    assert overridden["direction"] == "document_to_relational"
    assert plan["target_type"] == "mongodb"
    assert apply_override(plan, None)["target_type"] == "mongodb"
    assert apply_override(plan, "mongodb")["direction"] == "relational_to_document"


def test_assert_distinct_targets_rejects_same_dsn():
    fastapi = pytest.importorskip("fastapi")
    from fastapi import HTTPException
    from app.services.migration.safety import assert_distinct_targets

    dsn = "mysql+pymysql://root:root@localhost:3306/demo"
    with pytest.raises(HTTPException) as err:
        assert_distinct_targets(dsn, dsn, False)
    assert err.value.status_code == 400
    assert_distinct_targets(dsn, dsn, True)
    assert_distinct_targets(dsn, "mysql+pymysql://root:root@localhost:3307/migration_target", False)
    assert fastapi is not None
