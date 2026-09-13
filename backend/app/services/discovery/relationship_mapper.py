"""
services/discovery/relationship_mapper.py — Builds a graph of FK / reference relationships.

For MySQL: parses INFORMATION_SCHEMA FK metadata from describe_entity() output.
For MongoDB: infers embedded vs reference patterns from the sampled schema.
Output is used by SchemaGraph.tsx (react-flow) for visualization.
"""

from typing import Any


class RelationshipMapper:

    @staticmethod
    def build_graph(schema: dict[str, Any], source_type: str) -> dict[str, Any]:
        """
        Convert raw schema metadata into a graph structure suitable for react-flow.

        Args:
            schema:      Output of connector.describe_entity() calls (keyed by table/collection).
            source_type: "mysql" | "mongodb"

        Returns:
            {
                "nodes": [{"id": str, "label": str, "columns": [...]}],
                "edges": [{"source": str, "target": str, "label": str}]
            }

        TODO:
        - MySQL: extract foreign_keys from each table's describe_entity output
        - MongoDB: detect reference patterns (_id fields pointing to other collections)
        """
        raise NotImplementedError("TODO: implement RelationshipMapper.build_graph")
