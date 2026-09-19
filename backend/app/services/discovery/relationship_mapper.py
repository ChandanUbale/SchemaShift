"""
services/discovery/relationship_mapper.py — Builds a graph of FK / reference relationships.

For MySQL: parses INFORMATION_SCHEMA FK metadata from describe_entity() output.
For MongoDB: infers embedded vs reference patterns from the sampled schema.
Output is used by SchemaGraph.tsx (react-flow) for visualization.
"""

from typing import Any

def _graph_mysql(schema: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    edges = []
    
    for entity in schema.get("entities", []):
        table_name = entity.get("name")
        columns = [col.get("name") for col in entity.get("columns", [])]
        
        nodes.append({
            "id": table_name,
            "label": table_name,
            "columns": columns
        })
        
        for fk in entity.get("foreign_keys", []):
            child_column = fk.get("column")
            ref_table = fk.get("ref_table")
            ref_column = fk.get("ref_column")
            
            edges.append({
                "source": table_name,
                "target": ref_table,
                "label": f"{child_column} → {ref_column}"
            })
            
    return {"nodes": nodes, "edges": edges}

def _graph_mongo(schema: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("TODO: implement mongo graph (Dev 2)")

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
        """
        if source_type == "mysql":
            return _graph_mysql(schema)
        if source_type == "mongodb":
            return _graph_mongo(schema)
        
        raise ValueError(f"Unknown source type: {source_type}")
