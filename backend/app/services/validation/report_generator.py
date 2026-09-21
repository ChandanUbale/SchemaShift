"""
services/validation/report_generator.py — Generates the final HTML + JSON report.

Combines three stages (kept separate — do NOT fold into one number):
  1. Data quality BEFORE migration (profiling risk score)
  2. Migration execution stats
  3. Validation correctness AFTER migration
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
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
    .low {{ color: green; }} .medium {{ color: orange; }} .high {{ color: red; }}
    .passed {{ color: green; }} .failed {{ color: red; }}
  </style>
</head>
<body>
  <h1>SchemaShift Migration Report</h1>
  {body}
</body>
</html>
"""


class ReportGenerator:

    @staticmethod
    def generate(
        profiling_result: dict[str, Any],
        migration_stats: dict[str, Any],
        validation_result: dict[str, Any],
        output_path: str,
    ) -> dict[str, Any]:
        risk_label = str(profiling_result.get("risk_label") or "low")
        risk_score = float(profiling_result.get("risk_score") or 0.0)
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
            "before": {
                "heading": "Data quality before",
                "risk_label": risk_label,
                "risk_score": risk_score,
            },
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
            "note": "Profiling risk_label/risk_score are separate from validation match %. Do not average them.",
        }

        body = f"""
  <h2>1. Data quality before</h2>
  <p>Risk: <span class="{risk_label}">{risk_label}</span> (score {risk_score})</p>
  <p>This is source data quality. It is not a validation percentage.</p>
  <h2>2. Migration stats</h2>
  <table>
    <tr><th>Records migrated</th><td>{records}</td></tr>
    <tr><th>Batches total</th><td>{batches_total}</td></tr>
    <tr><th>Batches failed</th><td>{batches_failed}</td></tr>
    <tr><th>Duration (seconds)</th><td>{duration}</td></tr>
  </table>
  <h2>3. Validation after</h2>
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
