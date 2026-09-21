"""
Bidirectional relational ↔ document transformer (in memory, no DB I/O).

Task 4: relational_to_document via transform_batch + model_tree.
Task 6 (later): document_to_relational.
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


def _pick(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    if not fields:
        return dict(row)
    return {f: row.get(f) for f in fields}


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


class Transformer:

    def __init__(self, plan: dict[str, Any] | None = None) -> None:
        self.plan = plan or {}

    def _tree(self) -> dict[str, Any]:
        return self.plan.get("model_tree") or _SHOP_TREE

    def transform_row(self, row: dict[str, Any], direction: str) -> dict[str, Any]:
        if direction == "relational_to_document":
            return self._relational_to_document(row)
        if direction == "document_to_relational":
            return self._document_to_relational(row)
        raise ValueError(f"Unknown transform direction: {direction}")

    def transform_batch(self, tables: dict[str, list[dict]], direction: str) -> list[dict[str, Any]]:
        """Nest grouped relational tables into documents. Used by the batch executor."""
        if direction != "relational_to_document":
            raise ValueError(f"transform_batch does not support {direction}")
        tree = self._tree()
        root = tree.get("from_table") or tree.get("collection") or "customers"
        return _nest(tables.get(root, []), tree, tables)

    def _relational_to_document(self, row: dict[str, Any]) -> dict[str, Any]:
        """Single row cannot carry children; nest empty arrays from the plan."""
        tree = self._tree()
        doc = _pick(row, tree.get("fields") or list(row.keys()))
        for child in tree.get("embed") or []:
            doc[child["as"]] = []
        return doc

    def _document_to_relational(self, doc: dict[str, Any]) -> dict[str, list[dict]]:
        raise NotImplementedError("TODO: implement _document_to_relational")
