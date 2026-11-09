"""
Bidirectional relational ↔ document transformer (in memory, no DB I/O).
"""

import json
import uuid
from collections import defaultdict
from typing import Any

def _sql_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return value


def _pick(
    row: dict[str, Any],
    fields: list[str],
    json_fields: list[str] | None = None,
    rename: dict[str, str] | None = None,
    include_unknown_fields: bool = False,
    exclude_fields: list[str] | None = None,
) -> dict[str, Any]:
    json_fields = set(json_fields or [])
    rename = rename or {}
    excluded = set(exclude_fields or [])
    known_fields = set(fields)
    if not fields:
        items = [(key, value) for key, value in row.items() if key != "_id"]
    else:
        items = []
        for field in fields:
            if field == "id" and field not in row:
                continue
            items.append((field, row.get(field)))
    unknown_fields = set()
    if include_unknown_fields:
        for key, value in row.items():
            if key in known_fields or key in excluded or key in {"_id", "id"}:
                continue
            items.append((key, value))
            unknown_fields.add(key)
    out: dict[str, Any] = {}
    for field, value in items:
        key = rename.get(field, field)
        if field in unknown_fields:
            out[key] = None if value is None else json.dumps(value, default=str)
        elif field in json_fields or isinstance(value, (dict, list)):
            out[key] = None if value is None else _sql_value(value)
        else:
            out[key] = value
    return out


def _row_id(row: dict[str, Any]) -> Any:
    if row.get("id") is not None:
        return row["id"]
    if row.get("_id") is not None:
        return str(row["_id"])
    return None


def _group(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[row.get(key)].append(row)
    return out


def _nest(parents: list[dict[str, Any]], node: dict[str, Any], tables: dict[str, list[dict]]) -> list[dict[str, Any]]:
    docs = []
    child_indexes = [
        (child, _group(tables.get(child["from_table"], []), child["join"]["child"]))
        for child in node.get("embed") or []
    ]
    for parent in parents:
        doc = _pick(parent, node.get("fields") or [])
        for child, index in child_indexes:
            kids = index.get(parent.get(child["join"]["parent"]), [])
            doc[child["as"]] = _nest(kids, child, tables)
        docs.append(doc)
    return docs


def _nodes_at(doc: dict[str, Any], dotted: str) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Walk a dotted path and return each item with its nearest array-row parent."""
    parts = [p for p in dotted.replace("$.", "").replace("$", "").split(".") if p]
    stack: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = [(doc, doc, doc)]
    for part in parts:
        nxt: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = []
        for node, nearest_array_row, parent_for_node in stack:
            child = node.get(part) if isinstance(node, dict) else None
            if isinstance(child, list):
                nxt.extend((item, item, nearest_array_row) for item in child if isinstance(item, dict))
            elif isinstance(child, dict):
                nxt.append((child, nearest_array_row, parent_for_node))
        stack = nxt
    return [(node, parent) for node, _nearest, parent in stack]


def _flatten_doc(doc: dict[str, Any], flatten: list[dict[str, Any]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {spec["table"]: [] for spec in flatten}
    row_ids: dict[int, Any] = {}
    for spec in flatten:
        path = spec.get("from_path") or "$"
        fields = spec.get("fields") or []
        table = spec["table"]
        json_fields = spec.get("json_fields") or []
        rename = spec.get("rename") or {}
        include_unknown_fields = bool(spec.get("include_unknown_fields"))
        exclude_fields = spec.get("exclude_fields") or []
        if path in ("$", ""):
            row = _pick(doc, fields, json_fields, rename, include_unknown_fields, exclude_fields)
            if spec.get("emit_id") or not fields or "id" in fields:
                rid = _row_id(doc) or uuid.uuid4().hex
                row[rename.get("id", "id")] = rid
                row_ids[id(doc)] = rid
            out[table].append(row)
            continue
        dotted = path.replace("$.", "").lstrip("$")
        for node, parent in _nodes_at(doc, dotted):
            row = _pick(node, fields, json_fields, rename, include_unknown_fields, exclude_fields)
            if spec.get("emit_id") or not fields or "id" in fields:
                rid = _row_id(node) or uuid.uuid4().hex
                row[rename.get("id", "id")] = rid
                row_ids[id(node)] = rid
            fk = spec.get("parent_fk")
            if fk and parent is not None:
                row[fk] = row_ids.get(id(parent)) or _row_id(parent)
            out[table].append(row)
    return out


def _specs_for_collection(flatten: list[dict[str, Any]], collection: str) -> list[dict[str, Any]]:
    matched = [spec for spec in flatten if spec.get("collection") == collection]
    if matched:
        return matched
    roots = [
        spec for spec in flatten
        if (spec.get("from_path") or "$") in ("$", "") and spec.get("table") == collection
    ]
    if roots:
        children = [
            spec for spec in flatten
            if (spec.get("from_path") or "$") not in ("$", "") and not spec.get("collection")
        ]
        return roots + children
    tagged = {spec.get("collection") for spec in flatten if spec.get("collection")}
    if not tagged:
        return flatten
    return []


class Transformer:

    def __init__(self, plan: dict[str, Any] | None = None) -> None:
        self.plan = plan or {}

    def _tree(self) -> dict[str, Any]:
        tree = self.plan.get("model_tree")
        if not tree:
            raise ValueError("Migration plan is missing its document model tree.")
        return tree

    def _flatten_spec(self) -> list[dict[str, Any]]:
        flatten = self.plan.get("flatten")
        if not flatten:
            raise ValueError("Migration plan is missing its relational mapping.")
        return flatten

    def transform_row(self, row: dict[str, Any], direction: str) -> Any:
        if direction == "relational_to_document":
            return self._relational_to_document(row)
        if direction == "document_to_relational":
            return self._document_to_relational(row)
        raise ValueError(f"Unknown transform direction: {direction}")

    def transform_batch(self, tables: dict[str, list[dict]], direction: str) -> Any:
        if direction == "relational_to_document":
            tree = self._tree()
            root = tree.get("from_table") or tree.get("collection")
            if not root:
                raise ValueError("Document model tree is missing its source entity.")
            return _nest(tables.get(root, []), tree, tables)
        if direction == "document_to_relational":
            flatten = self._flatten_spec()
            merged: dict[str, list[dict]] = defaultdict(list)
            for collection, docs in tables.items():
                specs = _specs_for_collection(flatten, collection)
                if not specs:
                    continue
                for doc in docs or []:
                    if not isinstance(doc, dict):
                        continue
                    for table, rows in _flatten_doc(doc, specs).items():
                        merged[table].extend(rows)
            return dict(merged)
        raise ValueError(f"Unknown transform direction: {direction}")

    def _relational_to_document(self, row: dict[str, Any]) -> dict[str, Any]:
        tree = self._tree()
        doc = _pick(row, tree.get("fields") or list(row.keys()))
        for child in tree.get("embed") or []:
            doc[child["as"]] = []
        return doc

    def _document_to_relational(self, doc: dict[str, Any]) -> dict[str, list[dict]]:
        return _flatten_doc(doc, self._flatten_spec())
