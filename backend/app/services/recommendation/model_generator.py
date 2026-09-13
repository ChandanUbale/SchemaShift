"""
services/recommendation/model_generator.py — Generates the target data model.

Given a recommendation (relational or document), produces:
  - MySQL DDL (CREATE TABLE statements with AUTO_INCREMENT PKs, FK constraints)
    OR
  - Nested MongoDB document tree (JSON shape with embedded arrays)

Does NOT emit Parquet. Does NOT start a migration.
"""

from typing import Any


class ModelGenerator:

    @staticmethod
    def generate(
        recommendation: dict[str, Any],
        source_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate the target model from the recommendation and source schema.

        Args:
            recommendation: output of ScoringEngine.score()
            source_schema:  output of connector.describe_entity() calls, keyed by table name

        Returns:
            {
                "target_type":   "mysql" | "mongodb",
                "generated_ddl": str | None,   # MySQL DDL if relational
                "model_tree":    dict | None,  # MongoDB nested shape if document
            }

        TODO:
        - if relational: call _generate_mysql_ddl(source_schema)
        - if document:   call _generate_mongo_tree(source_schema)
        """
        raise NotImplementedError("TODO: implement ModelGenerator.generate")

    @staticmethod
    def _generate_mysql_ddl(source_schema: dict[str, Any]) -> str:
        """
        Emit CREATE TABLE ... statements.
        Use AUTO_INCREMENT for serial PKs (not SERIAL — MySQL syntax).
        Include FK constraints.
        TODO: iterate tables, build DDL strings.
        """
        raise NotImplementedError("TODO: implement _generate_mysql_ddl")

    @staticmethod
    def _generate_mongo_tree(source_schema: dict[str, Any]) -> dict[str, Any]:
        """
        Emit a nested document shape showing how relational tables embed into documents.
        e.g. Customer { orders: [ { items: [...] } ] }
        TODO: follow FK relationships to build nesting hierarchy.
        """
        raise NotImplementedError("TODO: implement _generate_mongo_tree")
