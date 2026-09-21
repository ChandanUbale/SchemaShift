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
    assert roundtrip["matched"] == 1


def test_checksum_validator_mismatched_rows():
    src = [{"id": 1, "name": "Alice", "email": "a@x.com"}]
    tgt = [{"id": 1, "name": "Alicia", "email": "a@x.com"}]
    result = ChecksumValidator.validate(src, tgt)
    assert result["checked"] == 1
    assert result["matched"] == 0
    assert result["summary"] == "0/1"
    assert result["mismatched_pks"] == [1]


class _RelConn:
    def __init__(self, tables):
        self.tables = tables

    def fetch_sample(self, name, n):
        return list(self.tables.get(name, []))[:n]


def test_relationship_validator_mysql_orphans_fail():
    conn = _RelConn({
        "customers": [{"id": 1}],
        "orders": [{"id": 10, "customer_id": 1}, {"id": 11, "customer_id": 999}],
        "order_items": [{"id": 100, "order_id": 10}],
    })
    result = RelationshipValidator.validate_fk_integrity(conn)
    assert result["passed"] is False
    orphans = {item["relationship"]: item["orphan_count"] for item in result["details"]}
    assert any(count == 1 for count in orphans.values())


def test_relationship_validator_mongo_embed_passes():
    conn = _RelConn({
        "customers": [{"id": 1, "orders": [{"id": 10, "items": []}]}],
    })
    result = RelationshipValidator.validate_fk_integrity(conn, fk_map=[])
    assert result["passed"] is True
    assert result["details"][0]["status"] == "passed"


def test_report_generator_produces_html(tmp_path):
    path = tmp_path / "report.html"
    report = ReportGenerator.generate(
        {"risk_label": "high", "risk_score": 12.5},
        {"records_migrated": 10, "batches_total": 2, "batches_failed": 0, "duration_seconds": 1.5},
        {"count_match_pct": 99.0, "aggregate_match": True, "sample_matched": "10/10", "relationship_checks": "passed"},
        str(path),
    )
    html = path.read_text(encoding="utf-8")
    assert "Data quality before" in html
    assert "high" in html
    assert "12.5" in html
    assert "Validation after" in html
    assert "99.0" in html
    assert "10/10" in html
    assert report["html_report_path"] == str(path)
    assert report["before"]["risk_label"] == "high"
    assert report["after"]["count_match_pct"] == 99.0


def test_risk_and_validation_are_separate(tmp_path):
    """Profiling risk score != migration validation result."""
    report = ReportGenerator.generate(
        {"risk_label": "high", "risk_score": 80.0},
        {"records_migrated": 100, "batches_total": 1, "batches_failed": 0, "duration_seconds": 3},
        {"count_match_pct": 99.8, "aggregate_match": True, "sample_matched": "100/100", "relationship_checks": "passed"},
        str(tmp_path / "sep.html"),
    )
    assert report["before"]["risk_score"] == 80.0
    assert report["after"]["count_match_pct"] == 99.8
    assert report["before"]["risk_score"] != report["after"]["count_match_pct"]
    assert "separate" in report["note"].lower()
