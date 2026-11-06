# SchemaShift user guide — start the app and migrate both ways

This is the operator guide for running SchemaShift and converting data.

- **MongoDB → MySQL** (document to SQL)
- **MySQL → MongoDB** (SQL to document)

It covers the **first-time install** and what you must start **every later session**.

The product inspects the source, recommends a model, dry-runs with **zero writes**, then copies into a **separate target**. The source database is never rewritten.

Supported engines: **MySQL** and **MongoDB** only.

---

## 1. What you will have running

| Piece | Address | Purpose |
|---|---|---|
| UI (wizard) | http://127.0.0.1:5173/ | 7-step migration UI |
| Backend API | http://127.0.0.1:8000/docs | FastAPI |
| MySQL source (demo) | `localhost:3306` database `demo` | Seeded shop tables |
| MySQL target | `localhost:3307` database `migration_target` | SQL copy is written here |
| MongoDB | `localhost:27017` | Local Mongo (`demo_source`, `migration_target`) |

**How to look at the data**

| Database | Tool | Not this tool |
|---|---|---|
| MongoDB (local or Atlas) | MongoDB Compass | — |
| MySQL (port 3306 or 3307) | MySQL Workbench, DBeaver, or HeidiSQL | Compass cannot open SQL |

---

## 2. First-time setup (do this once)

### 2.1 Install software

1. **Docker Desktop** — start it and wait until the engine is running.
2. **Node.js 20 LTS** — https://nodejs.org/
3. **Git**
4. Optional viewers:
   - **MongoDB Compass** for Mongo
   - **MySQL Workbench** or **DBeaver** for SQL

Python is not required if you run the backend in Docker (recommended).

### 2.2 Get the code

In PowerShell:

```powershell
cd C:\Users\LavanyaS\Source\repos
git clone https://github.com/ChandanUbale/SchemaShift.git
cd SchemaShift
```

If you already have the repo:

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
git pull
```

### 2.3 Create the env file

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
copy .env.example .env
```

You do not need to edit `.env` for the local Docker demo. Leave `USE_LOCAL_LLM=false`.

### 2.4 Install frontend packages (once per machine, or after `package.json` changes)

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift\frontend
npm install
cd ..
```

### 2.5 Build and start Docker services (first time is slower)

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
docker compose up --build -d mysql-source mysql-target mongo backend
```

Wait 30–60 seconds for MySQL health checks.

```powershell
docker compose ps
```

These should be **Up**:

- `schemashift-backend-1` — port 8000
- `schemashift-mysql-source-1` — port 3306
- `schemashift-mysql-target-1` — port 3307
- `schemashift-mongo-1` — port 27017

Check the API:

```powershell
curl.exe http://127.0.0.1:8000/docs
```

Or open http://127.0.0.1:8000/docs in a browser.

### 2.6 Start the UI (first time and every time)

Keep Docker running. In a **second** PowerShell window:

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Leave that window open. Open:

**http://127.0.0.1:5173/**

If 5173 is already in use:

```powershell
npm run dev -- --host 127.0.0.1 --port 5174
```

Then use http://127.0.0.1:5174/

You are ready to migrate. First-time install is finished.

---

## 3. Every later session (install is already done)

You do **not** run `npm install` or clone again unless dependencies or the repo changed.

### 3.1 Start

1. Start **Docker Desktop** and wait until it is ready.
2. Start databases + backend:

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
docker compose up -d mysql-source mysql-target mongo backend
```

3. Start the UI (new window, leave it open):

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

4. Open **http://127.0.0.1:5173/**

That is the full daily start: **Docker Desktop → `docker compose up -d` → `npm run dev` → browser**.

Use `docker compose up --build -d ...` again only after Docker/backend image changes, or if the backend container will not start.

### 3.2 Stop

- UI: in the frontend PowerShell window, press `Ctrl+C`.
- Docker (keeps database data):

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
docker compose stop
```

### 3.3 Optional: wipe local Docker databases

This deletes demo MySQL, target MySQL, and local Mongo volumes. Do not do this if you still need the SQL copy of a previous run.

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
docker compose down -v
```

Next start will recreate empty/seeded volumes (`demo` MySQL is re-seeded; `migration_target` starts empty).

---

## 4. Safety rules (both directions)

1. **Source is read-only.** SchemaShift inspects and copies. It does not convert the original database in place.
2. **Only Step 6 (Start migration) writes**, and only to the **target** you connected.
3. Leave **Optimise in place** **off**.
4. Dry run never contacts the target.
5. Source and target connection strings must be **different** databases.
6. Atlas / production Mongo used as **source** stays Mongo. SQL appears only in the MySQL target.
7. Compass views Mongo. Workbench/DBeaver views MySQL.

---

## 5. Connection strings you can paste

SchemaShift accepts **MySQL** or **MongoDB** for source and for target (any database name those engines can open — not only `customers` / `orders`).

### MongoDB (view in Compass)

| Place | Connection string |
|---|---|
| Local Docker demo source | `mongodb://localhost:27017/demo_source` |
| Local Docker Mongo target | `mongodb://localhost:27017/migration_target` |
| Atlas (any DB name, e.g. `xcap`) | `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/xcap` |

### MySQL (view in Workbench — not Compass)

| Place | Connection string in the UI | Workbench connection |
|---|---|---|
| Local Docker demo source | `mysql+pymysql://root:root@localhost:3306/demo` | host `localhost`, port **3306**, user `root`, password `root`, database `demo` |
| Local Docker SQL target | `mysql+pymysql://root:root@localhost:3307/migration_target` | host `localhost`, port **3307**, user `root`, password `root`, database `migration_target` |
| Remote / cloud MySQL | `mysql+pymysql://USER:PASS@HOST:3306/DATABASE` | same host, port, user, password, database |

The MySQL **database name in the URI must already exist**. Docker already created `demo` (3306) and `migration_target` (3307). Mongo creates the DB name on first write.

`localhost` in the UI is rewritten inside Docker to the compose services. A cloud hostname (Atlas, remote MySQL) is used as-is.

---

## 6. Path A — MySQL → MongoDB (SQL to document)

Use this to copy tables from MySQL into Mongo collections.

### 6.1 Demo (local shop)

1. Open http://127.0.0.1:5173/
2. **Step 1 Connect**
   - Click **MySQL** as the source type (not MongoDB).
   - Source string: `mysql+pymysql://root:root@localhost:3306/demo`
   - Target type: **MongoDB**
   - Target string: `mongodb://localhost:27017/migration_target`
   - **Optimise in place**: off
   - Click **Connect & inspect** (or Save / Test if the form asks).
3. **Step 2 Discover** — confirm tables such as `customers`, `orders`, `order_items`. Continue.
4. **Step 3 Profile** — read-only quality report. Continue with **Generate recommendation**.
5. **Step 4 Recommend** — the engine may prefer a document model. That is advice only.
   - To write Mongo, keep target as MongoDB (or set **Override target** to **MongoDB**).
   - Click **Continue to dry run**.
6. **Step 5 Dry run**
   - Click **Run dry run**.
   - Confirm **Target writes = 0**.
   - If you see **High risk**, tick **I understand the source data quality is High risk**.
   - Click **Approve & continue to migration**.
7. **Step 6 Migrate**
   - Click **Start migration**. This is the only write.
   - Wait until progress is 100%. Source MySQL is unchanged.
8. **Step 7 Validate & Report** — run validation, download JSON / view HTML if needed.

### 6.2 Any other MySQL database

Same steps. On Connect:

- Source: **MySQL** + that database’s `mysql+pymysql://...` string
- Target: **MongoDB** + `mongodb://localhost:27017/migration_target` **or** an Atlas URI with a **new** database name (do not reuse a source Atlas DB you want left untouched)

Every table becomes a Mongo collection of the same name. Nested `customers` → `orders` → `items` is used only when those three shop tables exist together; other tables still copy 1:1.

### 6.3 Where to see the Mongo result

Open **Compass**:

- Local: `mongodb://localhost:27017` → database **`migration_target`**
- Atlas: the database name you put in the target URI

You should see collections matching the MySQL table names (and nested `customers` documents for the shop demo).

---

## 7. Path B — MongoDB → MySQL (document to SQL)

Use this to copy collections from Mongo into MySQL tables. This is the path for Atlas `xcap` → local SQL.

### 7.1 Local demo Mongo → local SQL

1. Open http://127.0.0.1:5173/
2. **Step 1 Connect**
   - Click **MongoDB** as the source type (not MySQL).
   - Source: `mongodb://localhost:27017/demo_source`
   - Target type: **MySQL**
   - Target: `mysql+pymysql://root:root@localhost:3307/migration_target`
   - **Optimise in place**: off
   - **Connect & inspect**
3. Continue Discover → Profile → Recommend.
4. On Recommend, set **Override target for this job only** to **MySQL** (the scorer may still say “document model”; that does not rewrite Mongo).
5. Dry run → tick High risk if shown → Approve → **Start migration**.
6. Validate.

### 7.2 Atlas (or any Mongo DB) → local SQL

Same as 7.1, but source is your Atlas URI **including the database name**:

```text
mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/xcap
```

Target stays:

```text
mysql+pymysql://root:root@localhost:3307/migration_target
```

Click **MongoDB** on the source card. Do not leave source type as MySQL.

Expected result:

- Atlas `xcap` **stays Mongo** (Compass still shows the same collections).
- MySQL `migration_target` on port **3307** gets **one table per collection** (`mapping_categories`, `trayport_trades_xcap`, …). Nested objects/arrays are stored as JSON. `_id` becomes `id`.

### 7.3 Where to see the SQL result

Do **not** use Compass.

**MySQL Workbench / DBeaver**

- Host: `localhost`
- Port: **3307**
- User: `root`
- Password: `root`
- Database: `migration_target`

Then `SHOW TABLES` / browse rows.

**Docker Desktop**

1. Containers → **`schemashift-mysql-target-1`** (not backend, not mongo).
2. **Exec** tab:

```bash
mysql -uroot -proot migration_target
SHOW TABLES;
SELECT COUNT(*) FROM mapping_categories;
SELECT * FROM mapping_categories LIMIT 5;
```

**Files** in Docker Desktop are raw MySQL files, not a table browser.

### 7.4 If you already ran an old job that wrote 0 rows

The first shop-only job could leave leftover `customers` / `orders` / `order_items` in `migration_target`. Either:

- On Step 6 of that old job, click **Cleanup / reset target**, then run Path B again from Connect, or
- Ignore those three leftover demo tables and look at the `xcap` table names.

Do **not** click Cleanup after a successful copy unless you want the SQL tables dropped.

---

## 8. What each wizard step does

| Step | Writes? | What you do |
|---|---|---|
| 1 Connect | No | Pick MySQL or Mongo for **source** and **target**, paste URIs, connect |
| 2 Discover | No | Review collections/tables and relationships |
| 3 Profile | No | Read quality findings; continue even if High risk |
| 4 Recommend | No | Advice only. Set **Override** to the engine you actually connected as target |
| 5 Dry run | No | Must show **0 target writes**. Approve (tick High risk if required) |
| 6 Migrate | **Yes — target only** | **Start migration**. Watch row counts and audit |
| 7 Validate | No | Compare counts/samples; download report |

Refresh of the browser clears the in-page wizard. Start again from Connect (saved Docker data is unchanged).

---

## 9. Quick decision: which strings do I use?

| I want | Source type | Source string | Target type | Target string | View result with |
|---|---|---|---|---|---|
| Demo SQL → Mongo | MySQL | `mysql+pymysql://root:root@localhost:3306/demo` | MongoDB | `mongodb://localhost:27017/migration_target` | Compass |
| Demo Mongo → SQL | MongoDB | `mongodb://localhost:27017/demo_source` | MySQL | `mysql+pymysql://root:root@localhost:3307/migration_target` | Workbench port 3307 |
| Atlas Mongo → SQL | MongoDB | `mongodb+srv://.../your_db` | MySQL | `mysql+pymysql://root:root@localhost:3307/migration_target` | Workbench port 3307 |
| Any MySQL → Atlas Mongo | MySQL | that MySQL DSN | MongoDB | `mongodb+srv://.../a_new_db` | Compass |
| Any Mongo → any MySQL | MongoDB | that Mongo URI | MySQL | that MySQL DSN | Workbench |

Never set source and target to the same URI. Never use `xcap` as target if you need Atlas left unchanged.

---

## 10. Troubleshooting

| Symptom | What to do |
|---|---|
| Docker commands fail | Start Docker Desktop; wait until the engine is running |
| `docker compose ps` shows backend Exit | `docker compose logs backend --tail 80` then `docker compose up --build -d backend` |
| http://127.0.0.1:5173 will not open | Run `npm run dev` in `frontend`; only one Vite process |
| UI loads, Connect fails | Confirm http://127.0.0.1:8000/docs works. Use **127.0.0.1:5173**, not a random host |
| Connect refused on localhost MySQL/Mongo | Backend must be the **Docker** backend from compose (it rewrites localhost to compose hosts) |
| Source type still MySQL while pasting a Mongo URI | Click **MongoDB** on the source card first |
| Dry run sampled 0 / migrate wrote 0 | You are on an old backend. Restart `docker compose up -d backend` and run from Connect again |
| Compass shows no SQL tables | Correct — open Workbench on **port 3307** |
| Workbench on 3306 is empty of `xcap` tables | 3306 is the **demo source**. Converted SQL is **3307** / `migration_target` |
| Port 3306/3307/8000/27017 already in use | Stop the other program, or `docker compose down` then `up` again |
| Atlas connect error | Check user/password, `/database` on the URI, and Atlas Network Access (allow your IP) |

---

## 11. Cheatsheet (copy/paste)

**First time**

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
copy .env.example .env
cd frontend
npm install
cd ..
docker compose up --build -d mysql-source mysql-target mongo backend
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

**Every later day**

```powershell
cd C:\Users\LavanyaS\Source\repos\SchemaShift
docker compose up -d mysql-source mysql-target mongo backend
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

**Stop**

- Frontend window: `Ctrl+C`
- `docker compose stop`

**Open the app:** http://127.0.0.1:5173/
