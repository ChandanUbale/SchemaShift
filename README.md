# SchemaShift — Schema Migration Intelligence Platform

> We don't simply copy data from one database to another.
>
> Connect to a source, discover its schema, choose entities, rehearse the migration without writing, migrate in batches, and validate the result.

**MVP databases:** MySQL (relational) ↔ MongoDB (document), both directions.

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker Desktop | 4.x (or Rancher Desktop) |
| Git | 2.x |
| Python | 3.12.x *(local dev only)* |
| Node.js | 20 LTS *(local dev only)* |

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
| localhost:3306 | One shared MySQL instance; select existing source and target databases in the UI |
| localhost:27017 | One shared MongoDB instance; select existing databases/collections in the UI |

No sample databases or records are loaded. If omitted, the target database name defaults to the selected source database. A missing MySQL target database is created during target connection, so the target account needs permission to create databases. MongoDB creates its target database when migration first creates/writes a collection. Use different source and target databases.

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

## Migration Flow

1. **Connect** — choose MySQL or MongoDB, enter a connection string, discover and select the source database, then connect and inspect the target
2. **Discover** — review entity-specific relationship graphs and select all or specific tables/collections
3. **Dry run** — generate a plan from the discovered schema and review sample transformation issues; no writes
4. **Migrate** — approve and start batch migration; progress and audit log are shown
5. **Validate** — compare selected source and target counts, aggregates, samples, and relationships

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` for local Compose | Password for the local MySQL service |
| `BATCH_SIZE` | `1000` | Rows/docs per migration batch |
| `DRY_RUN_SAMPLE_SIZE` | `10000` | Max rows/docs sampled during dry run |

---

## Project Structure

```
schemashift/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/          # FastAPI + Python 3.12
├── frontend/         # React 18 + Vite
```

See [`docs/TechStack_and_Scaffolding 2.md`](docs/TechStack_and_Scaffolding%202.md) for the full architecture.

---

## Out of Scope (Hackathon MVP)

- PostgreSQL, SQL Server, Parquet
- Celery, Redis, distributed job queue
- Automatic rollback / CDC
- Multi-user auth, encrypted secrets, production deployment
