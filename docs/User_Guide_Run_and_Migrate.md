# SchemaShift — Run and migrate

SchemaShift uses connections supplied in the UI. It does not create or load sample source data.

## Start with Docker Compose

From the repository root:

```powershell
Copy-Item .env.example .env
# Set MYSQL_ROOT_PASSWORD in .env before starting if you want a non-default local password.
docker compose up --build
```

Open the frontend at http://localhost:5173 and the API docs at http://localhost:8000/docs.

Compose starts one MySQL service on port 3306 and one MongoDB service on port 27017. The same MySQL or MongoDB server can be used as source or target, but use different database names. No sample data is loaded.

If the target database name is omitted, SchemaShift uses the selected source database name. For MySQL, it checks for the target database and creates it during target connection if missing; the target account needs permission to create databases. For MongoDB, the target database is materialized by MongoDB when migration first creates/writes a collection.

Example connection strings (replace credentials, host, port, and database names as appropriate):

- MySQL: `mysql+pymysql://USER:PASSWORD@localhost:3306/DATABASE`
- MongoDB: `mongodb://USER:PASSWORD@localhost:27017/DATABASE`
- MongoDB Atlas: `mongodb+srv://USER:PASSWORD@HOST/DATABASE`

For local Compose connections, the backend maps `localhost` MySQL DSNs to the shared `mysql` service and MongoDB DSNs to the shared `mongo` service. Remote hostnames are used as supplied.

## Connect and migrate

1. Select MySQL or MongoDB as the source and enter its connection string.
2. Select **Discover databases**, then choose the source database.
3. Connect the selected source.
4. Enter the target connection string. The target engine is fixed to the opposite engine.
5. The target database name defaults to the selected source database. Enter a different one if desired. A missing MySQL target database is created during connection. For MongoDB, the target database is created on first migration write; optionally set the output collection name.
6. Select **Connect & inspect target**. This checks connectivity and lists existing tables or collections. For MySQL, it also creates the target database if it does not exist.
7. Continue through discovery, dry run, migration approval, and validation. The migration step is the only one that writes data to the target.

Use a least-privilege source account with permission to list databases and read metadata/data. Use a target account with only the permissions needed for migration. Do not use the same source and target database.

## Run locally without Compose

Start the backend from `backend/` with its virtual environment activated, and start the frontend from `frontend/` using `npm run dev`. Configure connection strings in the UI to point to reachable database servers.
