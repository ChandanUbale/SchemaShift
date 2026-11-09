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

    # ── Migration / dry-run ───────────────────────────────────────────────────
    batch_size: int = 1000
    dry_run_sample_size: int = 10_000
    docker_dsn_rewrite: bool = False


# Singleton used throughout the app
settings = Settings()
