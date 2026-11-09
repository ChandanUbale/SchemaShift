"""
services/validation/report_generator.py — Generates the final HTML + JSON report.

Combines migration execution stats and post-migration validation.
"""

from pathlib import Path
from typing import Any


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SchemaShift Migration Report</title>
  <style>
    body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; }}
    h1 {{ color: #1a1a2e; }}
    .back {{ display: inline-block; margin-bottom: 1rem; color: #111827; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
    .passed {{ color: green; }} .failed {{ color: red; }}
  </style>
</head>
<body>
  <p><a class="back" href="javascript:history.back()">← Back to SchemaShift</a></p>
  <h1>SchemaShift Migration Report</h1>
  {body}
</body>
</html>
"""


class ReportGenerator:

    @staticmethod
    def generate(
        migration_stats: dict[str, Any],
        validation_result: dict[str, Any],
        output_path: str,
    ) -> dict[str, Any]:
        records = int(migration_stats.get("records_migrated") or 0)
        batches_total = int(migration_stats.get("batches_total") or 0)
        batches_failed = int(migration_stats.get("batches_failed") or 0)
        duration = float(migration_stats.get("duration_seconds") or 0.0)
        count_pct = validation_result.get("count_match_pct")
        aggregate_match = bool(validation_result.get("aggregate_match"))
        sample = validation_result.get("sample_matched") or "0/0"
        relationships = validation_result.get("relationship_checks") or "failed"
        rel_class = "passed" if relationships == "passed" else "failed"
        agg_text = "yes" if aggregate_match else "no"

        report = {
            "migration": {
                "heading": "Migration stats",
                "records_migrated": records,
                "batches_total": batches_total,
                "batches_failed": batches_failed,
                "duration_seconds": duration,
            },
            "after": {
                "heading": "Validation after",
                "count_match_pct": count_pct,
                "aggregate_match": aggregate_match,
                "sample_matched": sample,
                "relationship_checks": relationships,
            },
            "note": "Validation compares the migrated target against the selected source entities.",
        }

        body = f"""
  <h2>1. Migration stats</h2>
  <table>
    <tr><th>Records migrated</th><td>{records}</td></tr>
    <tr><th>Batches total</th><td>{batches_total}</td></tr>
    <tr><th>Batches failed</th><td>{batches_failed}</td></tr>
    <tr><th>Duration (seconds)</th><td>{duration}</td></tr>
  </table>
  <h2>2. Validation</h2>
  <table>
    <tr><th>Records matched</th><td>{count_pct}%</td></tr>
    <tr><th>Aggregate matched</th><td>{agg_text}</td></tr>
    <tr><th>Sample</th><td>{sample}</td></tr>
    <tr><th>Relationships</th><td class="{rel_class}">{relationships}</td></tr>
  </table>
"""
        html = HTML_TEMPLATE.format(body=body)
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
        report["html"] = html
        report["html_report_path"] = output_path
        return report
