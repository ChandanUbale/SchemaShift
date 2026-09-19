"""tests/test_profiling.py — Unit tests for profiling services."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.profiling.column_profiler import ColumnProfiler
from app.services.profiling.quality_checker import QualityChecker
from app.services.profiling.volume_estimator import VolumeEstimator


def test_column_profiler_null_rate():
    """ColumnProfiler.profile_column computes correct null_rate."""
    values = [1, None, 3, None, 5]  # 2 nulls out of 5 = 0.4
    result = ColumnProfiler.profile_column("price", values)
    assert result["column"] == "price"
    assert result["null_rate"] == 0.4
    assert result["distinct_count"] == 3
    assert result["duplicate_count"] == 0


def test_quality_checker_risk_label():
    """QualityChecker.label_risk returns correct label for boundary values."""
    assert QualityChecker.label_risk(0.0) == "low"
    assert QualityChecker.label_risk(0.99) == "low"
    assert QualityChecker.label_risk(1.0) == "medium"
    assert QualityChecker.label_risk(4.99) == "medium"
    assert QualityChecker.label_risk(5.0) == "high"
    assert QualityChecker.label_risk(100.0) == "high"


def test_quality_checker_risk_score_zero_total():
    """risk_score returns 0.0 when total == 0."""
    score = QualityChecker.compute_risk_score(invalid=0, orphans=0, duplicates=0, total=0)
    assert score == 0.0


def test_volume_estimator_estimates_bytes():
    """VolumeEstimator correctly computes total rows and MB from counts."""
    counts = {"customers": 100, "orders": 400}
    result = VolumeEstimator.estimate_source_volume(counts, avg_row_bytes=512)
    assert result["total_rows"] == 500
    assert result["tables"]["customers"]["estimated_bytes"] == 100 * 512
    assert result["tables"]["orders"]["estimated_bytes"] == 400 * 512
    expected_mb = round((500 * 512) / 1_000_000, 2)
    assert result["total_estimated_mb"] == expected_mb
