from app.services.discovery import database_inspector
from app.services.migration.execute_gate import apply_target_collection


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, _query):
        return None

    def fetchall(self):
        return self.rows


class _MySQLConnection:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False

    def cursor(self):
        return _Cursor(self.rows)

    def close(self):
        self.closed = True


def test_list_mysql_databases_uses_credentials_without_selected_database(monkeypatch):
    connection = _MySQLConnection([
        {"Database": "sales"},
        {"Database": "analytics"},
    ])
    calls = {}

    def connect(**kwargs):
        calls.update(kwargs)
        return connection

    monkeypatch.setattr(database_inspector.pymysql, "connect", connect)
    databases = database_inspector.list_databases(
        "mysql", "mysql+pymysql://reader:secret@db.example:3307/previous"
    )

    assert databases == ["analytics", "sales"]
    assert calls["host"] == "db.example"
    assert calls["port"] == 3307
    assert calls["user"] == "reader"
    assert "database" not in calls
    assert connection.closed


def test_list_mongodb_databases_closes_client(monkeypatch):
    class Client:
        def __init__(self, _dsn, **_kwargs):
            self.closed = False

        def list_database_names(self):
            return ["zeta", "alpha"]

        def close(self):
            self.closed = True

    client = Client("mongodb://localhost")
    monkeypatch.setattr(database_inspector, "MongoClient", lambda *_args, **_kwargs: client)

    assert database_inspector.list_databases("mongodb", "mongodb://localhost/source") == ["alpha", "zeta"]
    assert client.closed


def test_inspect_connection_disconnects_after_listing(monkeypatch):
    class Connector:
        disconnected = False

        def connect(self):
            return None

        def list_entities(self):
            return ["customers"]

        def disconnect(self):
            self.disconnected = True

    connector = Connector()
    monkeypatch.setattr(database_inspector.ConnectorFactory, "get_connector", lambda *_args, **_kwargs: connector)

    result = database_inspector.inspect_connection("mysql", "mysql+pymysql://u:p@db:3306/store")

    assert result == {"database": "store", "entities": ["customers"]}
    assert connector.disconnected


def test_ensure_mysql_database_creates_target_if_missing(monkeypatch):
    statements = []

    class Cursor(_Cursor):
        def execute(self, query):
            statements.append(query)

    class Connection(_MySQLConnection):
        def cursor(self):
            return Cursor([])

        def commit(self):
            self.committed = True

    connection = Connection([])
    monkeypatch.setattr(database_inspector.pymysql, "connect", lambda **_kwargs: connection)

    database = database_inspector.ensure_mysql_database(
        "mysql+pymysql://root:root@localhost:3306/sales`archive"
    )

    assert database == "sales`archive"
    assert statements == ["CREATE DATABASE IF NOT EXISTS `sales``archive` CHARACTER SET utf8mb4"]
    assert connection.committed
    assert connection.closed


def test_ensure_mysql_database_requires_a_database_name():
    try:
        database_inspector.ensure_mysql_database("mysql+pymysql://root:root@localhost:3306/")
    except ValueError as exc:
        assert "must include a database name" in str(exc)
    else:
        raise AssertionError("a database-less target DSN must be rejected")


def test_apply_target_collection_changes_primary_tree_only():
    plan = {
        "target_type": "mongodb",
        "model_tree": {"from_table": "customers", "collection": "customers"},
        "model_trees": [
            {"from_table": "customers", "collection": "customers"},
            {"from_table": "products", "collection": "products"},
        ],
    }

    changed = apply_target_collection(plan, "client_records")

    assert changed["model_tree"]["collection"] == "client_records"
    assert changed["model_trees"][0]["collection"] == "client_records"
    assert changed["model_trees"][1]["collection"] == "products"
    assert plan["model_tree"]["collection"] == "customers"


def test_apply_target_collection_rejects_system_collections():
    try:
        apply_target_collection({"target_type": "mongodb"}, "system.users")
    except ValueError as exc:
        assert "non-system" in str(exc)
    else:
        raise AssertionError("system collection names must be rejected")


def test_compose_dsn_rewrite_uses_one_mysql_service(monkeypatch):
    from app.config import settings
    from app.services.discovery.dsn import resolve_dsn

    monkeypatch.setattr(settings, "docker_dsn_rewrite", True)

    assert resolve_dsn("mysql+pymysql://root:root@localhost:3307/target_db") == (
        "mysql+pymysql://root:root@mysql:3306/target_db"
    )


def test_compose_dsn_rewrite_maps_published_mongo_port_to_container_port(monkeypatch):
    from app.config import settings
    from app.services.discovery.dsn import resolve_dsn

    monkeypatch.setattr(settings, "docker_dsn_rewrite", True)

    assert resolve_dsn("mongodb://localhost:27018/source_db") == "mongodb://mongo:27017/source_db"