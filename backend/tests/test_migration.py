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
    raise NotImplementedError("TODO: Transformer is Lavanya's task")

def test_transformer_document_to_relational():
    raise NotImplementedError("TODO: Transformer is Lavanya's task")

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
