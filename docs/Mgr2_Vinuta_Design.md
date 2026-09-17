# SchemaShift Design Document — Mgr 2 (Vinuta)

**You are:** Vinuta, project lead and demo (Mgr 2).  
**You own:** seed data (MySQL + Mongo), dirty rows, README, the team tracker, demo script, slides, judge answers, rehearsal.

**Your first task:** [Task 1 — MySQL schema SQL](#task-1--first-task--mysql-schema-sql)  
Start Task 1 immediately. You do **not** wait for Chandan or Lavanya. You only wait on Kantraj when it is time to **load** data into Docker (Task 4).

---

## How to use this document

1. Do tasks **in this order**.
2. **Blockers** say when Kantraj or a developer must finish something first.
3. You write data and demo words. You do not write the migration engine or the React wizard.
4. If SQL fails to load, you fix SQL. If compose volumes are wrong, **Kantraj** fixes compose.

## Rules

- Same shop domain in **both** databases: Customer → Orders → Items, plus Products.
- Include **dirty rows**. Dry run and profiling must have something to show.
- README: no Gemini key, Ollama optional.
- Demo story: *we decide relational vs document, then prove the move* — not “we copied MySQL to Mongo”.

## Files you own

| File | Why |
|---|---|
| `seed/sample_mysql_schema.sql` | Tables + FKs |
| `seed/sample_mysql_data.sql` | ~10k rows + dirty rows |
| `seed/sample_mongo_customers.json` | Nested customers |
| `README.md` | Setup + demo steps |
| Demo script / slides (wherever the team keeps them, e.g. `docs/` or a shared deck) | Spoken demo |

You may add `seed/generate_mysql_data.py` and `seed/generate_mongo_data.py` to build the large files. Those generator scripts are yours too.

## Task order at a glance

| Order | Task | Blocked by |
|---|---|---|
| **1 FIRST** | MySQL schema SQL | None |
| 2 | MySQL data ~10k + dirty rows | Task 1 |
| 3 | Mongo nested JSON | Task 1 (same field names as MySQL). Not blocked by Docker |
| 4 | Load into Docker and verify | **Kantraj Task 1** (compose up). Mongo load also needs **Kantraj Task 2** (mongo-seed service) |
| 5 | README | Can start after Task 1; finish after Task 4 commands are known |
| 6 | Shared tracker | None. Start on Day 1 morning |
| 7 | Demo script (exact words) | Best after Path A works; you can draft from this doc now |
| 8 | Slides | After Task 7 outline |
| 9 | Judge answers | None. Use the table in this document |
| 10 | Rehearsal + fallback recording | **Kantraj Task 11** QA and developers’ E2E. Do not wait to **draft** the script |

---

## Task 1 — FIRST TASK — MySQL schema SQL

**Do this first.**  
**Blockers:** None.

### File

`seed/sample_mysql_schema.sql`

Replace the short draft that is already there. Compose mounts this as `01_schema.sql`.

### Procedure

Create **four** tables in database `demo` (Docker already creates the database). Use `AUTO_INCREMENT`. Do not use `SERIAL`.

```sql
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'paid',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

Put `CREATE TABLE` only in this file. No `INSERT` here.

These names (`customers`, `orders`, `order_items`, `products`) are what Chandan’s model tree and Lavanya’s transformer expect. Do not rename to `CUSTOMER` / `ORDER` even if the team plan used uppercase English words.

### Done when

The file has four tables and FKs as above, and it runs in MySQL 8 without errors.

---

## Task 2 — MySQL data (~10,000 rows + dirty rows)

**Do this after Task 1.**  
**Blockers:** None.

### File

`seed/sample_mysql_data.sql`  
Optional helper: `seed/generate_mysql_data.py` that **prints or writes** that SQL file.

### Procedure

Target counts (good enough, not exact):

| Table | Clean rows (about) |
|---|---|
| products | 50 |
| customers | 3,000 |
| orders | 6,000 |
| order_items | 12,000 |

That is more than enough for a 10k-row story. If generation is slow, 1,000 customers / 3,000 orders / 8,000 items is the minimum. Aim high.

**Clean data rules**

- Real-looking names and emails (`user{n}@example.com`)
- `order.customer_id` always exists
- `order_items.product_id` always exists
- `order.total` ≈ sum of its items (`quantity * price`)
- Dates between 2022-01-01 and 2025-12-31

**Dirty data (required — put these at the end of the file)**

Wrap dirty inserts with:

```sql
SET FOREIGN_KEY_CHECKS = 0;
SET SESSION sql_mode = '';
```

Then:

| Kind | How many | How to insert |
|---|---|---|
| Orphan orders | 40 | `customer_id = 999999` (no such customer) |
| Duplicate emails | 30 | extra customers that reuse an existing email |
| Invalid dates | 25 | `order_date = '0000-00-00'` or `'2023-13-40'` |
| Bad items | 20 | `quantity = 0` or `price` NULL if you temporarily allow it; if NOT NULL blocks you, use `quantity = -1` and describe it as invalid |

Then:

```sql
SET FOREIGN_KEY_CHECKS = 1;
```

Do **not** try to insert duplicate primary keys (MySQL will reject the whole script). Duplicate **email** is the duplicate-key story for the demo.

At the top of the data file, keep a comment the team can read:

```sql
-- Dirty rows: 40 orphan orders, 30 duplicate emails, 25 invalid dates, 20 bad items
```

Generate with a short Python script if you do not want to hand-write 10k lines. Run the script **once**, commit the SQL it wrote, so Docker does not need Python at startup.

### Done when

The SQL file exists, includes the dirty-row comment, and is large enough that profiling is not “4 rows”.

---

## Task 3 — Mongo nested customers JSON

**Do this after Task 1 (same field names).**  
**Blockers:** None for writing the file. Loading is Task 4.

### File

`seed/sample_mongo_customers.json`

It **must** be a JSON **array** `[ {...}, {...} ]` because Kantraj will `mongoimport --jsonArray`.

### Procedure

Each document:

```json
{
  "name": "Alice Smith",
  "email": "alice@example.com",
  "created_at": "2023-01-01T10:00:00Z",
  "orders": [
    {
      "order_date": "2023-02-01",
      "total": 100.5,
      "status": "paid",
      "items": [
        { "product_name": "Widget A", "sku": "W-A", "quantity": 2, "price": 25.0 }
      ]
    }
  ]
}
```

Generate ~3,000 documents (or at least 500). Same domain as MySQL so the reverse demo is comparable.

**Dirty Mongo documents (required)**

- 20 with `"email"` missing
- 20 with `"order_date": "not-a-date"`
- 20 with `"orders": []` and a note in a field `debug: "empty-orders"` (optional)
- 10 with duplicate emails

You may keep `_id` out and let Mongo assign ids. If you include `_id`, use Extended JSON only if `mongoimport` accepts it. Simpler: no `_id` field.

Replace the current 2-document file. It is only a stub.

Tell Kantraj the path is still `seed/sample_mongo_customers.json` so his `mongoimport` line does not break.

### Done when

The file is a JSON array, parses in a JSON validator, and has nested `orders[].items[]` plus dirty docs.

---

## Task 4 — Load into Docker and verify

**Do this after Tasks 1–3.**  
**Blockers:**

- **Kantraj Task 1** — `docker compose up` works.
- Mongo import — **Kantraj Task 2** (mongo-seed service). If that service is missing, ping him. Do not invent Redis. You may run `mongoimport` yourself once if you have Mongo tools:

```bash
mongoimport --host localhost --port 27017 --db demo_source --collection customers --file seed/sample_mongo_customers.json --jsonArray --drop
```

If MySQL still has **old** 4-row data after you changed SQL:

```bash
docker compose down -v
docker compose up --build
```

Volumes remember the first init. Kantraj’s document says the same thing.

### Procedure — verify MySQL

```sql
USE demo;
SHOW TABLES;                    -- customers, orders, order_items, products
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM orders WHERE customer_id = 999999;   -- expect 40 orphans
```

If `SHOW TABLES` is empty, compose did not mount your files. That is **Kantraj**. If tables exist but COUNT is tiny, your data file did not run or failed on a bad INSERT — that is **you**. Read `docker compose logs mysql-source`.

### Procedure — verify Mongo

```js
use demo_source
db.customers.countDocuments()
db.customers.findOne()
```

`findOne()` must show `orders` as an array of objects with `items`.

Tell Chandan and Lavanya in chat: “MySQL seed ready” / “Mongo seed ready” when counts look right.

### Done when

MySQL has thousands of rows plus orphans, Mongo has nested customers, and both developers have been told.

---

## Task 5 — README

**Do this after you know the compose commands (can draft during Task 1).**  
**Blockers:** None to write. Keep URLs matching Kantraj’s compose (8000, 5173, 3306, 3307, 27017).

### File

`README.md` (already exists — update it so it stays true)

### Procedure

README must contain, in this order:

1. One-paragraph product reminder (the “we don’t simply copy” text already at the top — keep it).
2. Prerequisites: Docker Desktop, Git. Python/Node only for local-without-Docker.
3. **No Gemini / OpenAI key.** `USE_LOCAL_LLM=false`.
4. Quick start:

```bash
cp .env.example .env
docker compose up --build
```

5. Table of URLs (API docs, UI, MySQL source, MySQL target, Mongo).
6. Demo flow numbered 1–10 (Connect through Final report) plus optional Mongo→MySQL.
7. Out of scope: PostgreSQL, SQL Server, Parquet, Celery, Redis, mandatory AI.

Do not tell judges to pull an Ollama model.

### Done when

A new teammate can start from README alone without asking you for ports.

---

## Task 6 — Shared tracker

**Do this on Day 1 morning (parallel with Task 1).**  
**Blockers:** None.

### Procedure

Create one board (GitHub Issues, Trello, or Notion — pick one, tell the team).

Columns: **To do / In progress / Blocked / Done**.

One card per task number from the four design docs, for example:

- Chandan T1 Connections + jobs
- Lavanya T1 Mongo connector
- Kantraj T1 Compose
- Vinuta T1 MySQL schema
- …

When someone is blocked, the card says **who** and **which task**, e.g. “Lavanya T5 blocked on Chandan T4 Mongo writer”.

Update the board at three times: end of Day 1, before the first rehearsal, and before demo.

### Done when

All four people can see their first task as In progress or Done without asking you in chat.

---

## Task 7 — Demo script (exact words, under 7 minutes)

**You can draft this now.**  
**Live rehearsal blocker:** working Path A (MySQL → Mongo). That needs Chandan Task 10 + Kantraj wiring. Do not wait to write the words.

### Procedure

Write a script the speaker can read. Time it by reading out loud. Cut sentences, not product steps.

**Suggested clock**

| Minutes | What you say and click |
|---|---|
| 0:00–0:30 | Problem: tools copy data; they do not choose the model or prove the move |
| 0:30–1:00 | Connect MySQL source + Mongo target (paste DSNs, test) |
| 1:00–1:40 | Discover: point at FK graph |
| 1:40–2:20 | Profile: “dirty rows, orphans, invalid dates; risk is Medium/High — that is **source quality**, not migration success” |
| 2:20–3:10 | Workload ticks: mostly reads + nested together. Recommendation: **document / Mongo**, confidence, **read two reasons out loud** |
| 3:10–3:40 | Model preview: nested Customer → orders → items |
| 3:40–4:20 | Dry run: “no writes; here are orphans and bad dates” |
| 4:20–4:40 | Approve (High risk checkbox if shown) |
| 4:40–5:20 | Progress bar |
| 5:20–6:20 | Validate: counts, aggregates, sample. **Say the risk number and the match % are different** |
| 6:20–6:50 | Final report download JSON |
| 6:50–7:00 | Stop. If time left: “same product, Mongo source, recommend MySQL” |

Line you must say:

> We inspect, we recommend relational vs document, we dry-run without writing, then we prove the target.

Do **not** centre the talk on PostgreSQL, Celery, or a live LLM.

### Done when

You can read the script in under 7 minutes with a timer.

---

## Task 8 — Slides

**Do this after the Task 7 outline exists.**  
**Blockers:** None.

### Procedure

Five slides only (add more only if you still have time):

1. **Problem** — copy tools do not choose the model or validate
2. **Solution** — inspect → recommend → dry-run → migrate → prove
3. **Live demo** — (you switch to the app; this slide is a title)
4. **Metrics** — risk before vs match % after, both directions if you have them
5. **Differentiator** — rule engine (not LLM), both directions, dry-run safety, validation split from profiling

No architecture aquarium of six databases.

### Done when

The deck can be presented without you improvising the story.

---

## Task 9 — Judge answers

**Do this in parallel whenever you have 30 minutes.**  
**Blockers:** None. Learn these answers.

| Question | Your short answer |
|---|---|
| Why not an existing migration tool? | Those tools move data. We decide *which model it should live in*, dry-run risk, then prove the target. |
| Why only MySQL and Mongo? | The MVP is the **relational vs document** decision. Two engines, both directions, in a weekend. |
| Why not PostgreSQL? | Same relational idea. It is a later connector on the same interface. We proved the workflow first. |
| How does recommendation work? | A **rule engine** scores FKs, joins, nested access, reads/writes, transactions. Then it maps relational → MySQL, document → Mongo. You can see the reason weights. |
| Does AI make the decision? | **No.** Optional Ollama only rewrites the explanation. If it is down, reasons still show. |
| How accurate? | Heuristic, on purpose, so you can see **why**. Not a trained model. |
| Is dry run safe? | Yes. It never calls the writer. Only migrate writes, after approval. |
| What if migrate fails halfway? | Batches retry a few times and are logged. User can cleanup/reset the target and rerun. No automatic distributed rollback. |
| How do you know it is correct? | Counts, aggregates, sample/checksum, relationships — **separate** from the source quality risk score. |
| Large data? | Demo is ~10k with sampled profiling and batch size 1000. Production would add workers, not a new product idea. |
| Production-ready? | No. Hackathon MVP. Modular connectors, but no auth, no secret encryption, no CDC. |

### Done when

You can answer those eleven without looking at notes.

---

## Task 10 — Rehearsal + fallback

**Do this when Path A runs on the demo machine.**  
**Blockers:** Kantraj QA + Chandan/Lavanya E2E for the live click-through. You can **record** fallback screenshots as soon as any step works; do not wait for perfection to start capturing.

### Procedure

1. Rehearse the script **twice** with a timer, full team.
2. Cut talking if you overflow 7 minutes. Do not cut dry-run or validation.
3. Fallback kit in a folder (for example `docs/demo-fallback/`):
   - Screenshot or clip of each of the 7 steps
   - One JSON report file
   - Prefer a recording of **both** directions if both work
4. Night before: `docker compose up --build` on the demo laptop. Do not pull an LLM model.

If live Docker fails on stage, play the recording and talk over it using the same script.

### Done when

Two timed rehearsals are done, and the fallback folder has at least one image per step plus a JSON report.

---

## What you must not do

- Backend Python or React features
- Changing `target_type` logic
- Making Ollama required in README
- Promising PostgreSQL, SQL Server, Parquet, or automatic rollback on stage
