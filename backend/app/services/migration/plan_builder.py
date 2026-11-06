"""
Build a migration plan from discovered schema.

Shop customers → orders → items stays the nested demo path.
Any other tables/collections are copied 1:1 into the connected target.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.migration.transformer import _SHOP_FLATTEN, _SHOP_TREE

_SHOP_MYSQL_DDL = """
CREATE TABLE IF NOT EXISTS customers (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NULL,
  email VARCHAR(255) NULL,
  created_at VARCHAR(64) NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id VARCHAR(64) NULL,
  order_date VARCHAR(64) NULL,
  total DECIMAL(12,2) NULL,
  status VARCHAR(64) NULL
);
CREATE TABLE IF NOT EXISTS order_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NULL,
  product_id VARCHAR(64) NULL,
  product_name VARCHAR(255) NULL,
  quantity INT NULL,
  price DECIMAL(12,2) NULL
);
"""

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


def shop_plan(source_type: str, plan_id: str | None = None) -> dict[str, Any]:
    """Fixture plan when no discovered schema is available yet."""
    if (source_type or "").lower() == "mongodb":
        flatten = [dict(spec, collection="customers") for spec in _SHOP_FLATTEN]
        return {
            "plan_id": plan_id,
            "direction": "document_to_relational",
            "target_type": "mysql",
            "generated_ddl": _SHOP_MYSQL_DDL,
            "flatten": flatten,
        }
    return {
        "plan_id": plan_id,
        "direction": "relational_to_document",
        "target_type": "mongodb",
        "model_tree": dict(_SHOP_TREE),
    }


def build_plan(
    schema: dict[str, Any] | None,
    source_type: str,
    target_type: str,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """
    Plan for whatever entities discovery found.

    Mongo → MySQL: one table per collection (JSON for nested values).
    Nested shop customers still flatten to customers/orders/order_items.
    MySQL → Mongo: shop embed tree when those tables exist; other tables 1:1.
    Same engine: copy each entity.
    """
    source = (source_type or "").lower()
    target = (target_type or "").lower()
    entities = _entities(schema)
    if not entities:
        return shop_plan(source, plan_id)
    if source == "mongodb" and target == "mysql":
        return _mongo_to_mysql(entities, plan_id)
    if source == "mysql" and target == "mongodb":
        return _mysql_to_mongo(entities, plan_id)
    if source == target and source in ("mysql", "mongodb"):
        return _copy_plan(entities, source, plan_id)
    return shop_plan(source, plan_id)


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


def _nest_paths(entity: dict[str, Any]) -> set[str]:
    return {item.get("path") for item in entity.get("nesting") or [] if item.get("path")}


def _is_shop_nested_customers(entity: dict[str, Any]) -> bool:
    return entity.get("name") == "customers" and {"orders", "orders.items"} <= _nest_paths(entity)


def _shop_mysql_tables(entities: list[dict[str, Any]]) -> bool:
    names = {entity["name"] for entity in entities}
    return {"customers", "orders", "order_items"} <= names


def _top_level_nested(entity: dict[str, Any]) -> set[str]:
    nested: set[str] = set()
    for path in _nest_paths(entity):
        nested.add(path.split(".", 1)[0])
    for col in entity.get("columns") or []:
        name = col.get("name") or ""
        if not name or name in ("_id", "id"):
            continue
        if "." in name:
            nested.add(name.split(".", 1)[0])
        elif str(col.get("data_type") or "").lower() in ("object", "array"):
            nested.add(name)
    return nested


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


def _rename_map(names: list[str]) -> dict[str, str]:
    return {name: sql_ident(name) for name in names if sql_ident(name) != name}


def _generic_mongo_table(entity: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    collection = entity["name"]
    table = sql_ident(collection)
    nested = _top_level_nested(entity)
    col_sql = ["`id` VARCHAR(64) PRIMARY KEY"]
    fields = ["id"]
    json_fields: list[str] = []
    seen = {"id"}
    for col in entity.get("columns") or []:
        name = col.get("name") or ""
        if not name or name in ("_id", "id") or "." in name:
            continue
        ident = sql_ident(name)
        if ident in seen:
            continue
        seen.add(ident)
        if name in nested or str(col.get("data_type") or "").lower() in ("object", "array"):
            col_sql.append(f"`{ident}` JSON NULL")
            json_fields.append(name)
        else:
            col_sql.append(f"`{ident}` {_mongo_sql_type(str(col.get('data_type') or ''))} NULL")
        fields.append(name)
    for name in sorted(nested):
        ident = sql_ident(name)
        if ident in seen:
            continue
        seen.add(ident)
        col_sql.append(f"`{ident}` JSON NULL")
        json_fields.append(name)
        fields.append(name)
    ddl = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(col_sql) + "\n)"
    spec = {
        "table": table,
        "from_path": "$",
        "collection": collection,
        "fields": fields,
        "json_fields": json_fields,
        "rename": _rename_map(fields),
    }
    return ddl, spec


def _mongo_to_mysql(entities: list[dict[str, Any]], plan_id: str | None) -> dict[str, Any]:
    flatten: list[dict[str, Any]] = []
    ddl_parts: list[str] = []
    used_shop = False
    for entity in entities:
        if _is_shop_nested_customers(entity):
            used_shop = True
            flatten.extend(dict(spec, collection="customers") for spec in _SHOP_FLATTEN)
            ddl_parts.append(_SHOP_MYSQL_DDL.strip())
            continue
        ddl, spec = _generic_mongo_table(entity)
        flatten.append(spec)
        ddl_parts.append(ddl)
    return {
        "plan_id": plan_id,
        "direction": "document_to_relational",
        "target_type": "mysql",
        "generated_ddl": ";\n".join(ddl_parts),
        "flatten": flatten,
        "used_shop_flatten": used_shop,
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
    if _shop_mysql_tables(entities):
        extras = [
            _mysql_tree_for_table(entity)
            for entity in entities
            if entity["name"] not in {"customers", "orders", "order_items"}
        ]
        plan: dict[str, Any] = {
            "plan_id": plan_id,
            "direction": "relational_to_document",
            "target_type": "mongodb",
            "model_tree": dict(_SHOP_TREE),
        }
        if extras:
            plan["model_trees"] = [dict(_SHOP_TREE), *extras]
        return plan
    trees = [_mysql_tree_for_table(entity) for entity in entities]
    return {
        "plan_id": plan_id,
        "direction": "relational_to_document",
        "target_type": "mongodb",
        "model_tree": trees[0] if trees else dict(_SHOP_TREE),
        "model_trees": trees,
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
    }
    if engine == "mysql":
        plan["generated_ddl"] = ";\n".join(_copy_mysql_ddl(entity) for entity in entities)
    return plan


def _walk_tree_tables(node: dict[str, Any], add) -> None:
    add(node.get("from_table") or node.get("collection"))
    for child in node.get("embed") or []:
        _walk_tree_tables(child, add)
