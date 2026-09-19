"""tests/test_validation.py — Unit tests for validation services."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.validation.count_validator import CountValidator


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
    raise NotImplementedError("TODO: ChecksumValidator.validate not yet implemented")


def test_checksum_validator_mismatched_rows():
    raise NotImplementedError("TODO: ChecksumValidator.validate not yet implemented")


def test_report_generator_produces_html():
    raise NotImplementedError("TODO: ReportGenerator.generate not yet implemented")


def test_risk_and_validation_are_separate():
    """Profiling risk score != migration validation result."""
    raise NotImplementedError("TODO: ReportGenerator.generate not yet implemented")
