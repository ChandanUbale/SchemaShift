"""
services/discovery/relationship_mapper.py — Builds a graph of FK / reference relationships.

For MySQL: parses INFORMATION_SCHEMA FK metadata from describe_entity() output.
For MongoDB: infers embedded vs reference patterns from the sampled schema.
Output is used by SchemaGraph.tsx (react-flow) for visualization.
"""

from typing import Any

def _graph_mysql(schema: dict[str, Any]) -> dict[str, Any]:
    nodes_by_id = {}
    edges = []
    current_database = schema.get("database")
    
    for entity in schema.get("entities", []):
        table_name = entity.get("name")
        columns = [col.get("name") for col in entity.get("columns", [])]
        
        nodes_by_id[table_name] = {
            "id": table_name,
            "label": table_name,
            "columns": columns
        }
        
        for fk in entity.get("foreign_keys", []):
            child_column = fk.get("column")
            ref_table = fk.get("ref_table")
            ref_column = fk.get("ref_column")
            ref_database = fk.get("ref_database")
            ref_node_id = ref_table if not ref_database or ref_database == current_database else f"{ref_database}.{ref_table}"
            if ref_node_id not in nodes_by_id:
                nodes_by_id[ref_node_id] = {
                    "id": ref_node_id,
                    "label": ref_node_id,
                    "columns": [],
                    "external": True,
                }
            
            edges.append({
                "source": table_name,
                "target": ref_node_id,
                "label": f"{child_column} → {ref_node_id}.{ref_column}",
                "relationship": "foreign key",
                "source_column": child_column,
                "target_column": ref_column,
            })
            
    return {"nodes": list(nodes_by_id.values()), "edges": edges}

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
    """Build a graph of discovered collections and nested paths."""
    nodes, edges = [], []
    for entity in schema.get("entities", []):
        col = entity.get("name")
        if not col:
            continue
        columns = entity.get("columns", [])
        nest_paths = {
            n.get("path"): n.get("type", "object")
            for n in entity.get("nesting", []) if n.get("path")
        }

        def direct_nested(parent: str) -> list[str]:
            prefix = f"{parent}." if parent else ""
            return [
                path[len(prefix):]
                for path in nest_paths
                if path.startswith(prefix) and path[len(prefix):] and "." not in path[len(prefix):]
            ]

        nodes.append({
            "id": col,
            "label": col,
            "columns": _direct_fields(columns, ""),
            "nested_children": direct_nested(""),
        })
        for path, kind in sorted(nest_paths.items(), key=lambda item: (item[0].count("."), item[0])):
            node_id = f"{col}.{path}"
            parent = col if "." not in path else f"{col}.{path.rsplit('.', 1)[0]}"
            nodes.append({
                "id": node_id,
                "label": path.rsplit(".", 1)[-1],
                "columns": _direct_fields(columns, path),
                "nested_children": direct_nested(path),
            })
            edges.append({
                "source": parent,
                "target": node_id,
                "label": f"{kind}: {path.rsplit('.', 1)[-1]}",
                "relationship": kind,
                "path": path,
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
