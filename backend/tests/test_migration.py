"""tests/test_migration.py — Stubs for dry runner, transformer, writer, and batch executor tests."""
import pytest

def test_dry_runner_does_not_call_writer():
    """DryRunner.run must not invoke any writer.write_batch method."""
    raise NotImplementedError("TODO")

def test_transformer_relational_to_document():
    raise NotImplementedError("TODO")

def test_transformer_document_to_relational():
    raise NotImplementedError("TODO")

def test_writer_factory_returns_mysql_writer():
    raise NotImplementedError("TODO")

def test_writer_factory_returns_mongo_writer():
    raise NotImplementedError("TODO")

def test_batch_executor_retries_on_failure():
    """BatchExecutor retries a failed batch up to MAX_RETRIES times."""
    raise NotImplementedError("TODO")
