"""
Bidirectional relational ↔ document transformer (in memory, no DB I/O).
"""

from collections import defaultdict
from typing import Any

_SHOP_TREE = {
    "from_table": "customers",
    "collection": "customers",
    "fields": ["id", "name", "email", "created_at"],
    "embed": [
        {
            "from_table": "orders",
            "as": "orders",
            "join": {"parent": "id", "child": "customer_id"},
            "fields": ["id", "order_date", "total", "status"],
            "embed": [
                {
                    "from_table": "order_items",
                    "as": "items",
                    "join": {"parent": "id", "child": "order_id"},
                    "fields": ["product_id", "product_name", "quantity", "price"],
                }
            ],
        }
    ],
}

_SHOP_FLATTEN = [
    {"table": "customers", "from_path": "$", "fields": ["id", "name", "email", "created_at"]},
    {"table": "orders", "from_path": "$.orders", "parent_fk": "customer_id",
     "fields": ["id", "order_date", "total", "status"]},
    {"table": "order_items", "from_path": "$.orders.items", "parent_fk": "order_id",
     "fields": ["product_id", "product_name", "quantity", "price"]},
]


def _pick(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    if not fields:
        return {
            k: v for k, v in row.items()
            if k != "_id" and not isinstance(v, (list, dict))
        }
    return {f: row.get(f) for f in fields}


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
    """Walk dotted path; return (node, parent) pairs at the leaf."""
    parts = [p for p in dotted.replace("$.", "").replace("$", "").split(".") if p]
    stack: list[tuple[dict[str, Any], dict[str, Any] | None]] = [(doc, None)]
    for part in parts:
        nxt: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        for node, _parent in stack:
            child = node.get(part) if isinstance(node, dict) else None
            if isinstance(child, list):
                nxt.extend((item, node) for item in child if isinstance(item, dict))
            elif isinstance(child, dict):
                nxt.append((child, node))
        stack = nxt
    return stack


def _flatten_doc(doc: dict[str, Any], flatten: list[dict[str, Any]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {spec["table"]: [] for spec in flatten}
    for spec in flatten:
        path = spec.get("from_path") or "$"
        fields = spec.get("fields") or []
        table = spec["table"]
        if path in ("$", ""):
            row = _pick(doc, fields)
            if not fields or "id" in fields:
                rid = _row_id(doc)
                if rid is not None:
                    row["id"] = rid
            out[table].append(row)
            continue
        dotted = path.replace("$.", "").lstrip("$")
        for node, parent in _nodes_at(doc, dotted):
            row = _pick(node, fields)
            if not fields or "id" in fields:
                rid = _row_id(node)
                if rid is not None:
                    row["id"] = rid
            fk = spec.get("parent_fk")
            if fk and parent is not None:
                row[fk] = _row_id(parent)
            out[table].append(row)
    return out


class Transformer:

    def __init__(self, plan: dict[str, Any] | None = None) -> None:
        self.plan = plan or {}

    def _tree(self) -> dict[str, Any]:
        return self.plan.get("model_tree") or _SHOP_TREE

    def _flatten_spec(self) -> list[dict[str, Any]]:
        return self.plan.get("flatten") or _SHOP_FLATTEN

    def transform_row(self, row: dict[str, Any], direction: str) -> Any:
        if direction == "relational_to_document":
            return self._relational_to_document(row)
        if direction == "document_to_relational":
            return self._document_to_relational(row)
        raise ValueError(f"Unknown transform direction: {direction}")

    def transform_batch(self, tables: dict[str, list[dict]], direction: str) -> Any:
        if direction == "relational_to_document":
            tree = self._tree()
            root = tree.get("from_table") or tree.get("collection") or "customers"
            return _nest(tables.get(root, []), tree, tables)
        if direction == "document_to_relational":
            merged: dict[str, list[dict]] = defaultdict(list)
            for docs in tables.values():
                for doc in docs or []:
                    if not isinstance(doc, dict):
                        continue
                    for table, rows in self._document_to_relational(doc).items():
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
