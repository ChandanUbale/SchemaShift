"""
services/migration/batch_executor.py — Batch migration executor.

Responsibilities:
  - Read batches from the source connector
  - Transform each batch via Transformer
  - Write each batch via BaseWriter
  - Retry failed batches a fixed number of times
  - Append to the audit log (success/fail per batch)
  - Push progress to jobs.update_progress() for SSE
  - Cleanup/reset action (delegated to writer.cleanup())

Hard write boundary: this is the ONLY service allowed to call writer.write_batch().
"""

from typing import Any

from app.jobs import update_progress, JobStatus

MAX_RETRIES = 3


class BatchExecutor:

    @staticmethod
    def run(
        job_id: str,
        source_connector,
        writer,
        transformer,
        plan: dict[str, Any],
        batch_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Execute the full migration for a single approved job.

        Steps per entity (table / collection):
          1. connector.estimate_counts() → batches_total
          2. For each batch:
               a. connector.fetch_batch(entity, offset, batch_size)
               b. transformer.transform_row(row, direction) for each row
               c. writer.write_batch(transformed_rows, entity)
               d. Retry up to MAX_RETRIES on failure; log outcome
               e. update_progress(job_id, pct)
          3. writer.finalize()

        Returns an audit_log dict summarising batch outcomes.

        TODO: implement the loop, retry logic, progress updates, and audit log.
        """
        update_progress(job_id, 0, JobStatus.RUNNING)
        audit_log: list[dict] = []

        # TODO: implement batch loop

        update_progress(job_id, 100, JobStatus.DONE)
        return {"audit_log": audit_log}
