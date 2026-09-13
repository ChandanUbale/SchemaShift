# Tech Stack & Project Scaffolding — Schema Migration Intelligence Platform

Hackathon implementation blueprint. This document describes **what the team will actually build for the MVP**, plus stretch/future items that must not leak into the first implementation.

---

## 1. Requirement Extraction

### Module: Discovery

> **Source is not limited to MySQL.** The engine is source-agnostic via pluggable connectors. The **hackathon MVP implements two sources**: MySQL (relational) and MongoDB (document). PostgreSQL and SQL Server share the same `BaseConnector` interface and are stretch/future — not MVP work.

| # | Requirement | Status |
|---|---|---|
| D1 | Accept a source connection for **MySQL** or **MongoDB** (MVP). Same UI/API shape so PostgreSQL / SQL Server can be added later. | ✅ MVP |
| D2 | For MySQL: discover tables, columns, data types, constraints, indexes, and foreign keys. Scan all schemas in scope. | ✅ MVP |
| D3 | For MongoDB: discover collections, field names, inferred types, and nested structure via schema sampling. | ✅ MVP |
| D4 | Infer relationships: FK graph for MySQL; embedded/reference patterns for MongoDB. | ✅ MVP |
| D5 | Estimate row/document counts and data volume per table/collection. | ✅ MVP |

**Defaults (resolved for MVP):**

- **D-Q1 — How is the connection provided?** UI form with a source-type selector (`mysql` | `mongodb`) and the matching connection-string field:
  - MySQL: `mysql+pymysql://user:pass@host:3306/dbname`
  - MongoDB: `mongodb://user:pass@host:27017/dbname`
- **D-Q2 — What is introspected?** All user tables/collections in the connected database. Skip system catalogs (`information_schema`, `performance_schema`, Mongo `system.*`).

---

### Module: Profiling

Profiling must be **good enough to feed recommendation and the dry-run report**. It is not a full enterprise data-quality platform.

| # | Requirement | Status |
|---|---|---|
| P1 | Profile null rates, distinct value counts, duplicates per column/field | ✅ MVP |
| P2 | Value range min/max per numeric/date column | ✅ MVP |
| P3 | Detect invalid dates, duplicate PKs, orphan FK records (relational); duplicate `_id` / broken references (Mongo) | ✅ MVP |
| P4 | Estimate source data volume and expected target storage (order-of-magnitude is enough) | ✅ MVP |

**Defaults (resolved for MVP):**

- **P-Q1 — Sample size:** Do **not** full-scan huge tables. Each connector implements `fetch_sample(n)`. Default `n = 10_000` (configurable `PROFILE_SAMPLE_SIZE`). MySQL may use `LIMIT` with `ORDER BY RAND()` or a row-count estimate; MongoDB uses `$sample`. Sampling logic lives **inside the connector**, not in shared SQL that only one database understands.
- **P-Q2 — Histograms / top-N:** Skip histograms in MVP. Top-N frequent values are optional and not required for the demo.

---

### Module: Recommendation

The engine does **not** choose among three similar SQL products. It answers one question:

> Would this workload be better as a **relational model** or a **document model**?

| # | Requirement | Status |
|---|---|---|
| R1 | Use schema + profiling + a simple workload form (read/write mix, joins, nested access, transactions) | ✅ MVP |
| R2 | Score **relational vs document**, then map: relational → **MySQL**, document → **MongoDB** | ✅ MVP |
| R3 | Produce explainable scoring: winner, confidence %, rule-based reasons | ✅ MVP |
| R4 | Generate the target model (MySQL DDL **or** nested MongoDB document shape) | ✅ MVP |

> **Two modes (keep both):**
> - **Auto (default):** Analyze → recommend relational or document → explain → user **approves or overrides** → only then can migration start.
> - **Manual:** User pre-selects MySQL or MongoDB on the connect/recommend screen and skips auto-scoring. Dry run, approval, migrate, and validate still run.

**Workload input (MVP):** A short structured form, not a real query log. Example options: mostly reads, frequent joins, nested/together access, transactional writes, analytical aggregations. Real query-log parsing is stretch/future.

**AI role:** Optional explanation only. See §5.

---

### Module: Migration

| # | Requirement | Status |
|---|---|---|
| M1 | Transform source data into the **approved** target model (relational ↔ document) | ✅ MVP |
| M2 | Dry run: detect issues **without writing to the target** | ✅ MVP |
| M3 | Batch migration with progress (SSE or WebSocket) | ✅ MVP |
| M4 | Retry failed batches; append-only audit log of migration events | ✅ MVP |
| M5 | User approval before migration; extra confirmation when profiling risk is High | ✅ MVP |
| M6 | Write to **MongoDB** when the approved target is document | ✅ MVP |
| M7 | Write to **MySQL** when the approved target is relational | ✅ MVP |

**Defaults (resolved for MVP):**

- **Batch size:** 1,000 rows/documents, configurable via `BATCH_SIZE`.
- **Same DB type is allowed:** e.g. MySQL → MySQL as **“Optimise in place”** (restructure schema). This must be an **explicit** user choice. Never write to the source connection by accident. Source DSN and target DSN must be stored separately; refuse to start if they resolve to the same database unless the user confirmed in-place optimisation.
- **Rollback:** No automatic rollback. Provide a **cleanup/reset target** action (drop migrated collections/tables for this job). Distributed rollback is future work.

---

### Module: Validation

Keep profiling risk and migration correctness **separate**. Do not fold them into one number.

| # | Requirement | Status |
|---|---|---|
| V1 | Record count comparison (source vs target) | ✅ MVP |
| V2 | Aggregate comparison (SUM/AVG of selected numeric fields) | ✅ MVP |
| V3 | Checksum / hash comparison on sampled rows | ✅ MVP |
| V4 | Relationship integrity (FK / references exist in target as modelled) | ✅ MVP |
| V5 | Random sampling match (N records spot-checked) | ✅ MVP |
| V6 | Final report: data quality **before**, migration stats, validation **after** | ✅ MVP |

**Defaults (resolved for MVP):**

- **Report format:** HTML in the UI + downloadable JSON. PDF is stretch.
- **Profiling risk (data quality before migrate):**  
  `risk_score = (invalid_records + orphan_records + duplicate_keys) / total_sampled_records * 100`  
  Labels: Low &lt; 1%, Medium &lt; 5%, High ≥ 5%.
- **Migration validation (correctness after migrate):** reported separately, e.g. records matched %, aggregate match yes/no, sample 100/100, relationship checks passed/failed.

---

## 2. Hackathon MVP Scope

### What we are building

A **Data Migration Intelligence Platform** (not a one-way converter).

```text
Connect source
  → Discover (read-only)
  → Profile (read-only)
  → Recommend relational vs document (no writes)
  → Generate target model
  → Dry run (no target writes)
  → User approves / overrides
  → Migrate in batches (only stage that writes to target)
  → Validate source vs target (read both)
  → Report
```

### MVP databases

| Role | MVP | Stretch | Future |
|---|---|---|---|
| **Source** | MySQL, MongoDB | PostgreSQL | SQL Server, other RDBMS |
| **Target** | MySQL, MongoDB | PostgreSQL | Parquet / data lake, Elasticsearch, etc. |

This is enough to demo **both directions**:

- MySQL shop schema → recommended **MongoDB** (nested Customer + orders)
- MongoDB nested documents + transactional/update-heavy form answers → recommended **MySQL** (normalized tables)

### Demo data

Seed ~10,000 rows/documents (Customer / Order / OrderItem / Product), plus a small set of **dirty rows** (invalid dates, duplicate keys, orphans) so dry run has something to show.

### Team (2 developers + 2 helpers)

| Person | Owns |
|---|---|
| Dev A | Inspect path: connectors, discovery, profiling, scoring, model generation |
| Dev B | Move path: transformer, writers, dry run, batch execute, validation, progress API |
| Helper 1 | Seed SQL/JSON, dirty data, README, demo script |
| Helper 2 | React wizard screens, copy, wiring to APIs |

Build order: scaffold + seed → discover + graph → profile → score + model → dry run → migrate + validate → report → Mongo-as-source (second direction). Do not start PostgreSQL, Celery, or Parquet until this path is demoable.

---

## 3. Architecture / Design Principles

### Hard write boundary (non-negotiable)

| Stage | Source | Target |
|---|---|---|
| Discovery | READ | no access |
| Profiling | READ | no access |
| Recommendation | none | none |
| Dry run | READ (sample) | **NO WRITES** |
| Migration | READ | **WRITES** (only after approval) |
| Validation | READ | READ |

- **Inspect does not write.** Discovery, profiling, scoring, and dry run must not call any `BaseWriter` method.
- **Recommend does not migrate.** Scoring cannot start a job.
- **Dry run does not write.** It transforms a sample in memory and returns issues.
- **Migration is the only stage that performs target writes.**
- **Validation happens after migration** and is read-only on both sides.

The demo line that matters: *“We inspect and detect problems before writing anything.”*

### Pluggable I/O (keep this)

Do **not** scatter MySQL- or Mongo-specific SQL/driver calls through profiling, scoring, or validation.

```text
source_type  → ConnectorFactory → MySQLConnector | MongoDBConnector
target_type  → WriterFactory    → MySQLWriter    | MongoWriter
```

MVP implements only those four classes. PostgreSQL / SQL Server / Parquet are additional classes on the **same interfaces**, not a redesign.

`BaseConnector` (minimum): `connect()`, `list_entities()`, `describe_entity()`, `fetch_sample(n)`, `fetch_batch(...)`, `estimate_counts()`.

`BaseWriter` (minimum): `prepare()`, `write_batch()`, `finalize()`. No `rollback()` required in MVP; cleanup/reset is a separate explicit action.

### Separate connections

- Store **source** and **target** as two records.
- Default target containers are distinct from the source (e.g. `mysql-source` vs `mysql-target`, or Mongo databases `demo_source` vs `migration_target`).
- In-place optimisation is opt-in only.

---

## 4. Tech Stack

### Language

| Choice | Justification |
|---|---|
| **Python 3.12** | Fastest iteration for discovery, profiling, and transforms at demo scale. |

Keep FastAPI + Python. Do not switch stacks mid-hackathon.

### Backend framework

| Choice | Justification |
|---|---|
| **FastAPI** | Small API surface, auto OpenAPI at `/docs`, native async, SSE or WebSocket for live progress. |

### Background work (MVP — no Celery, no Redis)

| Choice | Justification |
|---|---|
| **FastAPI background execution** + job row in SQLite | Demo is ~10,000 rows. Profiling, dry run, migrate, and validate can run in-process. Persist `job_id`, `status`, `progress_pct`, `error` in SQLite. Stream progress with **SSE** (preferred) or WebSocket. |

Celery + Redis are **not** in the MVP. They add a worker, a broker, and failure modes the team does not need at this scale. See §10.

Retry of a **failed batch** is in-process (re-run that batch a fixed number of times, log the outcome). It does not require a distributed queue.

### Source connectors (MVP)

| Source | Driver | Notes |
|---|---|---|
| **MySQL** | `pymysql` (or `mysql-connector-python`) | Catalog + sample/batch reads |
| **MongoDB** | `pymongo` | `$sample` + cursor batches |

Stretch/future (same `BaseConnector`, **do not add files in MVP tree**): PostgreSQL (`psycopg2`), SQL Server (`pyodbc`).

### Target writers (MVP)

The approved recommendation sets `target_type` to `mysql` or `mongodb`. `writer_factory` selects the writer.

| Target | Library | Notes |
|---|---|---|
| **MongoDB** | `pymongo` | `insert_many()` per batch |
| **MySQL** | `pymysql` | Batch insert |

**Parquet is not an MVP target.** Stretch/future only.

### Recommendation + optional AI

| Component | Choice | Role |
|---|---|---|
| **Decision** | Pure Python rule heuristic | Chooses relational vs document; confidence; reason codes |
| **Explanation** | Template from reason codes (always) | MVP always works |
| **Nicer prose** | **Optional** Ollama | Rewrites reasons; on timeout/error, keep template text |

See §5. Do not require an API key for the default path. Do not claim a specific model is fast on every CPU.

### Frontend

| Choice | Justification |
|---|---|
| **React 18 + Vite** | Wizard UI, fast refresh, SSE. |
| **Zustand** | Wizard/session state only. |
| **react-flow** | Schema / FK graph. |
| **recharts** | Simple profiling charts (optional if time is short; tables are enough). |

### Metadata / job state

| Choice | Justification |
|---|---|
| **SQLite via SQLAlchemy** | Jobs, profiles, plans, reports. Zero extra database container. Not for multi-user production; fine for hackathon. |

**MVP: connection strings are stored in SQLite for the demo. They are not encrypted.** Do not log passwords. Production secrets management is future work.

### Containerization

| Choice | Justification |
|---|---|
| **Docker Compose** | Reproducible judge environment: `docker compose up --build`. |

---

## 5. Recommendation Engine

### Decision (deterministic)

Score two **models**, then map to an MVP engine:

| Model score winner | MVP target |
|---|---|
| Relational | MySQL |
| Document | MongoDB |

Signals (keep weights simple and documented in `scoring_engine.py`):

- Number and depth of relationships / FK dependency
- Join or “fetched together” answers from the workload form
- Nested / embedded structure already present
- Read-heavy vs write-heavy
- Transactional / integrity needs
- Schema flexibility need
- Aggregation / scan-style access

Examples:

- High integrity + many joins + transactional writes → **MySQL**
- Nested access + fewer joins + read-heavy / flexible fields → **MongoDB**

Output JSON (always, even if Ollama is down):

```text
recommended_model: relational | document
target_type: mysql | mongodb
confidence: 0–100
reasons: [ { code, message, weight } ]
```

`model_generator.py` then emits either MySQL DDL **or** a nested MongoDB document tree from that result. It does **not** emit Parquet.

### LLM (optional, non-blocking)

```text
Rule engine → recommendation + score + reasons
                ↓
        Optional Ollama (short timeout)
                ↓
        Natural-language paragraph
```

If Ollama is not running, the model is missing, the request is slow, or it errors: **show the rule-based reasons**. Never block recommend, dry run, or migrate on the LLM.

- Primary optional runner: Ollama at `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`).
- Team picks a **small model that is actually pulled** on their machines. Do not treat any model name as guaranteed.
- `USE_LOCAL_LLM=false` (default) skips the call entirely.

A cloud LLM (Gemini/OpenAI) is **not** part of MVP setup. No `GEMINI_API_KEY` is required.

---

## 6. Migration & Validation

### Dry run

Uses Inspect only: sample rows → planned transform → issue list. **Zero target writes.**

Typical issues: invalid dates, duplicate keys, missing mandatory fields, orphans, type mappings that drop information.

### Execute

Runs only with `plan_id` + user approval.

1. Read batches from source connector  
2. Transform to approved model  
3. `write_batch` via target writer  
4. Retry a failed batch a small fixed number of times; log success/fail  
5. Push progress (`batches_done / batches_total`) over SSE  

Cleanup/reset: delete this job’s target tables/collections (or drop and recreate empty target DB). **No automatic distributed rollback.**

### Validation vs risk

**Profiling risk** = quality of source *before* migrate (Low / Medium / High).

**Migration validation** = correctness *after* migrate, shown separately, for example:

```text
Records matched:     99.8%
Aggregate matched:   Yes
Sample matched:      100 / 100
Relationship checks: Passed
```

Final report must include all three: (1) data quality before, (2) migration stats, (3) validation after.

---

## 7. Project Structure

Tree = **MVP files only**. Stretch connectors/writers are not created until needed.

```
data-migration-engine/
│
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, routers, SSE
│   │   ├── config.py               # pydantic-settings from .env
│   │   ├── database.py             # SQLAlchemy + SQLite
│   │   ├── jobs.py                 # In-process job runner + progress store
│   │   │
│   │   ├── models/                 # App metadata (not customer data)
│   │   │   ├── connection.py       # Source + target connection metadata / DSN (not encrypted)
│   │   │   ├── profiling.py        # ProfilingJob: status, results JSON
│   │   │   ├── migration.py        # MigrationJob: batches, progress, audit log
│   │   │   └── validation.py       # ValidationReport
│   │   │
│   │   ├── schemas/                # Pydantic API contracts
│   │   │   ├── connection.py
│   │   │   ├── profiling.py
│   │   │   ├── recommendation.py
│   │   │   ├── migration.py
│   │   │   └── validation.py
│   │   │
│   │   ├── routers/
│   │   │   ├── connections.py
│   │   │   ├── discovery.py
│   │   │   ├── profiling.py
│   │   │   ├── recommendation.py
│   │   │   ├── migration.py        # dry-run + execute + progress SSE
│   │   │   └── validation.py
│   │   │
│   │   └── services/
│   │       ├── discovery/
│   │       │   ├── base_connector.py
│   │       │   ├── mysql_connector.py
│   │       │   ├── mongodb_connector.py
│   │       │   ├── connector_factory.py
│   │       │   └── relationship_mapper.py
│   │       ├── profiling/
│   │       │   ├── column_profiler.py
│   │       │   ├── quality_checker.py
│   │       │   └── volume_estimator.py
│   │       ├── recommendation/
│   │       │   ├── scoring_engine.py    # relational vs document (the decision)
│   │       │   ├── model_generator.py   # MySQL DDL or Mongo document tree
│   │       │   └── ai_explainer.py      # optional Ollama; falls back to reason text
│   │       ├── migration/
│   │       │   ├── dry_runner.py        # no target writes
│   │       │   ├── transformer.py
│   │       │   ├── base_writer.py
│   │       │   ├── mysql_writer.py
│   │       │   ├── mongo_writer.py
│   │       │   ├── writer_factory.py
│   │       │   └── batch_executor.py    # batches, retries, audit; uses WriterFactory
│   │       └── validation/
│   │           ├── count_validator.py
│   │           ├── aggregate_validator.py
│   │           ├── checksum_validator.py
│   │           ├── relationship_validator.py
│   │           └── report_generator.py  # HTML + JSON
│   │
│   └── tests/
│       ├── test_discovery.py
│       ├── test_profiling.py
│       ├── test_recommendation.py
│       ├── test_migration.py
│       └── test_validation.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── store/
│       │   └── migrationStore.ts
│       ├── api/
│       │   └── client.ts
│       ├── components/
│       │   ├── ConnectionForm.tsx
│       │   ├── SchemaGraph.tsx
│       │   ├── ProfilingDashboard.tsx
│       │   ├── RecommendationCard.tsx
│       │   ├── ModelPreview.tsx
│       │   ├── DryRunReport.tsx
│       │   ├── MigrationProgress.tsx
│       │   ├── ValidationReport.tsx
│       │   └── FinalReport.tsx
│       └── pages/
│           ├── Step1_Connect.tsx
│           ├── Step2_Discover.tsx
│           ├── Step3_Profile.tsx
│           ├── Step4_Recommend.tsx
│           ├── Step5_DryRun.tsx
│           ├── Step6_Migrate.tsx
│           └── Step7_Validate.tsx
│
└── seed/
    ├── sample_mysql_schema.sql
    ├── sample_mysql_data.sql          # ~10k rows + dirty rows
    └── sample_mongo_customers.json       # nested docs for Mongo-as-source demo
```

There is **no** `worker.py`, Celery `tasks/` package, `postgresql_connector.py`, `sqlserver_connector.py`, or `postgresql_writer.py` in the MVP tree.

---

## 8. Environment Variables

`.env.example` at repo root — **MVP only**. Stretch keys stay commented and unused.

```env
# App metadata
SECRET_KEY=change-me-in-production
SQLITE_DB_URL=sqlite:///./app_metadata.db

# Demo source (overridden by the UI at runtime)
DEMO_SOURCE_TYPE=mysql
DEMO_MYSQL_DSN=mysql+pymysql://root:root@mysql-source:3306/demo
DEMO_MONGO_SRC_URI=mongodb://mongo:27017/demo_source

# Demo targets (engine writes to the approved one)
TARGET_MYSQL_DSN=mysql+pymysql://root:root@mysql-target:3306/migration_target
TARGET_MONGO_URI=mongodb://mongo:27017
TARGET_MONGO_DB=migration_target

# Optional LLM explanation (off by default)
USE_LOCAL_LLM=false
OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_MODEL=

# Migration / profiling
BATCH_SIZE=1000
PROFILE_SAMPLE_SIZE=10000
```

Do **not** require Redis, SQL Server, PostgreSQL, Gemini, or OpenAI keys for `docker compose up`.

---

## 9. Prerequisites, Setup, Docker Compose

### Tools

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12.x | Backend (local dev) |
| Node.js | 20 LTS | Frontend (local dev) |
| npm | 10.x | JS packages |
| Docker Desktop | 4.x | Compose demo (or Rancher Desktop if Desktop licensing is an issue) |
| Git | 2.x | Version control |

Ollama is **optional**. Install/pull a model only if you turn `USE_LOCAL_LLM=true`.

### Setup commands

```bash
git clone https://github.com/your-org/data-migration-engine.git
cd data-migration-engine
cp .env.example .env

docker compose up --build
```

Services after a successful start:

- `http://localhost:8000` — FastAPI (`/docs`)
- `http://localhost:5173` — React UI
- `localhost:3306` — MySQL **source** (seeded)
- `localhost:3307` — MySQL **target** (empty)
- `localhost:27017` — MongoDB (`demo_source` + `migration_target`)

```bash
# Optional tests
docker compose exec backend pytest tests/ -v

# Optional local API (without Docker)
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Optional local UI
cd frontend
npm install
npm run dev
```

There is no Gemini key step in the default setup.

### Docker Compose services (MVP)

```
services:
  backend:            # FastAPI, port 8000 (runs jobs in-process)
  frontend:           # Vite, port 5173
  mysql-source:       # MySQL 8, host 3306 — seeded demo source
  mysql-target:       # MySQL 8, host 3307 — empty relational target
  mongo:              # MongoDB 7, host 27017 — demo_source + migration_target

  # optional — uncomment only if USE_LOCAL_LLM=true
  # ollama:           # port 11434
```

No Redis. No Celery worker. No SQL Server. No PostgreSQL containers in the default compose file.

Judges should be able to connect to the seeded MySQL source immediately after `docker compose up --build`.

---

## 10. MVP vs Stretch / Future

| Item | Classification |
|---|---|
| Python 3.12, FastAPI, React 18, Vite, Zustand | **MVP** |
| SQLite metadata, Docker Compose | **MVP** |
| MySQL connector + writer | **MVP** |
| MongoDB connector + writer | **MVP** |
| BaseConnector / BaseWriter / factories | **MVP** |
| Rule-based relational vs document scoring | **MVP** |
| Target model generation (DDL or document tree) | **MVP** |
| Dry run, approval, batch migrate, retry, audit log | **MVP** |
| Cleanup/reset target | **MVP** |
| Validation (count, aggregate, sample checksum, relationships) | **MVP** |
| HTML + JSON report | **MVP** |
| FastAPI in-process jobs + SSE/WebSocket progress | **MVP** |
| Workload form (not query logs) | **MVP** |
| Ollama natural-language rewrite | **Optional enhancement** |
| PostgreSQL connector/writer | **Stretch** |
| SQL Server connector | **Future** |
| Parquet / columnar target | **Future** |
| Celery + Redis | **Future / production scaling** |
| Automatic rollback | **Future** |
| Real query-log / `pg_stat_statements` analysis | **Stretch / future** |
| Histograms / advanced statistical profiling | **Future** |
| PDF report | **Stretch** |
| Encrypted secrets, multi-user auth | **Future** |

### Future / production scaling (Celery + Redis)

Use a distributed worker **only if** jobs must survive API restarts, run for many minutes on large data, or scale across machines. That is not required for the ~10k-row hackathon demo. If added later, it wraps the same `services/` code; it does not replace connectors, scoring, or validation.

---

## 11. Verdict / Final Recommendation

| Decision | Choice | Why | Risk |
|---|---|---|---|
| Language | Python 3.12 | Data-heavy MVP, fast iteration | Low |
| API | FastAPI | Small surface, `/docs`, SSE | Low |
| Jobs | In-process + SQLite + SSE | Matches demo scale; no extra infra | Low — do not treat as production orchestration |
| Sources / targets | MySQL + Mongo only | Relational ↔ document story; two connectors, two writers | Low |
| Recommendation | Rules: relational vs document | Deterministic, explainable, demo-safe | Low |
| LLM | Optional Ollama | Must not block the wizard | Low if fallback is implemented |
| Frontend | React 18 + Vite + Zustand | Wizard + graph | Low |
| App DB | SQLite | No extra container | Low (single-user demo) |
| Compose | backend, frontend, 2× MySQL, 1× Mongo | One-command demo | Low |

**Go:** this stack covers every MVP module with free, well-known libraries. Implement MySQL+Mongo both directions, keep AI optional, keep Celery/PostgreSQL/SQL Server/Parquet out of the first build.

---

## 12. Out of Scope for Hackathon MVP

Do not start these during the hackathon unless the core demo (including Mongo → MySQL) is already working:

- SQL Server (source or target)
- PostgreSQL (unless explicitly taken as stretch after MVP)
- Parquet / data-lake target
- Automatic / distributed rollback
- Celery, Redis, or other production job orchestration
- Real query-log ingestion
- Advanced histograms, percentiles, full-table profiling of 150M-row databases
- Encrypted connection strings or enterprise secret managers
- Multi-user production deployment, SSO, RBAC
- Complex authentication beyond a local demo
- Paid cloud LLM as a required dependency
- CDC, zero-downtime, live dual-write

---

## 13. Why this MVP is still strong

Strength is **not** how many databases you list. Strength is the workflow judges can see end to end:

1. Connect to source (MySQL *or* Mongo)  
2. Discover structure  
3. Profile data quality  
4. Capture workload characteristics  
5. Recommend **relational vs document** (rules, not the LLM)  
6. Explain why (rules always; nicer prose if Ollama is up)  
7. Generate the target model  
8. Dry-run and show problems **before any target write**  
9. User approves or overrides  
10. Migrate in batches with live progress  
11. Validate source vs target (counts, aggregates, sample, relationships)  
12. Report: quality before, migration stats, correctness after  

That is the product. Fewer engines, same intelligence.

---

## 14. Zero-cost & license notes (MVP)

Dependencies below are the ones the MVP actually uses. All are free for typical hackathon/personal use as of this document. Confirm current licenses if your organisation has extra constraints.

| Dependency | License (typical) | Notes |
|---|---|---|
| Python 3.12, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic | OSI-style (PSF/MIT/BSD) | Free |
| SQLite | Public domain | Built-in |
| `pymysql` | MIT | Free |
| `pymongo` | Apache 2.0 | Free |
| MySQL 8, MongoDB 7 (Docker) | GPL / SSPL | Fine to run locally; SSPL restricts offering Mongo as a hosted service |
| React, Vite, Zustand, react-flow, Axios | MIT | Free |
| Docker Engine | Apache 2.0 | Free |
| Docker Desktop | Docker subscription terms | Free for personal/hackathon under Desktop’s small-org rules; otherwise Rancher Desktop |
| Ollama + chosen model | Optional | Only if the team enables local LLM; not required to run the app |

---

## 15. Consistency checklist (for implementers)

If something below appears in code or docs, it is **wrong for this MVP**:

- Celery, Redis, `worker.py`, `app/tasks/`
- SQL Server / PostgreSQL as required sources or targets
- Parquet as a generated or written target
- Gemini/OpenAI key as a setup prerequisite
- LLM choosing `target_type`
- Dry run or recommend calling `BaseWriter.write_batch`
- “Encrypted” connection strings
- Scoring Mongo vs MySQL vs PostgreSQL as three peer products
- Automatic rollback

If something below is missing, the MVP is incomplete:

- `BaseConnector` / `ConnectorFactory` / MySQL + Mongo readers  
- `BaseWriter` / `WriterFactory` / MySQL + Mongo writers  
- Rule scoring → `mysql` | `mongodb`  
- Dry run with no writes  
- Separate profiling risk vs validation results  
- In-process jobs + progress  
- Distinct source vs target connections  
