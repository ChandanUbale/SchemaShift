"""
services/migration/dry_runner.py — Dry run: detect issues WITHOUT writing to the target.

Hard rule: dry_runner NEVER calls BaseWriter.write_batch or any write method.
It reads a sample from the source, runs the transformer in memory, and returns issues.
"""

from typing import Any


class DryRunner:

    @staticmethod
    def run(
        source_rows: list[dict[str, Any]],
        transformer,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Transform a sample of source rows and collect issues.
        No rows are written to any target.

        Args:
            source_rows: sample fetched via connector.fetch_sample()
            transformer: Transformer instance (relational→document or vice versa)
            plan:        recommendation / model plan dict

        Returns:
            list of issue dicts:
            [{"table_or_collection": str, "issue_type": str, "row_count": int, "description": str}]

        Typical issues:
            - invalid_date:   date field value fails parsing
            - orphan_fk:      FK value missing in parent table sample
            - duplicate_pk:   same PK appears in the sample
            - type_mismatch:  source type cannot map to target type without data loss
            - missing_field:  required target field has no source equivalent

        TODO: iterate source_rows, call transformer.transform_row(),
              catch transformation errors, accumulate issues, return list.
        """
        raise NotImplementedError("TODO: implement DryRunner.run")
