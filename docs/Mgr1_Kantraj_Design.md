# SchemaShift Design Document — Mgr 1 (Kantraj)

**You are:** Kantraj, frontend and QA (Mgr 1).  
**You own:** Docker Compose for the demo, the React 7-step wizard, and end-to-end QA in both directions.

**Your first task:** [Task 1 — Get Docker Compose running](#task-1--first-task--get-docker-compose-running)  
This is the **team’s first task**. Chandan, Lavanya, and Vinuta cannot live-test databases until this works. Start Task 1 before any UI polish.

---

## How to use this document

1. Do tasks **in this order**.
2. **Blockers** tell you which API Chandan or Lavanya must finish before you wire a screen. You may still **build the empty screen** while you wait. You must not fake a successful migrate.
3. Do not implement backend Python. Ask Chandan (Steps 1–4 APIs) or Lavanya (Steps 5–7 APIs).
4. Frontend must work with **Ollama off**. Never require an AI key.

## Rules

- Compose services are only: `backend`, `frontend`, `mysql-source`, `mysql-target`, `mongo`. No Redis. No Celery. No Postgres. No SQL Server.
- Keep the Ollama service **commented out**.
- Source connection and target connection are **two forms / two records**. Never reuse one DSN field for both.
- Profiling risk and validation match % are **two different numbers**. Never combine them into one score on the final screen.

## Files you own

| File | Why |
|---|---|
| `docker-compose.yml` | Demo stack |
| `frontend/src/App.tsx` | Wizard steps |
| `frontend/src/store/migrationStore.ts` | Session state |
| `frontend/src/api/client.ts` | Axios helpers |
| `frontend/src/pages/Step1_Connect.tsx` … `Step7_Validate.tsx` | Screens |
| `frontend/src/components/*.tsx` | Widgets for those screens |

You may add a **mongo-seed** service in compose so Vinuta’s JSON loads. That is compose work, not seed-content work. She writes the JSON; you mount it.

## Task order at a glance

| Order | Task | Blocked by |
|---|---|---|
| **1 FIRST** | Docker Compose up and healthy | None. Do this now |
| 2 | Mongo seed service in compose | **Vinuta Task 3** (the JSON file). You can prepare the compose snippet and wait for her file name |
| 3 | React wizard shell (layout, step state, axios) | Task 1 UI container running. No API blocker |
| 4 | Step 1 Connection form (source + target) | **Chandan Task 1** (POST `/api/connections`). You can draw the form first |
| 5 | Step 2 Discover + SchemaGraph | **Chandan Task 3** (MySQL graph) and **Lavanya Task 2** (Mongo graph). You can draw a stub graph first |
| 6 | Step 3 ProfilingDashboard | **Chandan Task 5** |
| 7 | Step 4 RecommendationCard + ModelPreview + workload form | **Chandan Task 6 and 7** |
| 8 | Step 5 DryRunReport + approve | **Lavanya Task 7 and 8** |
| 9 | Step 6 MigrationProgress (SSE or poll) | **Lavanya Task 5** + **Chandan Task 1** SSE |
| 10 | Step 7 ValidationReport + FinalReport | **Lavanya Task 10** (report) which needs **Chandan Task 9** (counts) |
| 11 | QA both directions + bug list | Vinuta seed loaded. Happy path needs both developers’ E2E (Chandan Task 10, Lavanya Task 11) |

---

## Task 1 — FIRST TASK — Get Docker Compose running

**Do this first. The rest of the team is waiting on this.**  
**Blockers:** None.

### File

`docker-compose.yml` (already created — you **verify and fix**, you do not redesign the stack)

### Procedure

1. Copy `.env.example` to `.env` at the repo root if it does not exist.
2. From the repo root run:

```bash
docker compose up --build
```

3. Wait until these are true:

| Check | Expect |
|---|---|
| http://localhost:8000/health | `{ "status": "ok" }` |
| http://localhost:8000/docs | FastAPI swagger |
| http://localhost:5173 | React page (even if it only says “SchemaShift Wizard”) |
| localhost:3306 | MySQL source. Database `demo` |
| localhost:3307 | MySQL target. Database `migration_target` |
| localhost:27017 | Mongo accepts a connection |

4. Confirm the file has **no** `redis`, **no** `celery`, **no** `postgres`, **no** `sqlserver` services.
5. Confirm `ollama` stays commented.
6. If backend crash-loops: paste logs to Chandan. If frontend will not start: you fix Dockerfile / `package.json`. If MySQL is unhealthy: check Vinuta’s SQL only after Task 1 containers themselves start. Invalid SQL can block `mysql-source`; if that happens, tell **Vinuta** — do not rewrite her domain. You may comment a broken seed volume **temporarily** so the empty MySQL still starts, then put the volume back when she fixes SQL.

Default DSNs you will type in the UI later:

- MySQL source: `mysql+pymysql://root:root@localhost:3306/demo`
- MySQL target: `mysql+pymysql://root:root@localhost:3307/migration_target`
- Mongo source: `mongodb://localhost:27017/demo_source`
- Mongo target: `mongodb://localhost:27017/migration_target`

Inside Docker, the backend already uses host names `mysql-source`, `mysql-target`, `mongo`. The **browser** cannot use those names. The form the judge types uses `localhost` as above.

### Done when

The six checks in the table pass on your machine. Tell the team in chat: “compose is up”.

---

## Task 2 — Load Mongo seed via Compose

**Do this after Task 1.**  
**Blockers:** **Vinuta Task 3** — file `seed/sample_mongo_customers.json` must exist and be a JSON **array**. MySQL seed is already mounted in compose (`01_schema.sql`, `02_data.sql`). You do not write those files.

### Procedure

MySQL: confirm `docker-compose.yml` still has:

```yaml
volumes:
  - ./seed/sample_mysql_schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
  - ./seed/sample_mysql_data.sql:/docker-entrypoint-initdb.d/02_data.sql
```

If Vinuta changes file names, update these two lines only.

Mongo does **not** auto-load JSON. Add a one-shot service (do not add Redis to do this):

```yaml
mongo-seed:
  image: mongo:7
  depends_on:
    - mongo
  volumes:
    - ./seed/sample_mongo_customers.json:/seed/customers.json:ro
  command: >
    bash -c "sleep 8 && mongoimport --host mongo --db demo_source --collection customers --file /seed/customers.json --jsonArray --drop"
  networks:
    - schemashift
```

If `mongoimport` is not in PATH on that image, use `mongosh` + a small `seed/mongo-init.js` that Vinuta can also own. Prefer `mongoimport` first.

**Reset note:** MySQL init scripts run **only on first volume create**. If seed SQL changes, you must:

```bash
docker compose down -v
docker compose up --build
```

Tell Vinuta this when she asks “why is my new SQL not loading?”

### Done when

`demo.customers` has rows in MySQL and `demo_source.customers` has documents in Mongo.

---

## Task 3 — React wizard shell

**Do this after Task 1 (can overlap Task 2).**  
**Blockers:** None from developers.

### Files

- `frontend/src/App.tsx`
- `frontend/src/store/migrationStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/index.css` (keep it simple)

### Procedure

Replace the dummy store with **exactly** these fields (names matter so Steps share state):

```ts
{
  currentStep: number,          // 1–7
  sourceConnectionId: number | null,
  targetConnectionId: number | null,
  sourceType: "mysql" | "mongodb" | null,
  targetType: "mysql" | "mongodb" | null,
  schema: any | null,
  relationships: { nodes: any[]; edges: any[] } | null,
  profilingJobId: string | null,
  profiling: any | null,        // includes risk_label, risk_score
  workload: {
    mostly_reads: boolean,
    frequent_joins: boolean,
    nested_together_access: boolean,
    transactional_writes: boolean,
    analytical_aggregations: boolean,
  },
  recommendation: any | null,   // includes plan_id, reasons, generated_ddl, model_tree
  dryRunJobId: string | null,
  dryRun: any | null,
  confirmHighRisk: boolean,
  overrideTarget: "mysql" | "mongodb" | null,
  inPlace: boolean,
  migrationJobId: string | null,
  migrationProgress: { status: string; progress_pct: number } | null,
  validation: any | null,
  finalReport: any | null,
}
```

Add setters for each group (`setSourceConnection`, `setSchema`, `setProfiling`, …).

`App.tsx`:

- Header: `SchemaShift` and steps 1–7 as a simple list. Current step is bold.
- Buttons: **Back** and **Next**. Next is disabled until that step’s “Done when” is true.
- Do not let the user jump to Step 6 without Step 5.

`client.ts`:

```ts
baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000"
```

Compose already sets `VITE_API_URL=http://localhost:8000`. Paths you call must include `/api/...`.

Add helpers (empty bodies until later tasks fill them):

- `createConnection`, `testConnection`
- `discover`, `getRelationships`
- `startProfiling`, `getProfiling`
- `recommend`
- `startDryRun`, `getMigrationStatus`
- `executeMigration`, `cleanupTarget`
- `startValidation`, `getReport`

### Done when

You can click through all 7 placeholder pages with Back/Next. No API required yet.

---

## Task 4 — Step 1 Connect

**Do this after Task 3.**  
**Blockers:** **Chandan Task 1** — `POST /api/connections/` and `POST /api/connections/{id}/test` must return 201/200, not `NotImplementedError`. You may layout the form while you wait.

### Files

- `components/ConnectionForm.tsx`
- `pages/Step1_Connect.tsx`

### Procedure

One screen, **two** connection cards: **Source** and **Target**.

Each card:

1. Name (text)
2. Type select: `mysql` | `mongodb`
3. DSN text box
4. Button **Test connection** → `POST /api/connections/{id}/test` after save, or save then test
5. Show success/fail and latency

Flow:

1. User fills source → **Save source** → `POST /api/connections/` with `is_source: true` → store `sourceConnectionId` and `sourceType`
2. User fills target → **Save target** → `is_source: false` → store `targetConnectionId` and `targetType`
3. Checkbox **Optimise in place** (default off). Store as `inPlace`. Warn in small text: “Only tick this if source and target are the same database.”
4. Enable **Next** only when both ids exist and at least the source test succeeded.

Do not put Ollama fields on this page.

### Done when

Saving MySQL source + Mongo target stores two ids and you can go to Step 2.

---

## Task 5 — Step 2 Discover + SchemaGraph

**Do this after Task 4.**  
**Blockers:**

- MySQL graph: **Chandan Task 3** (`POST /api/discovery/{id}/discover` and `GET .../relationships`)
- Mongo graph: **Lavanya Task 2** (same URLs, Mongo connection)

You can render an empty box until they finish.

### Files

- `pages/Step2_Discover.tsx`
- `components/SchemaGraph.tsx`

### Procedure

On entering Step 2 (or a **Discover** button):

1. `POST /api/discovery/{sourceConnectionId}/discover`
2. Save `schema` in the store
3. `GET /api/discovery/{sourceConnectionId}/relationships`
4. Save `relationships`

**SchemaGraph** using `reactflow` (already in `package.json`):

- Map each `nodes[]` item to a react-flow node `{ id, data: { label, columns }, position: { x, y } }`
- Give positions in a simple grid: `x = index * 220`, `y = 80`
- Map `edges[]` to `{ id, source, target, label }`
- Import `reactflow/dist/style.css`

Under the graph, list tables/collections as a plain HTML table (name + column count) so the demo still works if react-flow layout looks messy.

Enable **Next** when `schema.entities.length > 0`.

### Done when

MySQL source shows `customers` → `orders` → `order_items` as boxes with lines. Mongo source shows nested `orders` / `items`.

---

## Task 6 — Step 3 ProfilingDashboard

**Do this after Task 5.**  
**Blockers:** **Chandan Task 5** — `POST /api/profiling/` returns `job_id`, `GET /api/profiling/{job_id}` returns results.

### Files

- `pages/Step3_Profile.tsx`
- `components/ProfilingDashboard.tsx`

### Procedure

1. Button **Run profiling** → `POST /api/profiling/` `{ connection_id: sourceConnectionId }`
2. Poll `GET /api/profiling/{job_id}` every 1 second until `status` is `done` or `failed`
3. Store `profiling`

Dashboard (tables/cards, **no recharts required**):

- Big label: `Risk: LOW | MEDIUM | HIGH` and `risk_score`
- One card/table per entity: column, null_rate, distinct_count, duplicate_count, min, max, invalid_dates, orphan_fk_count

Enable **Next** when `profiling.status === "done"` (or when results exist).

If status is `failed`, show `error` and do not continue.

### Done when

Demo MySQL seed shows a non-empty table and a risk label. Dirty rows from Vinuta should make this look real.

---

## Task 7 — Step 4 Recommend + model preview

**Do this after Task 6.**  
**Blockers:** **Chandan Task 6 and Task 7** — `POST /api/recommendation/`.

### Files

- `pages/Step4_Recommend.tsx`
- `components/RecommendationCard.tsx`
- `components/ModelPreview.tsx`

### Procedure

**Workload form** (checkboxes, all default false):

- Mostly reads
- Frequent joins
- Nested / fetched-together access
- Transactional writes
- Analytical aggregations

Button **Get recommendation** →

```json
POST /api/recommendation/
{ "connection_id": <source>, "workload": { ...checkboxes } }
```

**RecommendationCard** shows:

- Winner: `relational` or `document`
- Engine: `mysql` or `mongodb`
- Confidence %
- List of `reasons[].message` (always)
- `ai_explanation` only if it is a non-empty string. If null, hide that paragraph. **Do not show an error if AI is missing.**

Optional: dropdown **Override target** (`keep recommendation` | `mysql` | `mongodb`) stored as `overrideTarget`.

**ModelPreview**

- If `generated_ddl` is a string: show it in a `<pre>`
- If `model_tree` is an object: `JSON.stringify(model_tree, null, 2)` in a `<pre>`

Enable **Next** when `recommendation.plan_id` exists.

### Done when

MySQL shop + “nested access” + “mostly reads” shows document / Mongo and a nested tree. Reasons are visible without Ollama.

---

## Task 8 — Step 5 Dry run + approve

**Do this after Task 7.**  
**Blockers:** **Lavanya Task 7** (dry-run API) and **Lavanya Task 8** (execute will refuse without dry-run). You still show the issues list on this page.

### Files

- `pages/Step5_DryRun.tsx`
- `components/DryRunReport.tsx`

### Procedure

Button **Run dry run** → `POST /api/migration/dry-run` `{ source_connection_id, plan_id }`

Poll job status until done. Show issues in a table:

| Table / collection | Issue type | Row count | Description |

Empty issues: show “No issues found on the sample.”

If `profiling.risk_label === "high"`: show a red checkbox **I understand the source data quality is High risk**. Store `confirmHighRisk`.

Primary button **Approve and continue** (this only moves to Step 6; the real write is Step 6). Enable it when dry-run status is `done`. If risk is high, also require the checkbox.

Text on screen: **“Dry run does not write to the target.”**

### Done when

Orphan / invalid date issues from Vinuta’s seed appear here, and Mongo/MySQL target is still empty if you check the DB.

---

## Task 9 — Step 6 Migrate

**Do this after Task 8.**  
**Blockers:** **Lavanya Task 5 and 8** (execute + batches). Progress bar: **Chandan Task 1** SSE. If SSE fails, poll `GET /api/migration/{job_id}/status` every 500ms. Polling is an allowed fallback. Do not block the page on EventSource.

### Files

- `pages/Step6_Migrate.tsx`
- `components/MigrationProgress.tsx`

### Procedure

Button **Start migration** →

```json
POST /api/migration/execute
{
  "job_id": "<dryRunJobId or unused>",
  "plan_id": "...",
  "source_connection_id": ...,
  "target_connection_id": ...,
  "override_recommendation": overrideTarget or null,
  "in_place_optimisation": inPlace,
  "confirm_high_risk": confirmHighRisk
}
```

If Lavanya did not add `confirm_high_risk` yet and the call 400s, show her error message and ping her. Do not remove the checkbox.

Progress:

1. Try `EventSource` on `http://localhost:8000/api/migration/{job_id}/stream`
2. On each `data:` JSON, set `progress_pct` and `status`
3. If EventSource errors, poll GET status instead

UI: a percentage bar, status text, and a simple list of audit log lines if the status payload includes them.

Optional button **Cleanup target** → `POST /api/migration/cleanup` `{ job_id, target_connection_id }` for retries.

Enable **Next** when `status === "done"`. If `failed`, show `error` and keep Next disabled.

### Done when

The bar moves from 0 to 100 on a real execute, and the target DB has new rows/docs.

---

## Task 10 — Step 7 Validate + final report

**Do this after Task 9.**  
**Blockers:** **Lavanya Task 10**. Counts inside that report come from **Chandan Task 9**. If the report API 404s, ping Lavanya, not Chandan, unless the missing piece is count numbers.

### Files

- `pages/Step7_Validate.tsx`
- `components/ValidationReport.tsx`
- `components/FinalReport.tsx`

### Procedure

Button **Run validation** → `POST /api/validation/` with `migration_job_id`, source id, target id.

Poll until done. Then `GET /api/validation/{id}/report`.

**FinalReport layout (three blocks, in this order):**

1. **Before — source data quality**  
   `risk_label` and `risk_score` only. Use `ProfilingDashboard` in read-only mode if you want.
2. **Migration stats**  
   records migrated, batches total, batches failed, duration
3. **After — correctness**  
   records matched %, aggregate matched yes/no, sample `100/100`, relationship passed/failed

Do **not** average risk with match %.

Button **Download JSON** — `JSON.stringify(finalReport, null, 2)` as a file `schemashift-report.json`.

Optional: link to `GET /api/validation/{id}/report.html`.

This is the last step. No Next button. Show **Done**.

### Done when

A judge can see High/Low risk in block 1 and 99% match in block 3 as two separate facts.

---

## Task 11 — End-to-end QA

**Do this after Steps 1–7 are wired.**  
**Blockers:** Vinuta seed in both DBs. Full success needs Chandan’s MySQL→Mongo path and Lavanya’s Mongo→MySQL path. If one direction is late, QA the finished direction and log the other as blocked.

### Procedure

Run both scripts **by hand**, like a judge. Write bugs in the shared board (Vinuta tracks it). Assign:

- UI bug → you fix
- Steps 1–4 API → Chandan
- Steps 5–7 API → Lavanya
- Seed looks wrong → Vinuta

**Path A — MySQL → Mongo (must work)**

1. Source MySQL `localhost:3306/demo`
2. Target Mongo `localhost:27017/migration_target`
3. Workload: tick **mostly reads** and **nested / together**
4. Expect recommendation **document / mongodb**
5. Dry run shows dirty-row issues
6. Approve, migrate, validate
7. Confirm documents in Mongo

**Path B — Mongo → MySQL**

1. Cleanup or use empty `migration_target` MySQL on 3307
2. Source Mongo `demo_source`
3. Workload: tick **frequent joins** and **transactional writes**
4. Expect **relational / mysql**
5. Dry run, approve, migrate, validate
6. Confirm tables on 3307

Also check:

- Frontend with `USE_LOCAL_LLM=false` (default)
- Next buttons disabled until the step finished
- Same-DSN without in-place is rejected

### Done when

You have a written bug list with owners, and Path A is green. Path B is green or explicitly blocked with the owner’s task number.

---

## What you must not do

- Python services, scoring, transformers
- Seed content (SQL/JSON rows)
- Uncomment Ollama to “make the UI work”
- Add Redis/Celery/Postgres containers
- Mix risk score and validation into one number
