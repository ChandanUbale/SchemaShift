"""tests/test_validation.py — Unit tests for validation services."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.validation.count_validator import CountValidator
from app.services.validation.checksum_validator import ChecksumValidator
from app.services.validation.relationship_validator import RelationshipValidator
from app.services.validation.report_generator import ReportGenerator


def test_count_validator_perfect_match():
    """Equal counts → 100% match."""
    src = {"customers": 4, "orders": 10}
    tgt = {"customers": 4, "orders": 10}
    result = CountValidator.validate(src, tgt)
    assert result["total_source"] == 14
    assert result["total_target"] == 14
    assert result["match_pct"] == 100.0
    assert result["per_entity"]["customers"]["match"] is True
    assert result["per_entity"]["orders"]["match"] is True


def test_count_validator_partial_match():
    """Unequal counts → correct percentage and per-entity mismatch."""
    src = {"customers": 4, "orders": 10}
    tgt = {"customers": 4, "orders": 8}
    result = CountValidator.validate(src, tgt)
    assert result["total_source"] == 14
    assert result["total_target"] == 12
    assert result["match_pct"] == round(100.0 * 12 / 14, 1)
    assert result["per_entity"]["customers"]["match"] is True
    assert result["per_entity"]["orders"]["match"] is False


def test_count_validator_empty_both():
    """Both empty → 100% match, not divide-by-zero."""
    result = CountValidator.validate({}, {})
    assert result["match_pct"] == 100.0
    assert result["total_source"] == 0
    assert result["total_target"] == 0


def test_count_validator_source_empty_target_not():
    """Source empty, target has rows → 0% match."""
    result = CountValidator.validate({}, {"customers": 5})
    assert result["match_pct"] == 0.0


def test_checksum_validator_identical_rows():
    src = [{"id": 1, "name": "Alice", "email": "a@x.com"}]
    tgt = [{"id": 1, "name": "Alice", "email": "a@x.com"}]
    result = ChecksumValidator.validate(src, tgt)
    assert result["checked"] == 1
    assert result["matched"] == 1
    assert result["summary"] == "1/1"
    assert result["mismatched_pks"] == []
    nested = [{"id": 1, "name": "Alice", "email": "a@x.com", "orders": [{"id": 10}]}]
    flat = [{"id": 1, "name": "Alice", "email": "a@x.com"}]
    roundtrip = ChecksumValidator.validate(nested, flat)
    assert roundtrip["matched"] == 0


def test_checksum_validator_normalizes_sql_numeric_and_boolean_values():
    source = [{"id": "doc-1", "enabled": True, "amount": 2}]
    target = [{"id": "doc-1", "enabled": 1, "amount": 2.0}]
    result = ChecksumValidator.validate(source, target)
    assert result["summary"] == "1/1"


def test_checksum_validator_parses_known_json_fields_before_hashing():
    source = [{"id": "doc-1", "payload": '{"z": 1, "a": 2}'}]
    target = [{"id": "doc-1", "payload": '{"a": 2, "z": 1}'}]
    result = ChecksumValidator.validate(source, target, json_fields={"payload"})
    assert result["summary"] == "1/1"


def test_checksum_validator_mismatched_rows():
    src = [{"id": 1, "name": "Alice", "email": "a@x.com"}]
    tgt = [{"id": 1, "name": "Alicia", "email": "a@x.com"}]
    result = ChecksumValidator.validate(src, tgt)
    assert result["checked"] == 1
    assert result["matched"] == 0
    assert result["summary"] == "0/1"
    assert result["mismatched_pks"] == [1]


def test_checksum_validator_matches_different_source_and_target_id_fields():
    source = [{"_id": "doc-1", "name": "Rates", "categoryId": "abc"}]
    target = [{"id": "doc-1", "name": "Rates", "categoryId": "abc"}]
    result = ChecksumValidator.validate(
        source,
        target,
        source_pk_field="_id",
        target_pk_field="id",
    )
    assert result["summary"] == "1/1"
    assert result["mismatched_pks"] == []


def test_checksum_validator_counts_source_keys_missing_from_target():
    result = ChecksumValidator.validate(
        [{"_id": "doc-1", "name": "A"}, {"_id": "doc-2", "name": "B"}],
        [{"id": "doc-1", "name": "A"}],
        source_pk_field="_id",
        target_pk_field="id",
    )
    assert result["checked"] == 2
    assert result["matched"] == 1
    assert result["summary"] == "1/2"
    assert result["missing_in_target"] == 1
    assert result["mismatched_pks"] == ["doc-2"]


class _RelConn:
    def __init__(self, tables):
        self.tables = tables

    def fetch_sample(self, name, n):
        return list(self.tables.get(name, []))[:n]

    def fetch_batch(self, name, offset, limit):
        return list(self.tables.get(name, []))[offset:offset + limit]

    def fetch_by_ids(self, name, field, values):
        wanted = set(values)
        return [row for row in self.tables.get(name, []) if row.get(field) in wanted]


def test_aggregate_validator_compares_target_rows_by_source_ids():
    from app.services.validation.aggregate_validator import AggregateValidator

    source = _RelConn({"orders": [{"id": 1, "amount": 10}, {"id": 2, "amount": 20}]})
    target = _RelConn({"orders_docs": [{"id": 2, "amount": 20}, {"id": 1, "amount": 10}, {"id": 3, "amount": 999}]})
    result = AggregateValidator.validate(
        source,
        target,
        {"orders": ["amount"]},
        entity_mapping={"orders": "orders_docs"},
        source_primary_keys={"orders": "id"},
        target_primary_keys={"orders": "id"},
    )
    assert result["match"] is True
    assert result["details"]["orders"]["amount"]["source_sum"] == 30
    assert result["details"]["orders"]["amount"]["target_sum"] == 30
    assert result["details"]["orders"]["_sample"]["target_rows_with_matching_ids"] == 2


def test_validation_mapping_aligns_mongo_collections_to_root_mysql_tables():
    from app.models.connection import Connection
    from app.routers.validation import _validation_mapping

    source = Connection(source_type="mongodb")
    source.schema_json = {
        "source_type": "mongodb",
        "entities": [{
            "name": "mapping_categories",
            "columns": [
                {"name": "_id", "data_type": "objectid"},
                {"name": "name", "data_type": "string"},
                {"name": "sources", "data_type": "array"},
                {"name": "sources.system", "data_type": "string"},
            ],
            "nesting": [{"path": "sources", "type": "array"}],
        }],
    }
    selected, target_names, source_keys, target_keys, field_mappings, plan = _validation_mapping(source)

    assert [entity["name"] for entity in selected["entities"]] == ["mapping_categories"]
    assert target_names == {"mapping_categories": "mapping_categories"}
    assert source_keys == {"mapping_categories": "_id"}
    assert target_keys == {"mapping_categories": "id"}
    assert field_mappings == {"mapping_categories": {}}
    assert plan["direction"] == "document_to_relational"


def test_checksum_validation_uses_transformed_root_projection_for_mongo():
    from app.routers.validation import _validate_entity_samples
    from app.services.migration.plan_builder import build_plan

    schema = {
        "source_type": "mongodb",
        "entities": [{
            "name": "widgets",
            "columns": [
                {"name": "_id", "data_type": "objectid"},
                {"name": "name", "data_type": "string"},
                {"name": "enabled", "data_type": "boolean"},
                {"name": "meta", "data_type": "object"},
                {"name": "items", "data_type": "array"},
                {"name": "items.value", "data_type": "string"},
            ],
            "nesting": [{"path": "items", "type": "array"}],
        }],
    }
    plan = build_plan(schema, "mongodb", "mysql")

    class _MongoSamples:
        def fetch_sample(self, _name, _size):
            return [{"_id": "doc-1", "name": "Widget", "enabled": True, "meta": {"z": 1, "a": 2}, "items": [{"value": "part"}]}]

    target = _RelConn({"widgets": [{"id": "doc-1", "name": "Widget", "enabled": 1, "meta": '{"a": 2, "z": 1}'}]})
    result = _validate_entity_samples(
        _MongoSamples(),
        target,
        ["widgets"],
        {"widgets": "widgets"},
        {"widgets": "_id"},
        {"widgets": "id"},
        10,
        plan,
    )

    assert result["summary"] == "1/1"
    assert result["per_entity"]["widgets"]["missing_in_target"] == 0


def test_relationship_validator_mysql_orphans_fail():
    conn = _RelConn({
        "customers": [{"id": 1}],
        "orders": [{"id": 10, "customer_id": 1}, {"id": 11, "customer_id": 999}],
        "order_items": [{"id": 100, "order_id": 10}],
    })
    result = RelationshipValidator.validate_fk_integrity(conn, fk_map=[
        {"child_table": "orders", "fk_field": "customer_id", "parent_table": "customers", "pk_field": "id"},
        {"child_table": "order_items", "fk_field": "order_id", "parent_table": "orders", "pk_field": "id"},
    ])
    assert result["passed"] is False
    orphans = {item["relationship"]: item["orphan_count"] for item in result["details"]}
    assert any(count == 1 for count in orphans.values())


def test_relationship_validator_without_discovered_relationships_reports_none():
    conn = _RelConn({"arbitrary_collection": [{"id": 1}]})
    result = RelationshipValidator.validate_fk_integrity(conn, fk_map=[])
    assert result["passed"] is True
    assert result["details"] == []


def test_report_generator_produces_html(tmp_path):
    path = tmp_path / "report.html"
    report = ReportGenerator.generate(
        {"records_migrated": 10, "batches_total": 2, "batches_failed": 0, "duration_seconds": 1.5},
        {"count_match_pct": 99.0, "aggregate_match": True, "sample_matched": "10/10", "relationship_checks": "passed"},
        str(path),
    )
    html = path.read_text(encoding="utf-8")
    assert "Data quality before" not in html
    assert "Validation after" in html
    assert "99.0" in html
    assert "10/10" in html
    assert report["html_report_path"] == str(path)
    assert report["after"]["count_match_pct"] == 99.0


def test_report_summarizes_migration_and_validation(tmp_path):
    report = ReportGenerator.generate(
        {"records_migrated": 100, "batches_total": 1, "batches_failed": 0, "duration_seconds": 3},
        {"count_match_pct": 99.8, "aggregate_match": True, "sample_matched": "100/100", "relationship_checks": "passed"},
        str(tmp_path / "sep.html"),
    )
    assert report["after"]["count_match_pct"] == 99.8
    assert report["migration"]["records_migrated"] == 100
