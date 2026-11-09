"""
Build a migration plan from discovered schema without relying on fixed entity names.
"""

from __future__ import annotations

import re
from typing import Any

_IDENT = re.compile(r"[^A-Za-z0-9_]+")
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_MYSQL_TYPES = {
    "tinyint": "TINYINT",
    "smallint": "SMALLINT",
    "mediumint": "INT",
    "int": "INT",
    "integer": "INT",
    "bigint": "BIGINT",
    "decimal": "DECIMAL(18,6)",
    "numeric": "DECIMAL(18,6)",
    "float": "DOUBLE",
    "double": "DOUBLE",
    "varchar": "TEXT",
    "char": "TEXT",
    "text": "TEXT",
    "mediumtext": "MEDIUMTEXT",
    "longtext": "LONGTEXT",
    "date": "DATE",
    "datetime": "DATETIME",
    "timestamp": "TIMESTAMP NULL",
    "json": "JSON",
    "blob": "BLOB",
    "tinyblob": "BLOB",
    "mediumblob": "BLOB",
    "longblob": "LONGBLOB",
}


def sql_ident(name: str) -> str:
    raw = (name or "col").strip()
    if _SAFE_IDENT.fullmatch(raw) and len(raw) <= 64:
        return raw
    cleaned = _IDENT.sub("_", raw).strip("_") or "col"
    if cleaned[0].isdigit():
        cleaned = "c_" + cleaned
    return cleaned[:64]


def _unique_sql_ident(name: str, used: set[str]) -> str:
    base = sql_ident(name)
    candidate = base
    suffix = 2
    while candidate in used:
        tail = f"_{suffix}"
        candidate = f"{base[:64 - len(tail)]}{tail}"
        suffix += 1
    used.add(candidate)
    return candidate


def build_plan(
    schema: dict[str, Any] | None,
    source_type: str,
    target_type: str,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """
    Plan for whatever entities discovery found.

    Mongo → MySQL: one table per collection plus a child table for every
    discovered array of objects. Other nested values are preserved as JSON.
    MySQL → MongoDB: one collection per table, retaining FK values as references.
    No entity names or sample schema are assumed.
    Same engine: copy each entity.
    """
    source = (source_type or "").lower()
    target = (target_type or "").lower()
    entities = _entities(schema)
    if not entities:
        raise ValueError("No source tables or collections were discovered. Discover a non-empty source database first.")
    if source == "mongodb" and target == "mysql":
        return _mongo_to_mysql(entities, plan_id)
    if source == "mysql" and target == "mongodb":
        return _mysql_to_mongo(entities, plan_id)
    if source == target and source in ("mysql", "mongodb"):
        return _copy_plan(entities, source, plan_id)
    raise ValueError(f"Unsupported migration direction: {source} to {target}")


def collections_to_read(plan: dict[str, Any]) -> list[str]:
    """Source entity names the executor/dry-run should fetch."""
    direction = (plan or {}).get("direction") or ""
    names: list[str] = []

    def _add(name: str | None) -> None:
        if name and name not in names:
            names.append(name)

    if direction == "copy":
        for name in plan.get("entities") or []:
            _add(name)
        return names
    if direction == "document_to_relational":
        for spec in plan.get("flatten") or []:
            _add(spec.get("collection") or (
                spec.get("table") if (spec.get("from_path") or "$") in ("$", "") else None
            ))
        return names
    trees = list(plan.get("model_trees") or [])
    tree = plan.get("model_tree")
    if tree:
        trees.append(tree)
    for node in trees:
        _walk_tree_tables(node, _add)
    return names


def schema_from_connector(connector, source_type: str, database: str = "") -> dict[str, Any]:
    """Live discover when SQLite has no cached schema_json."""
    entities = []
    counts = {}
    try:
        counts = connector.estimate_counts() or {}
    except Exception:
        counts = {}
    for name in connector.list_entities():
        try:
            meta = connector.describe_entity(name)
        except Exception:
            meta = {"name": name, "columns": [], "nesting": [], "foreign_keys": []}
        meta["name"] = meta.get("name") or name
        meta["estimated_count"] = counts.get(name, meta.get("estimated_count") or 0)
        entities.append(meta)
    return {"source_type": source_type, "database": database, "entities": entities}


def _entities(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [entity for entity in (schema or {}).get("entities") or [] if entity.get("name")]


def select_schema_entities(
    schema: dict[str, Any] | None,
    entity_names: list[str] | None,
) -> dict[str, Any]:
    """Return a schema restricted to selected entities, preserving only internal FKs."""
    schema = schema or {}
    entities = _entities(schema)
    if entity_names is None:
        return dict(schema)
    requested = set(entity_names)
    available = {entity["name"] for entity in entities}
    unknown = requested - available
    if unknown:
        raise ValueError(f"Unknown source entities: {', '.join(sorted(unknown))}")
    if not requested:
        raise ValueError("Select at least one table or collection to migrate.")
    selected = []
    for entity in entities:
        if entity["name"] not in requested:
            continue
        copied = dict(entity)
        copied["foreign_keys"] = [
            fk for fk in entity.get("foreign_keys") or []
            if fk.get("ref_table") in requested
        ]
        selected.append(copied)
    return {**schema, "entities": selected}


def _source_constraints(entities: list[dict[str, Any]]) -> dict[str, Any]:
    required_fields: dict[str, list[str]] = {}
    foreign_keys: list[dict[str, str]] = []
    for entity in entities:
        name = entity["name"]
        required_fields[name] = [
            column["name"]
            for column in entity.get("columns") or []
            if column.get("name") and column.get("nullable") is False
        ]
        for fk in entity.get("foreign_keys") or []:
            if fk.get("column") and fk.get("ref_table"):
                foreign_keys.append({
                    "child_table": name,
                    "fk_field": fk["column"],
                    "parent_table": fk["ref_table"],
                    "pk_field": fk.get("ref_column") or "id",
                })
    return {"source_required_fields": required_fields, "source_foreign_keys": foreign_keys}


def _mongo_sql_type(data_type: str) -> str:
    dt = (data_type or "string").lower()
    if dt in ("number", "int", "integer", "float", "double", "decimal"):
        return "DOUBLE"
    if dt in ("boolean", "bool"):
        return "TINYINT(1)"
    if dt in ("object", "array", "mixed"):
        return "JSON"
    return "TEXT"


def _mysql_sql_type(col: dict[str, Any]) -> str:
    return _MYSQL_TYPES.get(str(col.get("data_type") or "text").lower(), "TEXT")


def _generic_mongo_table(
    entity: dict[str, Any],
    root_table: str | None = None,
    used_tables: set[str] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Build root and normalized array-of-object tables for one collection."""
    collection = entity["name"]
    columns = [column for column in entity.get("columns") or [] if column.get("name")]
    column_by_name = {column["name"]: column for column in columns}
    nested_paths = {
        item.get("path"): item.get("type", "object")
        for item in entity.get("nesting") or [] if item.get("path")
    }
    array_paths = sorted(
        (
            path for path, kind in nested_paths.items()
            if kind == "array" and any(column["name"].startswith(path + ".") for column in columns)
        ),
        key=lambda path: (path.count("."), path),
    )

    used_tables = used_tables if used_tables is not None else set()
    root_table = root_table or _unique_sql_ident(collection, used_tables)
    table_by_path = {"$": root_table}
    for path in array_paths:
        table_by_path[path] = _unique_sql_ident(f"{collection}_{path.replace('.', '_')}", used_tables)

    def direct_field_names(path: str) -> list[str]:
        prefix = "" if path == "$" else f"{path}."
        names = set()
        for column in columns:
            full_name = column["name"]
            if path == "$":
                if "." not in full_name:
                    names.add(full_name)
            elif full_name.startswith(prefix):
                remainder = full_name[len(prefix):]
                if remainder and "." not in remainder:
                    names.add(remainder)
        return sorted(names)

    def make_spec(path: str, parent_path: str | None = None) -> tuple[dict[str, Any], str]:
        table = table_by_path[path]
        direct_names = direct_field_names(path)
        child_array_names = {
            candidate[len(path + "."):]
            for candidate in array_paths
            if candidate.startswith(path + ".") and "." not in candidate[len(path + "."):]
        } if path != "$" else {
            candidate
            for candidate in array_paths
            if "." not in candidate
        }
        fields: list[str] = []
        json_fields: list[str] = []
        rename: dict[str, str] = {}
        definitions = ["`id` VARCHAR(64) PRIMARY KEY"] if path == "$" else []
        reserved = {"id"} if path == "$" else {"id"}
        parent_fk = None
        if parent_path is not None:
            parent_fk = "parent_id"
            while parent_fk in reserved:
                parent_fk = f"_{parent_fk}"
            reserved.add(parent_fk)
            definitions.extend([
                f"`id` VARCHAR(64) PRIMARY KEY",
                f"`{parent_fk}` VARCHAR(64) NOT NULL",
            ])

        for field in direct_names:
            if field in ("_id", "id") or field in child_array_names:
                continue
            full_name = field if path == "$" else f"{path}.{field}"
            column_meta = column_by_name.get(full_name) or {}
            data_type = str(column_meta.get("data_type") or "").lower()
            has_descendants = any(column["name"].startswith(full_name + ".") for column in columns)
            is_json = data_type in ("object", "array", "mixed") or has_descendants
            target_name = sql_ident(field)
            base_target_name = target_name
            suffix = 2
            while target_name in reserved:
                tail = f"_{suffix}"
                target_name = f"{base_target_name[:64 - len(tail)]}{tail}"
                suffix += 1
            reserved.add(target_name)
            fields.append(field)
            if target_name != field:
                rename[field] = target_name
            if is_json:
                json_fields.append(field)
                sql_type = "JSON"
            else:
                sql_type = _mongo_sql_type(data_type)
            definitions.append(f"`{target_name}` {sql_type} NULL")

        spec: dict[str, Any] = {
            "table": table,
            "from_path": path,
            "collection": collection,
            "fields": fields,
            "json_fields": json_fields,
            "rename": rename,
            "emit_id": True,
            "include_unknown_fields": True,
            "exclude_fields": sorted(child_array_names),
        }
        if parent_fk and parent_path is not None:
            spec["parent_fk"] = parent_fk
            spec["parent_path"] = parent_path
            parent_table = table_by_path.get(parent_path, root_table)
            definitions.append(
                f"FOREIGN KEY (`{parent_fk}`) REFERENCES `{parent_table}` (`id`)"
            )
        ddl = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(definitions) + "\n)"
        return spec, ddl

    root_spec, root_ddl = make_spec("$")
    specs = [root_spec]
    ddl_parts = [root_ddl]
    for path in array_paths:
        parent_paths = [candidate for candidate in array_paths if path.startswith(candidate + ".")]
        parent_path = max(parent_paths, key=len) if parent_paths else "$"
        spec, ddl = make_spec(path, parent_path)
        specs.append(spec)
        ddl_parts.append(ddl)
    return ddl_parts, specs


def _mongo_to_mysql(entities: list[dict[str, Any]], plan_id: str | None) -> dict[str, Any]:
    flatten: list[dict[str, Any]] = []
    ddl_parts: list[str] = []
    used_tables: set[str] = set()
    root_tables = {entity["name"]: _unique_sql_ident(entity["name"], used_tables) for entity in entities}
    for entity in entities:
        entity_ddl, entity_specs = _generic_mongo_table(entity, root_tables[entity["name"]], used_tables)
        flatten.extend(entity_specs)
        ddl_parts.extend(entity_ddl)
    return {
        "plan_id": plan_id,
        "direction": "document_to_relational",
        "target_type": "mysql",
        "generated_ddl": ";\n".join(ddl_parts),
        "flatten": flatten,
        **_source_constraints(entities),
    }


def _mysql_tree_for_table(entity: dict[str, Any]) -> dict[str, Any]:
    fields = [col.get("name") for col in entity.get("columns") or [] if col.get("name")]
    name = entity["name"]
    return {
        "from_table": name,
        "collection": sql_ident(name),
        "fields": fields,
        "embed": [],
    }


def _mysql_to_mongo(entities: list[dict[str, Any]], plan_id: str | None) -> dict[str, Any]:
    trees = [_mysql_tree_for_table(entity) for entity in entities]
    return {
        "plan_id": plan_id,
        "direction": "relational_to_document",
        "target_type": "mongodb",
        "model_tree": trees[0],
        "model_trees": trees,
        **_source_constraints(entities),
    }


def _copy_mysql_ddl(entity: dict[str, Any]) -> str:
    table = sql_ident(entity["name"])
    cols = []
    pk = None
    for col in entity.get("columns") or []:
        name = col.get("name")
        if not name:
            continue
        ident = sql_ident(name)
        sql_type = _mysql_sql_type(col)
        nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
        extra = " AUTO_INCREMENT" if col.get("auto_increment") else ""
        cols.append(f"`{ident}` {sql_type}{extra} {nullable}")
        if col.get("primary_key") and pk is None:
            pk = ident
    if not cols:
        cols.append("`id` VARCHAR(64) PRIMARY KEY")
    elif pk:
        cols.append(f"PRIMARY KEY (`{pk}`)")
    return f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(cols) + "\n)"


def _copy_plan(entities: list[dict[str, Any]], engine: str, plan_id: str | None) -> dict[str, Any]:
    names = [entity["name"] for entity in entities]
    plan: dict[str, Any] = {
        "plan_id": plan_id,
        "direction": "copy",
        "target_type": engine,
        "entities": names,
        **_source_constraints(entities),
    }
    if engine == "mysql":
        plan["generated_ddl"] = ";\n".join(_copy_mysql_ddl(entity) for entity in entities)
    return plan


def _walk_tree_tables(node: dict[str, Any], add) -> None:
    add(node.get("from_table") or node.get("collection"))
    for child in node.get("embed") or []:
        _walk_tree_tables(child, add)
