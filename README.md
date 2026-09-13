# SchemaShift — Schema Migration Intelligence Platform

> We don't simply copy data from one database to another.
>
> We inspect the source, understand its data and workload, recommend whether a **relational or document** model is more appropriate, show the generated target model, let the user **approve or override**, dry-run the migration **without writing**, migrate in batches, and **prove** the result with validation (counts, aggregates, samples) — separate from the source data-quality risk score.

**MVP databases:** MySQL (relational) ↔ MongoDB (document), both directions.

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker Desktop | 4.x (or Rancher Desktop) |
| Git | 2.x |
| Python | 3.12.x *(local dev only)* |
| Node.js | 20 LTS *(local dev only)* |

No Gemini / OpenAI key is required. Ollama is **optional** — leave `USE_LOCAL_LLM=false`.

---

## Quick Start (Docker — recommended)

```bash
git clone https://github.com/your-org/schemashift.git
cd schemashift

cp .env.example .env          # edit passwords/keys if needed

docker compose up --build
```

Services after a successful start:

| URL / address | What |
|---|---|
| http://localhost:8000/docs | FastAPI OpenAPI explorer |
| http://localhost:5173 | React wizard UI |
| localhost:3306 | MySQL **source** (seeded with demo data) |
| localhost:3307 | MySQL **target** (empty — migration writes here) |
| localhost:27017 | MongoDB (`demo_source` + `migration_target`) |

```bash
# Run backend tests inside the container
docker compose exec backend pytest tests/ -v
```

---

## Local Dev (without Docker)

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env

uvicorn app.main:app --reload --port 8000
```

> Requires a running MySQL instance on port 3306 and MongoDB on 27017.
> Update the DSNs in `.env` to point at your local databases.

### Frontend

```bash
cd frontend
npm install
npm run dev          # Vite dev server → http://localhost:5173
```

---

## Demo Flow (5–7 min)

1. **Connect** — paste the MySQL source connection string
2. **Discover** — browse tables, columns, FK graph
3. **Profile** — view null rates, duplicates, orphan FKs, data volume
4. **Recommend** — rule engine scores relational vs document; shows confidence and reasons
5. **Model preview** — inspect generated MySQL DDL or nested MongoDB document shape
6. **Dry run** — see issues (invalid dates, orphans, duplicate keys) before any write
7. **Approve** — confirm (extra confirmation when profiling risk is High)
8. **Migrate** — batch progress via SSE; retry on failure; audit log
9. **Validate** — counts, aggregates, sample/checksum, relationship checks
10. **Final report** — quality before vs correctness after, downloadable JSON

*(Optional step 11: reconnect to MongoDB source → recommend relational → MySQL)*

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MYSQL_DSN` | *(compose override)* | MySQL source DSN |
| `TARGET_MYSQL_DSN` | *(compose override)* | MySQL target DSN |
| `DEMO_MONGO_SRC_URI` | *(compose override)* | MongoDB source URI |
| `BATCH_SIZE` | `1000` | Rows/docs per migration batch |
| `PROFILE_SAMPLE_SIZE` | `10000` | Max rows sampled for profiling |
| `USE_LOCAL_LLM` | `false` | Enable optional Ollama explanation |
| `OLLAMA_MODEL` | *(empty)* | Model tag to pull (e.g. `llama3`) |

---

## Project Structure

```
schemashift/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/          # FastAPI + Python 3.12
├── frontend/         # React 18 + Vite
└── seed/             # Demo SQL + JSON data
```

See [`docs/TechStack_and_Scaffolding 2.md`](docs/TechStack_and_Scaffolding%202.md) for the full architecture.

---

## Out of Scope (Hackathon MVP)

- PostgreSQL, SQL Server, Parquet
- Celery, Redis, distributed job queue
- Automatic rollback / CDC
- Mandatory Ollama or any cloud LLM
- Multi-user auth, encrypted secrets, production deployment
