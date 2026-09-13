"""
services/migration/transformer.py — Bidirectional relational ↔ document data transformer.

Converts rows/documents between the source shape and the approved target model.
Works on individual rows in memory — does not access any database.

Directions:
  - relational_to_document: MySQL rows → nested MongoDB documents
  - document_to_relational: MongoDB documents → MySQL rows (flat + junction tables)
"""

from typing import Any


class Transformer:

    def __init__(self, plan: dict[str, Any]) -> None:
        """
        plan: the approved recommendation / model plan from model_generator.
        Defines how source fields map to target fields/nesting.
        """
        self.plan = plan

    def transform_row(self, row: dict[str, Any], direction: str) -> dict[str, Any]:
        """
        Transform a single row/document.

        Args:
            row:       source row or document
            direction: "relational_to_document" | "document_to_relational"

        Returns: transformed target row/document

        TODO: implement field mapping, type coercions, nesting/flattening.
        """
        if direction == "relational_to_document":
            return self._relational_to_document(row)
        elif direction == "document_to_relational":
            return self._document_to_relational(row)
        else:
            raise ValueError(f"Unknown transform direction: {direction}")

    def _relational_to_document(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        Map flat relational row(s) into a nested document.
        e.g. CUSTOMER + ORDER + ORDER_ITEM rows → Customer { orders: [ { items: [...] } ] }
        TODO: implement using plan's model_tree to guide nesting.
        """
        raise NotImplementedError("TODO: implement _relational_to_document")

    def _document_to_relational(self, doc: dict[str, Any]) -> dict[str, list[dict]]:
        """
        Flatten a nested document into one dict per target table.
        Returns {"customers": [...], "orders": [...], "order_items": [...]}
        TODO: implement using plan's generated_ddl table list to guide flattening.
        """
        raise NotImplementedError("TODO: implement _document_to_relational")
