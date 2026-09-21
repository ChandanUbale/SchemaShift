"""
Batch migration executor — the only service allowed to call writer.write_batch().

Task 5: relational_to_document (MySQL rows → nested Mongo docs).
Task 6: document_to_relational (Mongo docs → MySQL rows, parents first).
"""

import math
from typing import Any

from app.jobs import JobStatus, get_job_status, update_progress
from app.jobs import _progress_cache
from app.services.migration.transformer import _SHOP_FLATTEN, _SHOP_TREE

MAX_RETRIES = 3
_CHILD_FETCH = 10_000_000  # demo scale: load child tables once


def _ensure_job(job_id: str) -> None:
    if get_job_status(job_id) is None:
        _progress_cache[job_id] = {
            "job_id": job_id,
            "job_type": "migration",
            "status": JobStatus.PENDING,
            "progress_pct": 0,
            "error": None,
        }


def _embed_tables(node: dict[str, Any]) -> list[str]:
    names = []
    for child in node.get("embed") or []:
        names.append(child["from_table"])
        names.extend(_embed_tables(child))
    return names


def _write_with_retry(writer, docs: list[dict], collection: str) -> tuple[bool, int, int, str | None]:
    if not docs:
        return True, 0, 0, None
    err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return True, writer.write_batch(docs, collection), attempt, None
        except Exception as exc:
            err = str(exc)
    return False, 0, MAX_RETRIES, err


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
        direction = plan.get("direction") or "relational_to_document"
        _ensure_job(job_id)
        pct = 0
        try:
            update_progress(job_id, 0, JobStatus.RUNNING)
            writer.prepare(plan)

            if direction == "document_to_relational":
                result = BatchExecutor._run_document_to_relational(
                    job_id, source_connector, writer, transformer, plan, batch_size
                )
            elif direction == "relational_to_document":
                result = BatchExecutor._run_relational_to_document(
                    job_id, source_connector, writer, transformer, plan, batch_size
                )
            else:
                raise ValueError(f"Unsupported direction: {direction}")

            writer.finalize()
            failed = result["batches_failed"]
            status = JobStatus.FAILED if failed else JobStatus.DONE
            err = f"{failed} batch(es) failed" if failed else None
            update_progress(job_id, 100, status, error=err)
            return result
        except Exception as exc:
            update_progress(job_id, pct, JobStatus.FAILED, error=str(exc))
            raise

    @staticmethod
    def _run_relational_to_document(
        job_id: str,
        source_connector,
        writer,
        transformer,
        plan: dict[str, Any],
        batch_size: int,
    ) -> dict[str, Any]:
        tree = plan.get("model_tree") or _SHOP_TREE
        root = tree.get("from_table") or tree.get("collection") or "customers"
        collection = tree.get("collection") or root
        children = {
            name: source_connector.fetch_batch(name, 0, _CHILD_FETCH)
            for name in _embed_tables(tree)
        }

        total = int(source_connector.estimate_counts().get(root, 0) or 0)
        batches_total = math.ceil(total / batch_size) if total else 0
        audit_log: list[dict] = []
        batches_failed = 0

        for i, offset in enumerate(range(0, total, batch_size)):
            parents = source_connector.fetch_batch(root, offset, batch_size)
            docs = transformer.transform_batch({root: parents, **children}, "relational_to_document")
            ok, written, attempts, err = _write_with_retry(writer, docs, collection)
            audit_log.append({
                "batch_index": i,
                "entity": collection,
                "rows": written if ok else len(docs),
                "ok": ok,
                "attempts": attempts,
                "error": err,
            })
            if not ok:
                batches_failed += 1
            pct = int((i + 1) / max(batches_total, 1) * 100)
            update_progress(job_id, pct, JobStatus.RUNNING)

        return {
            "audit_log": audit_log,
            "batches_total": batches_total,
            "batches_failed": batches_failed,
        }

    @staticmethod
    def _run_document_to_relational(
        job_id: str,
        source_connector,
        writer,
        transformer,
        plan: dict[str, Any],
        batch_size: int,
    ) -> dict[str, Any]:
        flatten = plan.get("flatten") or _SHOP_FLATTEN
        if not flatten:
            raise ValueError("document_to_relational requires plan['flatten']")
        collection = (
            (plan.get("model_tree") or {}).get("collection")
            or plan.get("collection")
            or flatten[0]["table"]
        )
        total = int(source_connector.estimate_counts().get(collection, 0) or 0)
        batches_total = math.ceil(total / batch_size) if total else 0
        audit_log: list[dict] = []
        batches_failed = 0

        for i, offset in enumerate(range(0, total, batch_size)):
            docs = source_connector.fetch_batch(collection, offset, batch_size)
            tables = transformer.transform_batch({collection: docs}, "document_to_relational")
            batch_ok = True
            for spec in flatten:
                table = spec["table"]
                rows = tables.get(table) or []
                if not batch_ok:
                    audit_log.append({
                        "batch_index": i,
                        "entity": table,
                        "rows": len(rows),
                        "ok": False,
                        "attempts": 0,
                        "error": "skipped after parent batch failure",
                    })
                    continue
                ok, written, attempts, err = _write_with_retry(writer, rows, table)
                audit_log.append({
                    "batch_index": i,
                    "entity": table,
                    "rows": written if ok else len(rows),
                    "ok": ok,
                    "attempts": attempts,
                    "error": err,
                })
                if not ok:
                    batch_ok = False
            if not batch_ok:
                batches_failed += 1
            pct = int((i + 1) / max(batches_total, 1) * 100)
            update_progress(job_id, pct, JobStatus.RUNNING)

        return {
            "audit_log": audit_log,
            "batches_total": batches_total,
            "batches_failed": batches_failed,
        }
