"""
services/validation/report_generator.py — Generates the final HTML + JSON report.

Combines three stages (kept separate — do NOT fold into one number):
  1. Data quality BEFORE migration (profiling risk score)
  2. Migration execution stats
  3. Validation correctness AFTER migration
"""

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
        """
        Build the final report and write it to output_path as HTML.
        Returns the report as a JSON-serialisable dict.

        TODO:
        - Render HTML sections for each stage using HTML_TEMPLATE
        - Write to output_path
        - Return the full report dict
        """
        raise NotImplementedError("TODO: implement ReportGenerator.generate")
