"""
config.py — Application settings loaded from environment variables via pydantic-settings.

All connection strings, feature flags, and tuning knobs live here.
Copy .env.example → .env and override values as needed.

Note on env_file resolution:
  pydantic-settings resolves .env relative to the *process* cwd.
  Run uvicorn from backend/ (e.g. `uvicorn app.main:app`) so ".env" is found.
  For Docker Compose the .env is injected via `env_file:` in compose.yml.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    secret_key: str = "change-me-in-production"
    sqlite_db_url: str = "sqlite:///./app_metadata.db"

    # ── Demo source ──────────────────────────────────────────────────────────
    demo_source_type: str = "mysql"  # "mysql" | "mongodb"
    demo_mysql_dsn: str = "mysql+pymysql://root:root@localhost:3306/demo"
    demo_mongo_src_uri: str = "mongodb://localhost:27017/demo_source"

    # ── Demo targets ─────────────────────────────────────────────────────────
    target_mysql_dsn: str = "mysql+pymysql://root:root@localhost:3307/migration_target"
    target_mongo_uri: str = "mongodb://localhost:27017"
    target_mongo_db: str = "migration_target"

    # ── Optional LLM ─────────────────────────────────────────────────────────
    use_local_llm: bool = False
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = ""

    # ── Migration / profiling ─────────────────────────────────────────────────
    batch_size: int = 1000
    profile_sample_size: int = 10_000


# Singleton used throughout the app
settings = Settings()
