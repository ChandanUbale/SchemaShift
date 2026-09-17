# SchemaShift Design Document — Dev 1 (Chandan)

**You are:** Chandan, full-stack developer (Dev 1).  
**You own:** the inspect half — FastAPI jobs, MySQL source, discovery, profiling, scoring, model generation, Mongo writer, count/aggregate validation.

**Your first task:** [Task 1 — Handshake + Connections API + SQLite job persistence](#task-1--first-task--handshake--connections-api--sqlite-job-persistence)  
Start Task 1 this morning. Do not wait for other people’s code. You can type it as soon as the 15-minute handshake with Lavanya is done.

---

## How to use this document

1. Do tasks **in the order below**. Do not skip ahead.
2. Each task has **Blockers**. If it says a person must finish something, wait for that, then continue.
3. Follow the **Procedure** exactly. That is the design. Do not invent extra databases, Celery, Redis, or AI decisions.
4. When a task says **Done when**, that is your exit check.

## Rules you must never break

- Discovery, profiling, scoring, and model generation **must not write** to any target database.
- Only Lavanya’s batch executor may call `write_batch`. You implement `MongoWriter`, but you do not start a migration from scoring.
- The rule engine decides relational vs document. Ollama does not decide.
- Do not edit React files. That is Kantraj.
- Do not edit seed SQL/JSON. That is Vinuta.
- Do not edit `mongodb_connector.py`, `transformer.py`, `dry_runner.py`, `mysql_writer.py`, or `batch_executor.py`. Those are Lavanya.

## Files you own

| File | Why |
|---|---|
| `backend/app/jobs.py` | Job create / progress / SQLite persist |
| `backend/app/routers/connections.py` | Save and test source + target DSNs |
| `backend/app/routers/discovery.py` | MySQL discovery wiring (Lavanya plugs Mongo into the same endpoints) |
| `backend/app/routers/profiling.py` | Profiling job API |
| `backend/app/routers/recommendation.py` | Score + generate model |
| `backend/app/services/discovery/mysql_connector.py` | MySQL reads |
| `backend/app/services/discovery/relationship_mapper.py` | MySQL branch of the graph (Lavanya fills the Mongo branch) |
| `backend/app/services/profiling/*` | Column stats, quality, volume |
| `backend/app/services/recommendation/scoring_engine.py` | Relational vs document |
| `backend/app/services/recommendation/model_generator.py` | DDL or document tree |
| `backend/app/services/migration/mongo_writer.py` | Target writes for MySQL → Mongo |
| `backend/app/services/validation/count_validator.py` | Record counts |
| `backend/app/services/validation/aggregate_validator.py` | SUM/AVG |
| `backend/app/models/*` | Add `job_id` / plan table as this doc says |

## Task order at a glance

| Order | Task | Blocked by |
|---|---|---|
| **1 FIRST** | Handshake + connections + job persistence | None |
| 2 | MySQL connector | None to code. Live test needs Kantraj compose + Vinuta MySQL seed |
| 3 | Discovery API for MySQL + relationship graph (MySQL) | Task 2 |
| 4 | Mongo writer | None to code. Live test needs Kantraj Mongo service |
| 5 | Profiling services + profiling API | Task 2 and Task 3 |
| 6 | Scoring engine | Task 5 |
| 7 | Model generator | Task 6. Plan JSON must match the handshake |
| 8 | Source vs target safety | Task 1 |
| 9 | Count + aggregate validators | Task 2 |
| 10 | Pair with Lavanya: MySQL → Mongo end-to-end | Lavanya transformer + batch executor + your Tasks 2, 4, 7 |
| 11 | Answer Kantraj for UI Steps 1–4 | As he asks. Your APIs for those steps must exist (Tasks 1, 3, 5, 6, 7) |

---

## Shared contracts (agree with Lavanya in Task 1, then do not change)

Copy this block into the handshake. Both of you implement against **this shape only**.

### Schema JSON (what discovery returns)

```json
{
  "source_type": "mysql",
  "database": "demo",
  "entities": [
    {
      "name": "customers",
      "entity_kind": "table",
      "estimated_count": 10000,
      "columns": [
        {
          "name": "id",
          "data_type": "int",
          "nullable": false,
          "primary_key": true,
          "auto_increment": true
        }
      ],
      "indexes": [{ "name": "PRIMARY", "columns": ["id"], "unique": true }],
      "foreign_keys": [
        { "column": "customer_id", "ref_table": "customers", "ref_column": "id" }
      ],
      "nesting": []
    }
  ]
}
```

For Mongo, `entity_kind` is `"collection"`, `columns[].name` is a dotted path (`orders.items.price`), and `nesting` lists embedded arrays:

```json
"nesting": [
  { "path": "orders", "type": "array" },
  { "path": "orders.items", "type": "array" }
]
```

### Plan JSON (what recommendation stores; transformer and writers read this)

```json
{
  "plan_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "connection_id": 1,
  "recommended_model": "document",
  "target_type": "mongodb",
  "confidence": 78,
  "reasons": [
    { "code": "nested_embedded", "message": "Customer, orders, and items are accessed together.", "weight": -30 }
  ],
  "direction": "relational_to_document",
  "source_schema": {},
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

If the winner is relational:

- `recommended_model` = `"relational"`
- `target_type` = `"mysql"`
- `direction` = `"document_to_relational"`
- `generated_ddl` = full MySQL `CREATE TABLE` script using `AUTO_INCREMENT` (never `SERIAL`)
- `model_tree` = `null`
- Add `flatten`:

```json
"flatten": [
  { "table": "customers", "from_path": "$" },
  { "table": "orders", "from_path": "$.orders", "parent_fk": "customer_id" },
  { "table": "order_items", "from_path": "$.orders.items", "parent_fk": "order_id" }
]
```

Do not rename these keys after the handshake.

---

## Task 1 — FIRST TASK — Handshake + Connections API + SQLite job persistence

**Do this first.**  
**Blockers:** None. Talk to Lavanya for 15 minutes, then code immediately.

### Handshake (15 minutes, before you write code)

Sit with Lavanya (Dev 2). Confirm all three, then split:

1. Do **not** change method names on `BaseConnector` or `BaseWriter`. They are already correct.
2. Schema JSON and Plan JSON are the blocks above.
3. Job progress: Lavanya’s `batch_executor` will call `update_progress(job_id, pct)` from `app.jobs`. You make that function persist to SQLite.

After this talk, you implement the rest of Task 1. Lavanya starts her Task 1 (Mongo connector) in parallel.

### What this task builds

Kantraj’s Step 1 UI and every later job (profile, dry-run, migrate) need saved connections and a `job_id` they can poll.

### Files

- `backend/app/models/connection.py` (already exists)
- `backend/app/models/profiling.py`
- `backend/app/models/migration.py`
- `backend/app/jobs.py`
- `backend/app/routers/connections.py`
- `backend/app/routers/migration.py` — only the GET `/{job_id}/status` handler (SSE stream already works)

### Procedure

**A. Add `job_id` to profiling jobs**

`ProfilingJob` currently has only an integer `id`. The API uses a string `job_id`. Add:

```python
job_id = Column(String(36), unique=True, index=True, nullable=False)
```

Keep `MigrationJob.job_id` as it already is.

**B. Finish `jobs.py`**

`create_job(db, job_type, connection_id=None, **extra)` must:

1. Create `job_id = str(uuid.uuid4())`.
2. Put the same snapshot into `_progress_cache` (already there).
3. Insert a SQLite row:
   - `job_type == "profiling"` → `ProfilingJob(job_id=..., connection_id=..., status="pending")`
   - `job_type` in `("dry_run", "migration")` → `MigrationJob(job_id=..., status="pending", is_dry_run=(job_type=="dry_run"), ...)`
   - `job_type == "validation"` → you may reuse `MigrationJob` with a note in `audit_log`, or add `job_id` on `ValidationReport` later. For Task 1, persist dry-run/migration as `MigrationJob`.
4. `db.commit()` and return `job_id`.

`update_progress(job_id, progress_pct, status, error=None)` must:

1. Update `_progress_cache` (already there).
2. Update the matching SQLite row (`ProfilingJob` or `MigrationJob`) by `job_id`.
3. If you have no DB session in this function, open `SessionLocal()` inside `update_progress`, commit, close. Lavanya will call this from a background thread with no request session.

`get_job_status(job_id)` must:

1. Return cache if present.
2. Else load from SQLite and return `{job_id, status, progress_pct, error}` or `None`.

**C. Implement connections router — replace every `NotImplementedError`**

| Endpoint | Behaviour |
|---|---|
| `POST /api/connections/` | Insert `Connection` from `ConnectionCreate`. Return `ConnectionRead` (id, name, source_type, is_source). **Do not return the DSN.** |
| `GET /api/connections/` | List all rows as `ConnectionRead`. |
| `GET /api/connections/{id}` | One row or 404. |
| `DELETE /api/connections/{id}` | Delete or 404. |
| `POST /api/connections/{id}/test` | Load DSN. Time `ConnectorFactory.get_connector(...).connect()` then `disconnect()`. Return `{success, message, latency_ms}`. If connect fails, `success=false` and the error message. **Read-only.** |

How to build the connector from a saved row:

- `mysql` → `ConnectorFactory.get_connector("mysql", dsn)`
- `mongodb` → parse database name from the URI path (`mongodb://host:27017/demo_source` → `demo_source`). Call `ConnectorFactory.get_connector("mongodb", uri, db_name=db_name)`.

Until Task 2 / Lavanya Task 1 land, `connect()` will still raise. That is OK. CRUD must work today. Test endpoint will work as soon as connectors exist.

**D. Job status endpoint**

In `routers/migration.py`, implement `GET /api/migration/{job_id}/status`:

- Call `get_job_status(job_id)`.
- If missing → 404.
- Return `MigrationProgressResponse`. If batches are unknown, use `batches_done=0`, `batches_total=None`.

Leave SSE `GET /{job_id}/stream` as it is. It already uses `sse_generator`.

### Done when

- You can `POST /api/connections/` and `GET` the row in `/docs`.
- `create_job` writes a row you can see in SQLite.
- `GET /api/migration/{job_id}/status` returns the cache/DB status.
- Lavanya has the Plan JSON keys in writing (this document).

---

## Task 2 — MySQL connector

**Do this after Task 1.**  
**Blockers:** None to write code.  
**Live test blocker:** Kantraj must have `docker compose up` working, and Vinuta must have loaded MySQL seed into `mysql-source`. You can still write the class with a local MySQL if compose is not ready.

### File

`backend/app/services/discovery/mysql_connector.py`

### Procedure

Parse DSN `mysql+pymysql://user:pass@host:port/dbname` in `connect()` with `urllib.parse.urlparse`. Replace the scheme `mysql+pymysql` with `mysql` first so parsing works.

```text
user     = parsed.username
password = parsed.password or ""
host     = parsed.hostname
port     = parsed.port or 3306
database = parsed.path.lstrip("/")
```

Then `pymysql.connect(..., cursorclass=pymysql.cursors.DictCursor)`. Store on `self._conn`.

Implement each method:

**`list_entities`**

```sql
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME
```

Skip nothing else. There are no system tables in the demo database.

**`describe_entity(name)`** — return one entity object in the Schema JSON shape.

Columns:

```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
ORDER BY ORDINAL_POSITION
```

- `COLUMN_KEY = 'PRI'` → `primary_key: true`
- `EXTRA` contains `auto_increment` → `auto_increment: true`
- `IS_NULLABLE = 'YES'` → `nullable: true`

Foreign keys:

```sql
SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = %s
  AND REFERENCED_TABLE_NAME IS NOT NULL
```

Indexes:

```sql
SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
ORDER BY INDEX_NAME, SEQ_IN_INDEX
```

Group index columns by `INDEX_NAME`. `unique = (NON_UNIQUE == 0)`.

Set `nesting` to `[]` for MySQL.

**`fetch_sample(name, n)`**

```sql
SELECT * FROM `{name}` LIMIT %s
```

Identifier `{name}` must be a table from `list_entities` only. Never concatenate user SQL. Return `list[dict]`.

**`fetch_batch(name, offset, limit)`**

```sql
SELECT * FROM `{name}` LIMIT %s OFFSET %s
```

**`estimate_counts`**

```sql
SELECT TABLE_NAME, TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
```

Return `{table_name: int, ...}`.

**`disconnect`** — already correct. Keep it.

### Done when

`list_entities()` on the demo DB returns at least `customers`, `orders`, `order_items` (and `products` if Vinuta added it). `describe_entity("orders")` includes a foreign key to `customers`.

---

## Task 3 — Discovery API (MySQL) + relationship graph (MySQL)

**Do this after Task 2.**  
**Blockers:** Task 2 must work. Lavanya does **not** block you. She will use the same endpoints for Mongo later.

### Files

- `backend/app/routers/discovery.py`
- `backend/app/services/discovery/relationship_mapper.py`

### Procedure

**`POST /api/discovery/{connection_id}/discover`**

1. Load `Connection` or 404.
2. Open the matching connector (same rules as test connection).
3. `connect()`.
4. For each name in `list_entities()`: `describe_entity(name)` and set `estimated_count` from `estimate_counts()`.
5. Build Schema JSON (`source_type`, `database`, `entities`).
6. Save JSON on the connection row. Add a column if needed:

```python
# models/connection.py
schema_json = Column(JSON, nullable=True)
```

7. `disconnect()`. Return the Schema JSON.

**`GET /api/discovery/{connection_id}/schema`**

Return stored `schema_json` or 404 if discover was never run.

**`GET /api/discovery/{connection_id}/relationships`**

Call `RelationshipMapper.build_graph(schema_json, source_type)`.

**`RelationshipMapper.build_graph` — you implement the MySQL branch only**

Write the function as:

```python
if source_type == "mysql":
    return _graph_mysql(schema)
if source_type == "mongodb":
    return _graph_mongo(schema)  # Lavanya fills this; you leave a NotImplementedError for mongo
```

MySQL graph:

- One **node** per entity: `{ "id": table_name, "label": table_name, "columns": [column names] }`
- One **edge** per foreign key: `{ "source": child_table, "target": ref_table, "label": "column → ref_column" }`

Kantraj’s `SchemaGraph` will draw `nodes` + `edges`. Do not return react-flow objects with `position`. He will add positions.

Tell Lavanya when the function skeleton is in the file so she can add `_graph_mongo` without overwriting your MySQL branch.

### Done when

`POST /api/discovery/{id}/discover` on a MySQL connection returns tables, columns, and FKs. Relationships returns nodes and edges.

---

## Task 4 — Mongo writer

**Do this after Task 3, or in parallel with Task 3 if discovery is already returning JSON.**  
**Blockers:** None to write code. Live insert needs Kantraj’s Mongo container.

Lavanya’s batch executor will call this class. You must finish it before her “prove MySQL → Mongo” check.

### File

`backend/app/services/migration/mongo_writer.py`

### Procedure

`__init__(uri, db_name)` — already there.

**`prepare(plan)`**

1. `MongoClient(self.uri)`.
2. `self._db = self._client[self.db_name]`.
3. Ping: `self._client.admin.command("ping")`.
4. Read collection name from `plan["model_tree"]["collection"]` (default `"customers"`).
5. Store `self._collection_names = [that name]`. Do **not** drop existing data unless `cleanup` is called.

**`write_batch(rows, entity_name)`**

```python
if not rows:
    return 0
result = self._db[entity_name].insert_many(rows, ordered=False)
return len(result.inserted_ids)
```

**`finalize`**

Create a simple index if the plan has `name` or `email`:

```python
self._db[collection].create_index("email")
```

If index create fails because it exists, ignore.

**`cleanup(job_id)`**

Drop every name in `self._collection_names`:

```python
self._db[name].drop()
```

`WriterFactory` already returns `MongoWriter`. Do not change the factory unless `__init__` arguments are wrong. Factory currently calls `writer_cls(dsn, **kwargs)`, so Kantraj/Lavanya must pass `db_name=settings.target_mongo_db`.

### Done when

A 2-document `write_batch` into `migration_target.customers` is visible in MongoDB Compass or `mongosh`.

---

## Task 5 — Profiling services + profiling API

**Do this after Task 2 and Task 3.**  
**Blockers:** MySQL connector + discover must work so you have entity names. Vinuta’s dirty rows make the demo look good, but you can unit-test with small lists without her.

### Files

- `backend/app/services/profiling/column_profiler.py`
- `backend/app/services/profiling/quality_checker.py`
- `backend/app/services/profiling/volume_estimator.py`
- `backend/app/routers/profiling.py`

### Procedure

Profiling **never talks SQL itself**. It calls `connector.fetch_sample(entity, n)` and computes on Python lists. Default `n = settings.profile_sample_size` (10000).

**`ColumnProfiler.profile_column(name, values)`**

- `null_rate` = count of `None` / len(values). Empty list → 0.0
- `distinct_count` = number of unique non-null values
- `duplicate_count` = (non-null count) − distinct_count
- `min_value` / `max_value` = min/max of values that are `int`, `float`, or `datetime`/`date`. If none, `null`
- `invalid_dates` = `QualityChecker.detect_invalid_dates(values)`

**`ColumnProfiler.profile_table(rows)`**

Collect all keys across rows. For each key, `profile_column(key, [row.get(key) for row in rows])`. Return that list.

**`QualityChecker.detect_duplicate_pks(rows, pk_field)`**

Count how many rows have a `pk_field` value that appears more than once. If `pk_field` missing, return 0.

**`QualityChecker.detect_orphan_fks(child_rows, fk_field, parent_ids)`**

Count children whose `fk_field` is not `None` and not in `parent_ids`.

**`QualityChecker.detect_invalid_dates(values)`**

For each non-null value:

- If it is already a `date`/`datetime`, it is valid.
- If it is a string, try `datetime.fromisoformat(s.replace("Z", "+00:00"))`. Also reject `'0000-00-00'`.
- If parse fails, count 1.

Do **not** change `compute_risk_score` or `label_risk`. They are already correct:

- Low < 1%, Medium < 5%, High ≥ 5%.

**`VolumeEstimator.estimate_source_volume(counts, avg_row_bytes=512)`**

For each table: `estimated_bytes = count * avg_row_bytes`.  
`total_estimated_mb = total_bytes / 1_000_000`.

**`estimate_target_overhead(source_type, target_type, source_bytes)`**

- mysql → mongodb: `int(source_bytes * 1.4)` (embedding copies parent fields)
- mongodb → mysql: `int(source_bytes * 1.1)`
- same type: `source_bytes`

**Profiling API**

`POST /api/profiling/` body: `{ "connection_id": int, "sample_size": int | null }`

1. `job_id = create_job(db, "profiling", connection_id)`
2. `background_tasks.add_task(run_profiling, job_id, connection_id, sample_size)`
3. Return `{ "job_id": job_id }` with HTTP 202

`run_profiling` (new function in the router file or `services/profiling/runner.py`):

1. `update_progress(job_id, 0, RUNNING)`
2. Load connection, open connector, `connect()`
3. `counts = estimate_counts()`
4. For each entity, `fetch_sample`, `profile_table`
5. For MySQL orphans: for each FK, sample parent ids and `detect_orphan_fks`
6. Sum invalid_dates + orphan counts + duplicate PKs
7. `risk_score = QualityChecker.compute_risk_score(...)`
8. `risk_label = QualityChecker.label_risk(risk_score)`
9. Save full JSON on `ProfilingJob.results`
10. `update_progress(job_id, 100, DONE)`  
    On exception: `update_progress(job_id, 0, FAILED, error=str(exc))`

`GET /api/profiling/{job_id}` → `ProfilingResult` from the SQLite row (`status`, `risk_label`, `risk_score`, `tables`).

### Done when

Profiling a MySQL demo connection returns a risk label and per-column null/duplicate stats. Dirty seed rows should raise risk above Low if Vinuta loaded them.

---

## Task 6 — Scoring engine (relational vs document)

**Do this after Task 5.**  
**Blockers:** You need a profiling JSON + the workload form. You can unit-test with a fake dict before the API is wired.

### File

`backend/app/services/recommendation/scoring_engine.py`

### Procedure

Do **not** change `WEIGHTS`. Use them.

`ScoringEngine.score(profiling_result, workload)`:

1. `raw = 0`
2. `reasons = []`
3. For each signal below, if it fires, add the weight to `raw` and append `{code, message, weight}`.

| Signal | When it fires | Message to store |
|---|---|---|
| `high_fk_count` | total foreign_keys across entities ≥ 3 | "Several foreign keys. Relational integrity fits." |
| `normalized_schema` | source has ≥ 3 tables/collections and ≥ 1 FK | "Data is split across related tables." |
| `frequent_joins` | `workload["frequent_joins"]` is true | "Workload does frequent joins." |
| `transactional_writes` | `workload["transactional_writes"]` is true | "Writes need transactions." |
| `integrity_needs` | transactional_writes **or** high_fk_count | "Referential integrity matters." |
| `nested_embedded` | any entity `nesting` is non-empty **or** `workload["nested_together_access"]` | "Records are fetched as a nested document." |
| `few_joins` | `frequent_joins` is false | "Joins are uncommon." |
| `read_heavy` | `workload["mostly_reads"]` is true | "Read-heavy access favours embedding." |
| `flexible_fields` | source_type is mongodb **or** any column type is mixed/object | "Schema is flexible / nested." |
| `aggregation_scan` | `workload["analytical_aggregations"]` is true | "Aggregations / scans are common." |

4. If `raw >= 0`: `recommended_model = "relational"`, `target_type = "mysql"`  
   Else: `recommended_model = "document"`, `target_type = "mongodb"`
5. `confidence = min(100, max(50, 50 + abs(raw) // 2))`
6. Return `{recommended_model, target_type, confidence, reasons, raw_score}`.

Never call Ollama here.

### Done when

A shop schema (customers/orders/items + FKs) with `nested_together_access=true` and `mostly_reads=true` returns **document / mongodb**. The same schema with `frequent_joins=true` and `transactional_writes=true` returns **relational / mysql**.

---

## Task 7 — Model generator

**Do this after Task 6.**  
**Blockers:** Plan JSON keys must stay as the handshake. Lavanya’s transformer reads `model_tree` / `flatten` / `generated_ddl`.

### Files

- `backend/app/services/recommendation/model_generator.py`
- `backend/app/routers/recommendation.py`
- New model `backend/app/models/recommendation.py` (plan storage)

### Procedure

**New table `recommendation_plans`**

```python
class RecommendationPlan(Base):
    __tablename__ = "recommendation_plans"
    id = Column(Integer, primary_key=True)
    plan_id = Column(String(36), unique=True, nullable=False)
    connection_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**`ModelGenerator.generate(recommendation, source_schema)`**

If `recommended_model == "relational"`:

- Build `CREATE TABLE` for each entity. Use `AUTO_INCREMENT` for integer PKs. Add `FOREIGN KEY` lines from `foreign_keys`.
- If source is Mongo, emit tables from `flatten` paths: `customers`, `orders`, `order_items`.
- Return `{target_type, generated_ddl, model_tree: None, flatten: [...], direction: "document_to_relational"}`.

If `recommended_model == "document"`:

- Pick the table with no incoming FKs as the root (usually `customers`).
- Embed children: a table whose FK points at the parent becomes an array on the parent.
- Shop default if FKs are `orders.customer_id` and `order_items.order_id`: exactly the `model_tree` in the handshake.
- Return `{target_type, generated_ddl: None, model_tree: {...}, direction: "relational_to_document"}`.

**Router `POST /api/recommendation/`**

Body: `{ connection_id, workload }` matching `RecommendationRequest`.

1. Load latest successful `ProfilingJob` for that connection. If missing → 400 `"profile first"`.
2. Load `schema_json` from the connection. If missing → 400 `"discover first"`.
3. `rec = ScoringEngine.score(profiling.results, workload.model_dump())`
4. `model = ModelGenerator.generate(rec, schema_json)`
5. Optional: if `settings.use_local_llm` is true, call `ai_explainer.explain`. If it returns `None`, leave `ai_explanation` null. **Do not fail the request.**
6. `plan_id = uuid`. Save full plan JSON (rec + model + source_schema + connection_id + direction).
7. Return `RecommendationResult`.

**`GET /api/recommendation/{plan_id}`** — load payload or 404.

### Done when

POST recommend after profile returns `plan_id`, `reasons`, and either `generated_ddl` or `model_tree`. Saving and GET by `plan_id` works.

---

## Task 8 — Source vs target safety

**Do this after Task 1.** You may do it as soon as connections exist; it must be in place before Lavanya’s execute endpoint writes.

**Blockers:** None.

### Where to put it

Add `backend/app/services/migration/safety.py` with `assert_distinct_targets(source_dsn, target_dsn, in_place: bool) -> None`.

Lavanya will call this from `POST /api/migration/execute`. You write the helper so she does not invent a second rule.

### Procedure

Normalize each DSN to `(engine, host, port, database)`:

- MySQL: parsed host, port, database name
- Mongo: host, port, database name from URI path or `TARGET_MONGO_DB`

If `(host, port, database)` of source equals target **and** `in_place` is false → raise HTTP 400:

`"Source and target are the same database. Set in_place_optimisation=true to confirm."`

If they are equal and `in_place` is true → allow.

If they differ → allow.

Never write using the source connection object.

### Done when

A unit test (or a `/docs` execute call) with identical DSNs and `in_place_optimisation=false` is rejected.

---

## Task 9 — Count + aggregate validators

**Do this after Task 2.**  
**Blockers:** Connectors must be able to `estimate_counts` / sample. Lavanya’s report generator will **call your two classes**. She owns checksum, relationships, and HTML.

### Files

- `backend/app/services/validation/count_validator.py`
- `backend/app/services/validation/aggregate_validator.py`

### Procedure

**`CountValidator.validate(source_counts, target_counts)`**

- `total_source = sum(source_counts.values())`
- `total_target = sum(target_counts.values())`
- `match_pct = 0.0` if total_source == 0 else `round(min(total_source, total_target) / max(total_source, 1) * 100, 1)` — better: `round(total_target / total_source * 100, 1)` capped later in the UI.
- Use: `match_pct = round(100.0 * total_target / total_source, 1)` when `total_source > 0`, else `100.0` if both 0, else `0.0`.
- `per_entity`: for every name in the union of keys, `{source, target, match: source==target}`.

For MySQL → Mongo, names will not match 1:1 (4 tables vs 1 collection). Compare **grand total documents vs grand total root rows** plus put each name in `per_entity`. Do not fail the whole validator because names differ. The report will show both.

**`AggregateValidator.validate(source_connector, target_connector, numeric_fields, tolerance=0.001)`**

`numeric_fields` example: `{ "orders": ["total"], "order_items": ["price", "quantity"] }`.

For each table/field:

- Source: sample or SQL `SELECT SUM(col), AVG(col) FROM table`
- Target: same if MySQL; if Mongo, aggregate `$sum` / `$avg` on the dotted path (`orders.total`)

`match` is true when `abs(source_sum - target_sum) <= tolerance * max(abs(source_sum), 1)`.

Overall `"match":` true only if every field matches.

Keep this **read-only**.

Export a small helper Lavanya can call:

```python
def run_count_and_aggregate(source_connector, target_connector, numeric_fields) -> dict:
    return {
        "counts": CountValidator.validate(source_connector.estimate_counts(), target_connector.estimate_counts()),
        "aggregates": AggregateValidator.validate(source_connector, target_connector, numeric_fields),
    }
```

Tell Lavanya the function name when it exists.

### Done when

Equal fake dicts `{customers: 4}` vs `{customers: 4}` give `match_pct` 100. Unequal dicts do not.

---

## Task 10 — Pair with Lavanya: MySQL → Mongo end-to-end

**Do this after Tasks 2, 4, 7.**  
**Blockers:** Lavanya must have finished **transformer relational → document** and **batch executor** (her Tasks 4–5). You do not write those files.

### Procedure

1. Use Vinuta’s MySQL seed as source.
2. Target = Mongo `migration_target`.
3. Through API or a small script: connect → discover → profile → recommend (expect document) → (Lavanya) dry-run → approve → execute → your count validator.
4. If transform output shape is wrong, **you fix `model_tree`**. If insert fails, **you fix MongoWriter**. If loop/retry is wrong, **Lavanya fixes batch_executor**.
5. Answer Kantraj when Step 1–4 UI calls fail (payload shape, 404s, CORS).

### Done when

A MySQL shop source produces nested customer documents in Mongo, and counts are in the right order of magnitude.

---

## Task 11 — Support Kantraj (Steps 1–4)

**Blockers:** He will ask when his screens are ready. Do not take over `frontend/`.

APIs he will call, which you own:

| Step | Method | Path |
|---|---|---|
| 1 | POST/GET/POST test | `/api/connections/` |
| 2 | POST discover, GET relationships | `/api/discovery/...` |
| 3 | POST/GET | `/api/profiling/` |
| 4 | POST/GET | `/api/recommendation/` |

Return JSON that matches the Pydantic schemas. If the UI shows an empty graph, check that you return `{nodes, edges}` not a different key.

---

## What you must not do

- PostgreSQL, SQL Server, Parquet, Celery, Redis, `worker.py`
- React components
- Seed files
- Making Ollama required
- Calling `MongoWriter.write_batch` from discovery, profile, or recommend
