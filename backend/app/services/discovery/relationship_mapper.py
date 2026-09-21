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

def _direct_fields(columns: list[dict], prefix: str) -> list[str]:
    """Names one level under prefix (empty prefix = top-level / no dots)."""
    names = []
    for col in columns:
        name = col.get("name") or ""
        if prefix:
            if not name.startswith(prefix + ".") or "." in name[len(prefix) + 1:]:
                continue
            names.append(name[len(prefix) + 1:])
        elif "." not in name:
            names.append(name)
    return names


def _graph_mongo(schema: dict[str, Any]) -> dict[str, Any]:
    """Embed graph: collection → nested arrays (customers → orders → items)."""
    nodes, edges = [], []
    for entity in schema.get("entities", []):
        col = entity.get("name")
        if not col:
            continue
        columns = entity.get("columns", [])
        nest_paths = [n.get("path") for n in entity.get("nesting", []) if n.get("path")]
        nodes.append({"id": col, "label": col, "columns": _direct_fields(columns, "")})
        for path in nest_paths:
            node_id = f"{col}.{path}"
            parent = col if "." not in path else f"{col}.{path.rsplit('.', 1)[0]}"
            nodes.append({
                "id": node_id,
                "label": path.rsplit(".", 1)[-1],
                "columns": _direct_fields(columns, path),
            })
            edges.append({
                "source": parent,
                "target": node_id,
                "label": f"embeds {path.rsplit('.', 1)[-1]}",
            })
    return {"nodes": nodes, "edges": edges}

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
