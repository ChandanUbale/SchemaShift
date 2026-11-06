"""
Batch migration executor — the only service allowed to call writer.write_batch().

Task 5: relational_to_document (MySQL rows → nested Mongo docs).
Task 6: document_to_relational (Mongo docs → MySQL rows, parents first).
Generic: every discovered collection/table, plus copy when engines match.
"""

import math
from collections import OrderedDict
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
        return True, 0, 1, None
    err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return True, writer.write_batch(docs, collection), attempt, None
        except Exception as exc:
            err = str(exc)
    return False, 0, MAX_RETRIES, err


def _flatten_groups(flatten: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    current_root = "customers"
    for spec in flatten:
        path = spec.get("from_path") or "$"
        collection = spec.get("collection")
        if collection:
            groups.setdefault(collection, []).append(spec)
            if path in ("$", ""):
                current_root = collection
            continue
        if path in ("$", ""):
            current_root = spec.get("table") or current_root
            groups.setdefault(current_root, []).append(spec)
            continue
        groups.setdefault(current_root, []).append(spec)
    if not groups:
        groups["customers"] = list(flatten)
    return list(groups.items())


def _audit(batch_index: int, entity: str, rows: int, ok: bool, attempts: int, error: str | None) -> dict:
    return {
        "batch_index": batch_index,
        "entity": entity,
        "rows": rows,
        "ok": ok,
        "attempts": attempts,
        "error": error,
    }


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
            elif direction == "copy":
                result = BatchExecutor._run_copy(
                    job_id, source_connector, writer, plan, batch_size
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
        trees = list(plan.get("model_trees") or [])
        if not trees:
            trees = [plan.get("model_tree") or _SHOP_TREE]
        counts = source_connector.estimate_counts() or {}
        audit_log: list[dict] = []
        batches_failed = 0
        batches_total = 0
        done = 0

        for tree in trees:
            root = tree.get("from_table") or tree.get("collection") or "customers"
            collection = tree.get("collection") or root
            children = {
                name: source_connector.fetch_batch(name, 0, _CHILD_FETCH)
                for name in _embed_tables(tree)
            }
            total = int(counts.get(root, 0) or 0)
            tree_batches = math.ceil(total / batch_size) if total else 0
            batches_total += tree_batches
            if total == 0:
                audit_log.append(_audit(0, collection, 0, True, 1, None))
                continue
            scoped = TransformerWithTree(transformer, tree) if not tree.get("embed") else transformer
            for i, offset in enumerate(range(0, total, batch_size)):
                parents = source_connector.fetch_batch(root, offset, batch_size)
                if tree.get("embed"):
                    docs = transformer.transform_batch(
                        {root: parents, **children}, "relational_to_document"
                    )
                else:
                    docs = scoped.transform_batch({root: parents}, "relational_to_document")
                ok, written, attempts, err = _write_with_retry(writer, docs, collection)
                audit_log.append(_audit(i, collection, written if ok else len(docs), ok, attempts, err))
                if not ok:
                    batches_failed += 1
                done += 1
                update_progress(job_id, int(done / max(batches_total, 1) * 100), JobStatus.RUNNING)

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
        groups = _flatten_groups(flatten)
        counts = source_connector.estimate_counts() or {}
        audit_log: list[dict] = []
        batches_failed = 0
        batches_total = 0
        done = 0

        for collection, specs in groups:
            total = int(counts.get(collection, 0) or 0)
            tree_batches = math.ceil(total / batch_size) if total else 0
            batches_total += tree_batches
            if total == 0:
                for spec in specs:
                    audit_log.append(_audit(0, spec["table"], 0, True, 1, None))
                continue
            for i, offset in enumerate(range(0, total, batch_size)):
                docs = source_connector.fetch_batch(collection, offset, batch_size)
                tables = transformer.transform_batch({collection: docs}, "document_to_relational")
                batch_ok = True
                for spec in specs:
                    table = spec["table"]
                    rows = tables.get(table) or []
                    if not batch_ok:
                        audit_log.append(_audit(
                            i, table, len(rows), False, 0, "skipped after parent batch failure"
                        ))
                        continue
                    ok, written, attempts, err = _write_with_retry(writer, rows, table)
                    audit_log.append(_audit(i, table, written if ok else len(rows), ok, attempts, err))
                    if not ok:
                        batch_ok = False
                if not batch_ok:
                    batches_failed += 1
                done += 1
                update_progress(job_id, int(done / max(batches_total, 1) * 100), JobStatus.RUNNING)

        return {
            "audit_log": audit_log,
            "batches_total": batches_total,
            "batches_failed": batches_failed,
        }

    @staticmethod
    def _run_copy(
        job_id: str,
        source_connector,
        writer,
        plan: dict[str, Any],
        batch_size: int,
    ) -> dict[str, Any]:
        entities = list(plan.get("entities") or [])
        if not entities:
            entities = list((source_connector.estimate_counts() or {}).keys())
        counts = source_connector.estimate_counts() or {}
        audit_log: list[dict] = []
        batches_failed = 0
        batches_total = 0
        done = 0
        for entity in entities:
            total = int(counts.get(entity, 0) or 0)
            tree_batches = math.ceil(total / batch_size) if total else 0
            batches_total += tree_batches
            if total == 0:
                audit_log.append(_audit(0, entity, 0, True, 1, None))
                continue
            for i, offset in enumerate(range(0, total, batch_size)):
                rows = source_connector.fetch_batch(entity, offset, batch_size)
                ok, written, attempts, err = _write_with_retry(writer, rows, entity)
                audit_log.append(_audit(i, entity, written if ok else len(rows), ok, attempts, err))
                if not ok:
                    batches_failed += 1
                done += 1
                update_progress(job_id, int(done / max(batches_total, 1) * 100), JobStatus.RUNNING)
        return {
            "audit_log": audit_log,
            "batches_total": batches_total,
            "batches_failed": batches_failed,
        }


class TransformerWithTree:
    """Apply a 1:1 table→collection tree without mutating the shared transformer plan."""

    def __init__(self, transformer, tree: dict[str, Any]) -> None:
        self._inner = transformer
        self._tree = tree

    def transform_batch(self, tables: dict[str, list[dict]], direction: str):
        original = getattr(self._inner, "plan", {}) or {}
        try:
            self._inner.plan = {**original, "model_tree": self._tree}
            return self._inner.transform_batch(tables, direction)
        finally:
            self._inner.plan = original
