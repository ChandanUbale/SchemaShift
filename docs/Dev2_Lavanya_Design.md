# SchemaShift Design Document — Dev 2 (Lavanya)

**You are:** Lavanya, full-stack developer (Dev 2).  
**You own:** the move half — MongoDB source, transformer (both directions), MySQL writer, dry run, batch execute, approval, sample/relationship validation, final report.

**Your first task:** [Task 1 — Handshake + MongoDB connector](#task-1--first-task--handshake--mongodb-connector)  
Start Task 1 this morning after the 15-minute handshake with Chandan. You do **not** wait for Chandan’s MySQL connector to start coding Mongo. You **do** wait for him on later tasks, and this document says exactly which ones.

---

## How to use this document

1. Do tasks **in this order**.
2. Read **Blockers** before you start a task. If it names Chandan or Kantraj, that work must exist first.
3. The **Procedure** is the design. Implement that, nothing extra.
4. **Done when** is your exit check.

## Rules you must never break

- Dry run **never** calls `BaseWriter.write_batch` or any insert/update/drop.
- Migration is the **only** stage that writes, and only after `approved=true`.
- Do not let Ollama block dry-run or migrate. Optional AI is Task 11 and may be skipped.
- Do not edit React. That is Kantraj.
- Do not edit seed files. That is Vinuta.
- Do not edit `mysql_connector.py`, `scoring_engine.py`, `model_generator.py`, `column_profiler.py`, or `mongo_writer.py`. Those are Chandan.

## Files you own

| File | Why |
|---|---|
| `backend/app/services/discovery/mongodb_connector.py` | Mongo source reads |
| `backend/app/services/discovery/relationship_mapper.py` | Mongo branch only |
| `backend/app/routers/discovery.py` | Plug Mongo into the same endpoints Chandan wired |
| `backend/app/services/migration/mysql_writer.py` | Target writes for Mongo → MySQL |
| `backend/app/services/migration/transformer.py` | Relational ↔ document |
| `backend/app/services/migration/dry_runner.py` | Issues, zero writes |
| `backend/app/services/migration/batch_executor.py` | Batches, retry, audit, progress |
| `backend/app/routers/migration.py` | Dry-run, execute, cleanup (not the SSE generator — Chandan owns jobs.py) |
| `backend/app/services/validation/checksum_validator.py` | Sample hash match |
| `backend/app/services/validation/relationship_validator.py` | FK / refs after migrate |
| `backend/app/services/validation/report_generator.py` | HTML + JSON report |
| `backend/app/routers/validation.py` | Validation API |
| `backend/app/services/recommendation/ai_explainer.py` | Optional last; already has fallback |

## Task order at a glance

| Order | Task | Blocked by |
|---|---|---|
| **1 FIRST** | Handshake + MongoDB connector | Handshake with Chandan only (15 min). Code is not blocked. Live test needs Kantraj compose + Vinuta Mongo seed |
| 2 | Discovery for Mongo + graph Mongo branch | Your Task 1. Chandan must have put the discover router skeleton in place (his Task 3). If his endpoints still raise `NotImplementedError`, implement only the Mongo path in the same functions after he has the MySQL path, **or** wait until his Task 3 is merged so you do not overwrite him |
| 3 | MySQL writer | None to code. Live test needs Kantraj `mysql-target` |
| 4 | Transformer: relational → document | Handshake Plan JSON. You can code against the JSON in this file **without** waiting. Full prove waits for Chandan MySQL connector + Mongo writer |
| 5 | Batch executor skeleton + prove MySQL → Mongo | **Chandan Task 1** (jobs `update_progress`) **and Chandan Task 4** (MongoWriter) **and Chandan Task 2** (MySQLConnector) **and your Task 4** |
| 6 | Transformer: document → relational | Your Task 4 shape. Not blocked by Chandan |
| 7 | Dry runner | Your Task 4. Must not wait on writers |
| 8 | Approval gate on execute | Your Task 5. Extra confirm uses Chandan’s profiling `risk_label` |
| 9 | Retry, audit log, cleanup | Your Task 5 and Task 3 (cleanup uses writers) |
| 10 | Checksum + relationship validators + report | **Chandan Task 9** (count + aggregate). You call his functions inside the report |
| 11 | Pair with Chandan: Mongo → MySQL E2E | Your Tasks 1, 3, 6, 5, 8 and Vinuta Mongo seed |
| 12 | Answer Kantraj for UI Steps 5–7 | Your dry-run / execute / validation APIs |
| 13 | Optional Ollama explainer | Only if both directions already work. Cut this first if short on time |

---

## Shared contracts (same as Chandan’s document — do not change)

### Schema JSON

```json
{
  "source_type": "mongodb",
  "database": "demo_source",
  "entities": [
    {
      "name": "customers",
      "entity_kind": "collection",
      "estimated_count": 10000,
      "columns": [
        { "name": "name", "data_type": "string", "nullable": false, "primary_key": false, "auto_increment": false },
        { "name": "orders.total", "data_type": "number", "nullable": true, "primary_key": false, "auto_increment": false }
      ],
      "indexes": [],
      "foreign_keys": [],
      "nesting": [
        { "path": "orders", "type": "array" },
        { "path": "orders.items", "type": "array" }
      ]
    }
  ]
}
```

### Plan JSON — document target (MySQL → Mongo)

```json
{
  "plan_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "recommended_model": "document",
  "target_type": "mongodb",
  "direction": "relational_to_document",
  "generated_ddl": null,
  "model_tree": {
    "collection": "customers",
    "fields": ["id", "name", "email", "created_at"],
    "embed": [
      {
        "from_table": "orders",
        "as": "orders",
        "join": { "parent": "id", "child": "customer_id" },
        "fields": ["id", "order_date", "total", "status"],
        "embed": [
          {
            "from_table": "order_items",
            "as": "items",
            "join": { "parent": "id", "child": "order_id" },
            "fields": ["product_id", "product_name", "quantity", "price"]
          }
        ]
      }
    ]
  }
}
```

### Plan JSON — relational target (Mongo → MySQL)

- `direction`: `"document_to_relational"`
- `generated_ddl`: MySQL `CREATE TABLE` with `AUTO_INCREMENT`
- `model_tree`: `null`
- `flatten`:

```json
"flatten": [
  { "table": "customers", "from_path": "$" },
  { "table": "orders", "from_path": "$.orders", "parent_fk": "customer_id" },
  { "table": "order_items", "from_path": "$.orders.items", "parent_fk": "order_id" }
]
```

`BaseConnector` and `BaseWriter` method names stay as in the repo. Do not rename them.

---

## Task 1 — FIRST TASK — Handshake + MongoDB connector

**Do this first.**  
**Blockers:** Only the handshake. Chandan must sit with you for 15 minutes and agree the JSON above. He does **not** need to finish MySQL connector before you start this file.

**Live test blocker:** Kantraj’s `docker compose up` and Vinuta’s Mongo seed in database `demo_source`. You can still write the class now.

### Handshake (15 minutes)

1. Confirm `BaseConnector` methods will not change.
2. Confirm Schema JSON + Plan JSON keys above.
3. Confirm you will call `from app.jobs import update_progress` and will not rewrite `jobs.py`.

Then you open `mongodb_connector.py`. Chandan goes to connections/jobs.

### File

`backend/app/services/discovery/mongodb_connector.py`

`ConnectorFactory` already maps `"mongodb"` to this class. Do not fight Chandan on that file.

### Procedure

`__init__(uri, db_name)` is already correct.

**`connect`**

```python
self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
self._db = self._client[self.db_name]
self._client.admin.command("ping")
```

**`disconnect`** — already correct.

**`list_entities`**

```python
names = self._db.list_collection_names()
return [n for n in names if not n.startswith("system.")]
```

**`describe_entity(name)`**

1. Sample up to 100 documents: `aggregate([{"$sample": {"size": 100}}])`. If the collection is smaller, you get fewer.
2. Walk each document recursively.
3. For every field path (`orders.items.price`) record inferred type: `string | number | boolean | date | objectid | object | array | null`.
4. If the same path has more than one type, store `data_type: "mixed"`.
5. If a field is an array of objects, add `{ "path": that.path, "type": "array" }` to `nesting`.
6. `_id` is `primary_key: true`.
7. Return one entity dict in Schema JSON shape.

**`fetch_sample(name, n)`**

```python
list(self._db[name].aggregate([{"$sample": {"size": n}}]))
```

If n < 1, return `[]`. Convert `ObjectId` and `datetime` to `str` before returning if JSON serialization breaks later; keep raw types inside the connector if the transformer can handle them. Prefer converting `ObjectId` → `str` in the connector so FastAPI can JSON-encode samples.

**`fetch_batch(name, offset, limit)`**

```python
list(self._db[name].find().skip(offset).limit(limit))
```

**`estimate_counts`**

```python
{col: self._db[col].estimated_document_count() for col in self.list_entities()}
```

### Done when

Against `demo_source.customers`, `list_entities` includes `customers`, and `describe_entity` lists `orders` and `orders.items` in `nesting`.

---

## Task 2 — Discovery API for Mongo + relationship graph (Mongo)

**Do this after Task 1.**  
**Blockers:** Chandan **Task 3** should land first so you do not both rewrite `discovery.py`. If his MySQL discover endpoint already works, you only make the same function accept `source_type == "mongodb"`.

If you get to this file and Chandan has not implemented the router yet: **stop and ping him**. Do not replace the whole file. Wait until his MySQL path is merged.

### Files

- `backend/app/routers/discovery.py` (Mongo branch only)
- `backend/app/services/discovery/relationship_mapper.py` — function `_graph_mongo`

### Procedure

Chandan’s discover handler already: load connection → factory → list/describe → save `schema_json`.

You verify that `ConnectorFactory.get_connector("mongodb", dsn, db_name=...)` is used when `source_type` is mongodb. If he forgot `db_name`, add it carefully (one `if` branch).

**`_graph_mongo(schema)`**

- One node per collection: `{ id, label, columns }` where `columns` are top-level field names plus nesting paths.
- Edges: for each nesting path, `{ source: collection, target: collection, label: "embeds orders" }` is enough for the demo (self-edge or a child node `customers.orders`).

Simpler and clearer for Kantraj:

- Nodes: `customers`, `customers.orders`, `customers.orders.items`
- Edges: `customers → customers.orders` label `embeds`, `customers.orders → customers.orders.items` label `embeds`

### Done when

`POST /api/discovery/{mongo_connection_id}/discover` returns nesting. GET relationships returns those nodes/edges.

---

## Task 3 — MySQL writer

**Do this after Task 1 (can overlap Task 2).**  
**Blockers:** None to code. Live write needs Kantraj `mysql-target` on port 3307.

### File

`backend/app/services/migration/mysql_writer.py`

### Procedure

Parse DSN the same way Chandan does for MySQL (scheme `mysql+pymysql` → `urlparse`). Connect with `pymysql` DictCursor.

**`prepare(plan)`**

1. Connect.
2. Run `plan["generated_ddl"]` split on `;`. Skip empty chunks.
3. Remember table names from `plan["flatten"]` for cleanup.
4. Do not drop tables here. That is `cleanup`.

**`write_batch(rows, entity_name)`**

`rows` is a list of dicts for **one table**.

```python
if not rows:
    return 0
cols = list(rows[0].keys())
placeholders = ", ".join(["%s"] * len(cols))
col_sql = ", ".join(f"`{c}`" for c in cols)
sql = f"INSERT INTO `{entity_name}` ({col_sql}) VALUES ({placeholders})"
values = [tuple(r.get(c) for c in cols) for r in rows]
with self._conn.cursor() as cur:
    cur.executemany(sql, values)
self._conn.commit()
return len(rows)
```

**`finalize`**

`self._conn.commit()`. Optional: `ANALYZE TABLE` skipped for MVP.

**`cleanup(job_id)`**

`SET FOREIGN_KEY_CHECKS=0`, `DROP TABLE IF EXISTS` each remembered table in reverse FK order (`order_items`, `orders`, `customers`, `products`), then `SET FOREIGN_KEY_CHECKS=1`.

### Done when

`prepare` + `write_batch` of 2 customer rows into `migration_target` is visible with `SELECT`.

---

## Task 4 — Transformer: relational → document (first direction)

**Do this after the handshake.**  
**Blockers:** None to code. You implement against the Plan JSON in this file.  
**Prove-it blocker (not this task):** Chandan MySQL connector + Mongo writer are needed in Task 5.

### File

`backend/app/services/migration/transformer.py`

### Procedure

`transform_row` already routes on `direction`. Implement `_relational_to_document`.

This method cannot nest children from a **single** customer row. The executor will pass **groups**, not one isolated row.

Add a public method the executor will call (keep `transform_row` for single-row tests):

```python
def transform_batch(self, tables: dict[str, list[dict]], direction: str) -> list[dict]:
    # tables = {"customers": [...], "orders": [...], "order_items": [...]}
```

**Relational → document algorithm**

1. Read `plan["model_tree"]`.
2. Index child rows by FK:
   - `orders_by_customer = group orders by customer_id`
   - `items_by_order = group order_items by order_id`
3. For each customer row, build:

```python
{
  "id": customer["id"],
  "name": customer["name"],
  "email": customer["email"],
  "created_at": customer["created_at"],
  "orders": [
    {
      "id": order["id"],
      "order_date": order["order_date"],
      "total": order["total"],
      "status": order.get("status"),
      "items": [ { product fields } for item in items_by_order[order["id"]] ]
    }
    for order in orders_by_customer.get(customer["id"], [])
  ]
}
```

4. Copy only fields listed in `model_tree.fields` / nested `fields` so extra columns do not leak.

If `model_tree` is missing, use the shop default above (customers ← orders ← order_items). Do not guess PostgreSQL names.

`_relational_to_document` on a **single** row: wrap it as `{**row, "orders": []}` so unit tests do not crash. Real nesting happens in `transform_batch`.

### Done when

Given 1 customer, 2 orders, 3 items in a fixture dict, you get 1 document with `orders.length == 2` and nested `items`.

---

## Task 5 — Batch executor skeleton + prove MySQL → Mongo

**Do this after Task 4.**  
**Blockers — Chandan must finish these first:**

1. **Chandan Task 1** — `update_progress` works (you call it).
2. **Chandan Task 2** — `MySQLConnector.fetch_batch` / `estimate_counts` work.
3. **Chandan Task 4** — `MongoWriter.write_batch` works.

If any of those three is missing, you can still write the loop with placeholders, but you **cannot prove** the path. Ping Chandan by name for the missing task, then continue.

### File

`backend/app/services/migration/batch_executor.py`

### Procedure

`MAX_RETRIES = 3` is already there.

`BatchExecutor.run(job_id, source_connector, writer, transformer, plan, batch_size=1000)`:

1. `writer.prepare(plan)`
2. `direction = plan["direction"]`

**If `relational_to_document`:**

- Root table = `plan["model_tree"]["collection"]` mapped back to table name `customers` (shop default).
- `total = estimate_counts()[root]`
- `batches_total = ceil(total / batch_size)`
- For `offset` in 0, batch_size, 2*batch_size, ...:
  - `customers = fetch_batch("customers", offset, batch_size)`
  - Collect ids. Fetch matching orders / items (simple approach for demo: fetch all orders/items once into memory if counts are ~10k; that is allowed at demo scale).
  - `docs = transformer.transform_batch(tables, direction)`
  - Try `writer.write_batch(docs, collection_name)` up to `MAX_RETRIES`
  - Append `{batch, ok, rows, error}` to `audit_log`
  - `pct = int((batch_index+1) / batches_total * 100)`
  - `update_progress(job_id, pct, RUNNING)`
- `writer.finalize()`
- `update_progress(job_id, 100, DONE)`
- Return `{audit_log, batches_total, batches_failed}`

On unhandled exception: `update_progress(job_id, pct, FAILED, error=str(exc))` and re-raise.

**If `document_to_relational`:** implement the loop in Task 6 after flatten exists. For Task 5 you may `raise` if direction is not relational_to_document.

**Prove (end of this task):**

Using Chandan’s MySQL connector + your transformer + his MongoWriter, one script or one execute call copies the shop into `migration_target`. You should see nested customer documents.

### Done when

Audit log has one success entry per batch and Mongo contains nested docs. Failed batch retries 3 times then records `ok: false`.

---

## Task 6 — Transformer: document → relational

**Do this after Task 4.**  
**Blockers:** None from Chandan.

### Procedure

Implement `_document_to_relational(doc) -> dict[str, list[dict]]`.

Using `plan["flatten"]` (or shop default):

```python
customers = [{ "id": ..., "name": ..., "email": ..., "created_at": ... }]  # from top-level
orders = []
order_items = []
for order in doc.get("orders") or []:
    orders.append({
        "id": order.get("id"),          # if missing, leave None; writer uses AUTO_INCREMENT
        "customer_id": doc["id"],
        "order_date": order.get("order_date"),
        "total": order.get("total"),
        "status": order.get("status"),
    })
    for item in order.get("items") or []:
        order_items.append({
            "order_id": order.get("id"),
            "product_name": item.get("product_name"),
            "quantity": item.get("quantity"),
            "price": item.get("price"),
        })
return {"customers": customers, "orders": orders, "order_items": order_items}
```

If Mongo `_id` is the only id, map `_id` → `id` as string or hash to int. Prefer storing original `_id` in a `mongo_oid VARCHAR` column only if Chandan’s DDL includes it. If DDL does not, skip the field.

Extend `transform_batch` for this direction: flatten every doc, concatenate lists per table.

Extend `BatchExecutor` for this direction:

1. `writer.prepare(plan)` runs DDL
2. Read Mongo batches from source connector
3. Flatten
4. Write **parents first**: `customers`, then `orders`, then `order_items` (FK order)

### Done when

One nested customer fixture becomes 1 + N + M rows in the three table lists.

---

## Task 7 — Dry runner (zero target writes)

**Do this after Task 4.**  
**Blockers:** None. Do **not** wait for writers.

### File

`backend/app/services/migration/dry_runner.py`

### Procedure

`DryRunner.run(source_rows, transformer, plan)`:

`source_rows` for relational→document should actually be the `tables` dict. Change the signature to:

```python
def run(source_data, transformer, plan) -> list[dict]
```

- If direction is relational_to_document, `source_data` is `{table: rows}`.
- If document_to_relational, `source_data` is `list[dict]` documents.

Steps:

1. Try `transformer.transform_batch` / `transform_row` inside `try/except`. Each exception → issue `type_mismatch` or `transform_error`.
2. Scan source (not target) for:
   - `invalid_date` — same rules as QualityChecker (copy the date check; do not import writers)
   - `duplicate_pk` — duplicate `id` / `_id` in the sample
   - `orphan_fk` — order.customer_id not in sampled customer ids
   - `missing_field` — required target field is None (name, email, quantity)
3. Return list of `{table_or_collection, issue_type, row_count, description}`.

**Hard rule:** this module must not import `mysql_writer`, `mongo_writer`, or `WriterFactory`. Add a unit test later that grep/import-checks this if you can.

### Router

`POST /api/migration/dry-run` body: `{ source_connection_id, plan_id }`

1. Load plan from Chandan’s `recommendation_plans` table. If that table is not ready, **ping Chandan Task 7**. You can still implement `DryRunner.run` with a fixture plan.
2. `job_id = create_job(db, "dry_run", ...)` — `create_job` is Chandan’s. If it still does not persist, you may call it anyway; ping him if it crashes.
3. Background: fetch samples via the **source connector only**, run `DryRunner.run`, save issues on `MigrationJob.audit_log`, mark job DONE.
4. Return 202 `{ job_id }`. Client polls status or you also return issues when job is DONE via GET status plus stored audit_log.

Add GET that returns issues. Simplest: put issues on `MigrationJob.audit_log` and have `GET /api/migration/{job_id}/status` include them if you extend the response. If you cannot change Chandan’s schema, add `GET /api/migration/{job_id}/dry-run` that reads `audit_log`.

### Done when

Vinuta’s orphan / bad-date rows show up in the issue list, and Mongo `migration_target` is still empty.

---

## Task 8 — Approval gate

**Do this after Task 5 (execute exists) and Task 7 (dry-run exists).**  
**Blockers:** Chandan’s profiling result must expose `risk_label` (his Task 5). If profiling is missing, still require `approved=true`, and skip the extra High-risk check until his API returns it.

### File

`backend/app/routers/migration.py` — `POST /api/migration/execute`

### Procedure

Body is `MigrationApproveRequest`.

Reject with 400 unless **all** of these are true:

1. `payload.approved` — wait, the schema field is on the **job**, not the request. Look at `MigrationApproveRequest`: `job_id`, `plan_id`, `source_connection_id`, `target_connection_id`, `override_recommendation`, `in_place_optimisation`.

The request **is** the approval. Treat POST execute as the user saying yes.

Still reject if:

1. `plan_id` does not exist.
2. No successful dry-run job for that `plan_id` (look up latest dry_run `MigrationJob` with that plan_id and `status=done`). If you cannot find one → 400 `"Run dry-run before execute"`.
3. Source DSN == target DSN and `in_place_optimisation` is false → call Chandan’s `assert_distinct_targets` (**Chandan Task 8**). If his helper is not there yet, copy the same rule inline and replace later.
4. If latest profiling `risk_label == "high"`: require query param or body field. The schema has no `confirm_high_risk`. **Add** `confirm_high_risk: bool = False` to `MigrationApproveRequest`. If risk is high and `confirm_high_risk` is false → 400 `"Profiling risk is High. Set confirm_high_risk=true to proceed."`

If `override_recommendation` is `"mysql"` or `"mongodb"` and differs from the plan’s `target_type`, rewrite `plan["target_type"]` and `direction` for this job only. Do not rescore. User override wins.

Then `create_job(..., "migration")`, set `approved=True` on `MigrationJob`, start `BatchExecutor.run` as a background task, return 202 `{ job_id }`.

### Done when

Execute without dry-run fails. Execute with High risk and `confirm_high_risk=false` fails. Execute with approval starts batches.

---

## Task 9 — Retry, audit log, cleanup

**Do this as you harden Task 5.**  
**Blockers:** Writers must exist (your MySQL writer + Chandan Mongo writer).

### Procedure

Retry is already in Task 5. Finish it if you skipped failures.

Audit log entry shape (append-only, never delete):

```json
{ "batch_index": 0, "entity": "customers", "rows": 1000, "ok": true, "attempts": 1, "error": null }
```

Save the full list on `MigrationJob.audit_log` when the job ends.

**`POST /api/migration/cleanup`** body `{ job_id, target_connection_id }`

1. Load target connection.
2. `WriterFactory.get_writer(target_type, dsn, ...)`
3. `writer.cleanup(job_id)`
4. Do not drop the source.

No automatic rollback. No `DELETE FROM` of “only failed rows”. Full reset of this job’s target tables/collections only.

### Done when

After a migrate, cleanup leaves `migration_target` empty, and source data is untouched.

---

## Task 10 — Checksum, relationships, final report

**Do this after Task 8.**  
**Blockers:** **Chandan Task 9** — you must call his `CountValidator` / `AggregateValidator` (or `run_count_and_aggregate`). If he is late, you can still ship checksum + HTML and leave two labelled placeholders, then plug his dicts in. Do not reimplement counts yourself if his functions exist.

### Files

- `checksum_validator.py`
- `relationship_validator.py`
- `report_generator.py`
- `routers/validation.py`

### Procedure

**Checksum**

`ChecksumValidator.checksum_row` already hashes sorted keys (skips `id`/`_id`). Finish `validate`:

- Map source sample by `pk_field`
- Map target sample by `pk_field`
- For each pk in the intersection, compare checksums
- Return `{ checked, matched, summary: "96/100", mismatched_pks: [...] }`

For nested Mongo vs flat MySQL, checksum the **root customer fields only** (name, email) so the demo can pass. Document that in the report JSON.

**Relationships**

For MySQL target: for each FK in the plan/schema, count child rows whose parent id is missing. `passed` if every `orphan_count == 0`.

For Mongo target: for each customer, every `orders[].items` may exist without a product table — treat as passed if `orders` is an array (embedding is the relationship).

**Report generator**

Inputs: profiling result, migration stats, validation result.

Write HTML using `HTML_TEMPLATE` already in the file. Three headings:

1. Data quality before (risk_label, risk_score) — **do not mix into validation %**
2. Migration stats (records, batches, duration, failed batches)
3. Validation after (count %, aggregate yes/no, sample summary, relationship passed/failed)

Also return the same data as a dict (JSON).

**Router**

- `POST /api/validation/` → 202 job, background run all validators, save `ValidationReport`
- `GET /{migration_job_id}/result` → `ValidationResult`
- `GET /{migration_job_id}/report` → `FinalReport`
- `GET /{migration_job_id}/report.html` → `HTMLResponse` of the file

### Done when

Final report shows Low/Medium/High **and separately** “Records matched: …”. One number must not replace the other.

---

## Task 11 — Pair with Chandan: Mongo → MySQL end-to-end

**Blockers:** Your Tasks 1, 3, 6, 8 and Vinuta’s Mongo seed. Chandan’s scoring should recommend **relational** when you tick frequent joins + transactional writes on the Mongo source.

### Procedure

1. Connect Mongo `demo_source`.
2. Discover → profile → recommend (expect mysql) → dry-run → approve → execute into `mysql-target`.
3. You fix transformer flatten + MySQL writer. He fixes scoring if it wrongly picks Mongo.
4. Validation uses his counts + your checksum/report.

### Done when

`migration_target` MySQL has customers/orders/items populated from nested Mongo docs.

---

## Task 12 — Support Kantraj (Steps 5–7)

He will call:

| Step | Path |
|---|---|
| 5 | `POST /api/migration/dry-run` |
| 6 | `POST /api/migration/execute`, `GET .../status`, `GET .../stream` |
| 7 | `POST /api/validation/`, `GET .../report` |

Explain request bodies. Do not write his React.

SSE: Chandan’s `sse_generator` already exists. Your executor must call `update_progress` or his bar will sit at 0.

---

## Task 13 — Optional: AI explainer

**Blockers:** Both directions of migrate already work. If not, **skip this**.

`ai_explainer.py` already returns `None` when `USE_LOCAL_LLM=false` and already swallows errors. Only finish the TODO if Ollama is actually running. Never require it in the router.

---

## What you must not do

- Rewrite `jobs.py` (call it only)
- React, seed data, scoring rules, MySQL connector, Mongo writer
- Celery, Redis, PostgreSQL, Parquet
- Target writes inside dry run
