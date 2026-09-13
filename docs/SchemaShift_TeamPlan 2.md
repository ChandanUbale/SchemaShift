# SchemaShift — Team Organization & Work Distribution

> **Team size:** 4 people — 2 full developers (Dev 1, Dev 2) + 2 semi-technical (Mgr 1, Mgr 2)
>
> **Source of truth for architecture and MVP scope:** `TechStack_and_Scaffolding.md`. If this plan and that document disagree, follow the scaffolding document.

---

## Product reminder (so tasks stay aligned)

SchemaShift is **not** a one-way MySQL→Mongo copier.

We inspect the source, understand its data and workload, recommend whether a **relational or document** model is more appropriate, show the target model, let the user approve or override, dry-run the migration, migrate in batches, and prove the result with validation.

**MVP databases:** MySQL + MongoDB, **both directions**.

```text
Connect → Discover → Profile → Recommend → Generate model
  → Dry Run → User Approval / Override → Migrate → Validate → Final Report
```

**Hard boundaries (everyone follows these):**

| Stage | Writes to target? |
|---|---|
| Discovery, Profiling | No (source read-only) |
| Recommendation | No |
| Dry run | **No** |
| Migration | **Yes** — only after approval; only stage that writes |
| Validation | No (reads source + target) |

Source and target connections are stored separately. In-place optimisation is an **explicit** user choice, never an accident.

**AI:** Rule engine decides. Optional Ollama only rewrites the explanation. If Ollama is down, rule-based reasons still show. Do not spend critical hours debugging an LLM.

---

## Team Roles

| Person | Role Title | Skill Level | Primary Focus |
|---|---|---|---|
| **Dev 1** | Full-stack Developer | Full technical | Owns the **MySQL source + inspect** half: FastAPI/SQLite jobs, MySQL connector, discovery/profiling APIs, scoring, model generation, Mongo writer, count/aggregate validation |
| **Dev 2** | Full-stack Developer | Full technical | Owns the **MongoDB source + move** half: Mongo connector, transformer, MySQL writer, dry run, batch execute, approval, sample/relationship validation, final report |
| **Mgr 1** | Frontend & QA | Semi-technical | React app + components, Docker Compose verification, end-to-end QA (both directions) |
| **Mgr 2** | Project Lead & Demo | Semi-technical | Seed data (MySQL + Mongo), dirty rows, README, tracker, demo script, presentation, judge Qs |

Dev 1 and Dev 2 have the **same title and the same load**. They split the backend down the middle (one source type + half of inspect/move), not lead vs helper. Frontend stays with Mgr 1 so neither developer is also a full-time UI owner.

---

## Module Ownership Map

| Module | Owner | Supporter | Deliverable |
|---|---|---|---|
| **Infrastructure / Docker Compose** (backend, frontend, mysql-source, mysql-target, mongo; optional Ollama commented out) | Mgr 1 | Dev 1 + Dev 2 | `docker compose up --build` brings the MVP stack up. **No Redis, no Celery worker.** |
| **FastAPI application + SQLite job state + SSE** | Dev 1 | Dev 2 | API at `/docs`; in-process jobs with `job_id` / status / `progress_pct`; SSE endpoint Dev 2's executor can update |
| **MySQL connector** | Dev 1 | Dev 2 | `MySQLConnector`: schema, FKs, `fetch_sample`, `fetch_batch` |
| **MongoDB connector** | Dev 2 | Dev 1 | `MongoDBConnector`: collections, nested schema, `$sample` / batches — **required for Mongo → MySQL** |
| **Discovery** | Dev 1 | Dev 2 | Discovery API + `ConnectorFactory`. Dev 1 wires MySQL; Dev 2 plugs Mongo into the same factory |
| **Profiling** | Dev 1 | Mgr 2 (test data) | Profiling API: nulls, distinct, dupes, min/max, orphans, volume (sampled, default 10k) |
| **Recommendation scoring** | Dev 1 | Dev 2 | Deterministic **relational vs document** score → `recommended_model`, `target_type`, `confidence`, `reasons` |
| **Model generation** | Dev 1 | Dev 2 | MySQL DDL **or** nested Mongo document tree from the approved recommendation |
| **Optional AI explanation** | Either (if time) | — | `ai_explainer.py` only if enabled; always fall back to rule-based reasons. **Not a blocker.** |
| **Transformer** | Dev 2 | Dev 1 | Relational ↔ document mapping (both directions). Dev 1 agrees the model JSON shape on Day 1 |
| **MongoDB writer** | Dev 1 | Dev 2 | `MongoWriter` — target for the MySQL → Mongo path |
| **MySQL writer** | Dev 2 | Dev 1 | `MySQLWriter` — target for the Mongo → MySQL path |
| **Dry run** | Dev 2 | Dev 1 | Issue list from a sample transform; **zero target writes** |
| **Batch executor + approval + cleanup** | Dev 2 | Dev 1 | Batches, retry, audit log, cleanup/reset; uses Dev 1's job/SSE store |
| **Validation — counts + aggregates** | Dev 1 | Mgr 1 | Record counts and SUM/AVG vs source |
| **Validation — sample/checksum + relationships + report** | Dev 2 | Mgr 1 | Sample match, relationship checks, HTML + JSON report (includes Dev 1's count/aggregate) |
| **Frontend** (React skeleton + 7 steps + components) | Mgr 1 | Dev 1 + Dev 2 (API help only) | Ollama **not** required for the UI |
| **Seed / demo data** | Mgr 2 | Mgr 1 | MySQL shop schema **and** nested Mongo customers; dirty rows for dry run |
| **Testing & QA** | Mgr 1 | Dev 1 + Dev 2 | Happy path **both directions**; edge cases logged |
| **Demo script & presentation** | Mgr 2 | Everyone | 5–7 min flow rehearsed and timed; fallback screenshots/recording |

Do **not** assign MVP ownership for Redis, Celery, `worker.py`, PostgreSQL, SQL Server, or Parquet.

---

## What Each Person Does — Day by Day

### Dev 1 — Full-stack Developer

Day-1 handshake: agree `BaseConnector` / `BaseWriter` / plan JSON with Dev 2 before splitting.

**Day 1** 
- [ ] FastAPI skeleton (`main.py`, `config.py`, `database.py`, `jobs.py` — in-process, **not** `worker.py`)
- [ ] SQLite metadata + job/progress state (`status`, `progress_pct`, error)
- [ ] SSE (or job-status) endpoint so the UI can watch progress
- [ ] `BaseConnector` + `ConnectorFactory`
- [ ] `MySQLConnector` (schema, FKs, indexes, `fetch_sample`, `fetch_batch`)
- [ ] Discovery endpoint working for **MySQL**
- [ ] Start profiling (`column_profiler.py`, `quality_checker.py`, `volume_estimator.py`)
- [ ] `mongo_writer.py` (batch insert) so MySQL → Mongo can land on a target

**Day 2**
- [ ] Finish profiling API (nulls, distinct, dupes, min/max, invalid dates, duplicate keys, orphans, volume)
- [ ] `scoring_engine.py`: **relational vs document** → `recommended_model`, `target_type`, `confidence`, `reasons`
- [ ] `model_generator.py` (MySQL DDL or Mongo document tree — **no Parquet**)
- [ ] Source vs target safety (refuse same DSN unless explicit in-place optimisation)
- [ ] Count + aggregate validators (feed Dev 2's report)
- [ ] Pair with Dev 2 to close **MySQL → MongoDB** end-to-end
- [ ] Answer Mgr 1's API questions for Steps 1–4 (connect, discover, profile, recommend)

**Do not work on in MVP:** SQL Server, PostgreSQL, Celery, Redis, Parquet. Do not take over React — that is Mgr 1.

---

### Dev 2 — Full-stack Developer

Day-1 handshake: same interfaces as above.

**Day 1** 
- [ ] `MongoDBConnector` (collections, nested field inference, `$sample`, batches)
- [ ] Plug Mongo into `ConnectorFactory` so discovery works for **MongoDB**
- [ ] `BaseWriter` + `WriterFactory`
- [ ] `mysql_writer.py` (batch insert)
- [ ] `transformer.py` — relational → document first (document → relational skeleton)
- [ ] `batch_executor.py` skeleton (loop + write_batch; hook Dev 1's job store)
- [ ] Prove source → transform → Mongo writer using Dev 1's MySQL connector + Mongo writer

**Day 2**
- [ ] Finish transformer **document → relational**
- [ ] `dry_runner.py` — sample transform + issues; **ZERO target writes**
- [ ] Approval / override gate; extra confirm when profiling risk is High
- [ ] Batch retry, audit log, cleanup/reset (no automatic rollback)
- [ ] Sample/checksum + relationship validators; `report_generator.py` (HTML + JSON) combining Dev 1's count/aggregate
- [ ] Pair with Dev 1 to close **MongoDB → MySQL** end-to-end
- [ ] Answer Mgr 1's API questions for Steps 5–7 (dry run, migrate, validate)
- [ ] Optional, **only if both directions work:** `ai_explainer.py` with rule-based fallback. Cut this first.

**Do not make Ollama a blocking task. Do not take over React — that is Mgr 1.**

---

### Mgr 1 — Semi Technical

**Day 1**
- [ ] Docker Compose for **MVP services only:** backend, frontend, `mysql-source`, `mysql-target`, `mongo`
- [ ] Confirm there is **no** Redis, **no** Celery worker, **no** SQL Server/PostgreSQL containers
- [ ] Ollama container stays **commented out / optional** — do **not** block Day 1 on a model download
- [ ] Verify `docker compose up --build`: API `:8000/docs`, UI `:5173`, MySQL source seeded, Mongo reachable
- [ ] Build `ConnectionForm.tsx` (source type: `mysql` \| `mongodb` + connection string; separate target connection)
- [ ] Set up React + Vite skeleton (`App.tsx`, routing, Zustand, Axios) — **Mgr 1 owns this**, not Dev 1/Dev 2
- [ ] Build `SchemaGraph.tsx` (react-flow tables/FKs **or** Mongo nested shape)
- [ ] Wire Step 1 (Connect) and Step 2 (Discover): Dev 1 for MySQL APIs, Dev 2 for Mongo APIs
- [ ] Help test **both** source connection paths (MySQL and Mongo)

**Day 2**
- [ ] `ProfilingDashboard.tsx` (tables/cards first; recharts only if time)
- [ ] `RecommendationCard.tsx` — winner, confidence, **rule-based reasons** (AI prose is optional extra)
- [ ] `ModelPreview.tsx` (DDL tree or document tree)
- [ ] `DryRunReport.tsx` (issue list)
- [ ] `MigrationProgress.tsx` (SSE if Dev 1's job endpoint is ready; otherwise poll job status)
- [ ] `ValidationReport.tsx` + `FinalReport.tsx` (risk before vs match % after — do not mix into one number)
- [ ] End-to-end QA: all 7 steps
  - [ ] MySQL → MongoDB (Dev 1's path)
  - [ ] MongoDB → MySQL (Dev 2's path)
- [ ] Log bugs; both developers fix their half
- [ ] Frontend must work **without** Ollama

---

### Mgr 2 — Semi Technical

**Day 1**
- [ ] `seed/sample_mysql_schema.sql` — CUSTOMER, ORDER, ORDER_ITEM, PRODUCT with FKs
- [ ] `seed/sample_mysql_data.sql` — ~10,000 realistic rows **plus dirty rows** (invalid dates, duplicate keys, orphans / missing required fields) so dry run is impressive
- [ ] `seed/sample_mongo_customers.json` — nested Customer → orders[] → items[] (same domain) for **Mongo-as-source**
- [ ] Load MySQL seed into `mysql-source`; load Mongo seed into `demo_source`; verify both
- [ ] Track progress on a shared board (Notion / Trello / GitHub Issues)
- [ ] Write `README.md` (setup, no Gemini key, Ollama optional, demo steps)

**Day 2**
- [ ] Demo script: exact words for Connect → Discover → Profile → Recommend (why relational vs document) → Model → Dry run → Approve → Progress → Validate → Report
- [ ] Slides: problem → solution → live demo → metrics → differentiator
- [ ] Time the demo: under 7 minutes
- [ ] Rehearse with the team at least twice
- [ ] Fallback: screenshots or a recording of each step if live demo fails
- [ ] Prepare judge answers (see below)
- [ ] Story to tell: *we decide relational vs document, then prove the move* — not PostgreSQL/SQL Server/Parquet/Celery/mandatory AI

---

## Dependency Order — Build in This Sequence

Parallel work is marked. **Ollama is not on this critical path.**

```
1. Repo + Docker Compose MVP skeleton (Mgr 1)          ← everyone needs this
       │
2. FastAPI + SQLite job/progress state (Dev 1)         ← backend needs this first
       │
3. Seed MySQL + MongoDB demo data (Mgr 2)              ← can overlap with 2
       │
4. BaseConnector + MySQL connector (Dev 1)
       │
5. MongoDB connector (Dev 2)                           ← parallel with 4 after interfaces exist
       │
6. Discovery APIs (Dev 1 MySQL + Dev 2 Mongo)          ║ Frontend Steps 1–2 (Mgr 1)  ← parallel
       │
7. Profiling (Dev 1)
       │
8. Recommendation scoring (Dev 1)                      ← relational vs document
       │
9. Target model generation (Dev 1)
       │
10. Transformer (Dev 2)                                ← can start once schema shape is known
       │
11. Mongo writer (Dev 1) + MySQL writer (Dev 2)        ← parallel
       │
12. Dry run — no target writes (Dev 2)
       │
13. Approval + batch execute + retry + audit (Dev 2) using Dev 1 job/SSE
       │
14. Count + aggregate validation (Dev 1)
       │
15. Sample/relationship validation + final report (Dev 2)
       │
16. Remaining frontend steps 3–7 (Mgr 1)               ← parallel with 12–15; both Devs answer API questions
       │
17. E2E MySQL → MongoDB (Dev 1 + Dev 2)
       │
18. E2E MongoDB → MySQL (Dev 2 + Dev 1)
       │
19. QA both directions (Mgr 1)
       │
20. Demo rehearsal (Mgr 2 + everyone)

Optional anytime after 8, never blocking: Ollama explanation (either developer if spare time)
```

---

## Hackathon Timeline (Assuming 2-Day / 48-Hour Format)

Do **not** pull an Ollama model at H+0. Get an end-to-end migration working as early as possible.

### Day 1 — Build the core pipeline

**Day-1 bar:** MySQL → Discover → Profile → Recommend → Transform → write Mongo, at a basic level, visible in the API (and Step 1–2 in the UI if possible).

| Time | Milestone | Who |
|---|---|---|
| H+0 | Repo created; Docker Compose MVP up (backend, frontend, mysql-source, mysql-target, mongo). **No Redis/Celery. No mandatory Ollama.** | Mgr 1 |
| H+2 | FastAPI skeleton + SQLite jobs at `localhost:8000/docs` | Dev 1 |
| H+2 | MySQL seed loaded; Mongo nested seed loaded | Mgr 2 |
| H+4 | Discovery returns schema JSON for **MySQL** | Dev 1 |
| H+4 | React routing + Step 1 connection form (`mysql` \| `mongodb`) | Mgr 1 |
| H+4 | Mongo connector discovery working | Dev 2 |
| H+6 | Profiling endpoint returns column/collection stats | Dev 1 |
| H+6 | `SchemaGraph` for MySQL FK graph | Mgr 1 |
| H+8 | Recommendation returns relational vs document + `target_type` + confidence + reasons | Dev 1 |
| H+8 | Transformer + writers: relational rows → Mongo docs | Dev 1 (Mongo writer) + Dev 2 (transformer) |
| H+10 | MySQL writer ready; ProfilingDashboard / Mongo graph in UI | Dev 2 + Mgr 1 |
| H+12 | **End of Day 1 sync** — Steps 1–4 in browser; MySQL→Mongo transform proven via API | Everyone |

### Day 2 — Complete both directions, polish, demo

| Time | Milestone | Who |
|---|---|---|
| H+13 | Dry runner detects dirty seed issues; **no target writes** | Dev 2 |
| H+14 | Approval gate + batch migrate MySQL → Mongo + retry + audit + cleanup/reset | Dev 2 |
| H+14 | RecommendationCard + ModelPreview (rule-based reasons; Ollama only if spare time) | Mgr 1 |
| H+16 | SSE (or poll) progress + all 7 pages navigable | Dev 1 (SSE) + Mgr 1 |
| H+18 | Count + aggregate validation | Dev 1 |
| H+18 | Sample validation + FinalReport | Dev 2 + Mgr 1 |
| H+18 | **MongoDB → MySQL** path working | Dev 2 + Dev 1 |
| H+20 | Full E2E QA both directions; each developer fixes their half | Mgr 1 + Dev 1 + Dev 2 |
| H+22 | Demo script + slides done | Mgr 2 |
| H+24 | First full demo rehearsal (timed, &lt; 7 min) | Everyone |
| H+36 | Final demo rehearsal + fallback screenshots/recording checked | Everyone |
| H+48 | **Demo day** | Everyone |

**Not scheduled before the core MVP works:** PostgreSQL, SQL Server, Celery, Redis, Parquet, mandatory AI.

---

## MVP Cut Line — If Time Runs Short

> If you hit H+20 and things are behind, cut in this order. **Preserve the end-to-end intelligence story.**

**Never cut:** Discovery, Profiling, Recommendation, Dry run, Migration, Validation. That flow **is** the product.

| Cut | What to cut | Replace with |
|---|---|---|
| **Cut 1** | Optional Ollama explanation | Rule-based reason codes/text already returned by the scorer |
| **Cut 2** | Advanced validation (checksum + full relationship walk) | Keep **count + aggregate + basic sample** |
| **Cut 3** | Fancy charts (recharts) | Simple tables / cards |
| **Cut 4** | Advanced schema visualization | Simpler table list or model tree |
| **Cut 5** | Extra polish / animations / SSE niceties | Functional progress (poll job status if needed) |

**Only after** Connect→…→Report works (ideally **both directions**), consider stretch: PostgreSQL, SQL Server, Parquet, Celery/Redis, heavier profiling, PDF, automatic rollback.

**Two-way fallback (only if truly out of time):** Ship a complete MySQL → Mongo story **and** keep Mongo discovery + recommendation + a recorded or partial Mongo → MySQL path. Do **not** quietly turn the product into “we only copy MySQL to Mongo” unless there is no other option. Do not cut dry run or validation to save the second direction.

---

## Demo story — Mgr 2 uses this everywhere

Use this in the README, slides, live script, and judge answers:

> We don’t simply copy data from one database to another.
>
> We inspect the source, understand its data and workload, recommend whether a **relational or document** model is more appropriate, show the generated target model, let the user **approve or override**, dry-run the migration **without writing**, migrate in batches, and **prove** the result with validation (counts, aggregates, samples) — separate from the source data-quality risk score.

Live order (5–7 min):

1. Connect (MySQL sample)
2. Discover (tables + FKs)
3. Profile (dirty-data counts)
4. Recommendation (document → Mongo, confidence, **why**)
5. Generated nested model
6. Dry run (invalid dates, dupes, orphans)
7. User approval
8. Migration progress
9. Validation (match % vs profiling risk)
10. Final report
11. *(If time)* reconnect to Mongo sample → recommend relational → MySQL

Do **not** centre the demo on PostgreSQL, SQL Server, Parquet, Celery, Redis, or a live LLM.

---

## Likely Judge Questions — Mgr 2 Prep These Answers

| Question | Short answer to prepare |
|---|---|
| *"Why not just use an existing migration tool?"* | Existing tools move data. SchemaShift decides *where it should live and in which model*, shows the plan, dry-runs risk, then proves the target — before and after touching records. |
| *"Why only MySQL and MongoDB?"* | We focused the hackathon MVP on the **relational vs document** decision. Those two engines let us demonstrate **both directions** without spending the weekend on four database implementations. |
| *"Why not PostgreSQL?"* | PostgreSQL is the same *relational* idea, so it is a natural **stretch connector** on `BaseConnector` / `BaseWriter`. We proved the intelligence and the migrate/validate workflow first. |
| *"How does the recommendation work?"* | A **rule engine** scores measurable signals: relationships/FKs, join or nested access, read/write mix, transactional needs, schema flexibility. It picks relational vs document, then maps to MySQL or Mongo. The decision is deterministic and explainable. |
| *"Does AI make the decision?"* | **No.** AI is an optional explanation layer (Ollama). The rule engine chooses the target. If Ollama is unavailable, the same reason codes still display. |
| *"How accurate is the recommendation?"* | It is heuristic, not a trained model — by design, so judges can see **why**. Confidence % and reason weights are in the API and on the card. |
| *"Is dry run safe?"* | **Yes.** Dry run never calls the writer and performs **no target writes**. Migration is the only stage allowed to write, and only after approval. |
| *"What happens if the migration fails halfway?"* | Migration is batch-based. Failed batches are retried a small number of times and logged. The user can **clean/reset the target** and rerun. Automatic distributed rollback is future work. |
| *"How do you know the migration was correct?"* | We separate **source data-quality risk** from **post-migration validation**: record counts, aggregates, sampled/checksum compares, relationship checks, and a final report. |
| *"How do you handle very large datasets?"* | MVP is demo-scale (~10k rows) with sampled profiling and configurable `BATCH_SIZE`. Production would add distributed workers, not a different product idea. We did **not** put Celery/Redis in the hackathon critical path. |
| *"Is this production-ready?"* | **No.** It is a hackathon MVP. The architecture is modular (connectors, writers, inspect vs move), but production needs secrets management, auth, distributed jobs, rollback/CDC, and operational hardening. |

---

## Task tracking, rehearsal, fallback (keep doing these)

- **Mgr 2** keeps the shared board current (blocked / in progress / done) at each sync (end of Day 1, H+20, H+24).
- **Rehearse at least twice** with a timer. Cut talking, not product steps.
- **Fallback kit:** screenshot or screen-recording of each wizard step, plus a JSON report file, in case live Docker or a DB flake. Prefer a recording of **both** directions if you have them.
- **Demo machine:** run `docker compose up --build` the night before; do not depend on pulling an LLM model.

---

## Stretch / future — do not pick these up during the 48 hours unless the MVP is already demoable

- PostgreSQL connector/writer
- SQL Server
- Parquet target
- Celery + Redis
- Mandatory or blocking Ollama
- Automatic rollback
- PDF report
- Encrypted secrets, multi-user auth
