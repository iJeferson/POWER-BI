from pathlib import Path
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_sqlite_url() -> str:
    return f"sqlite:///{(_ROOT / 'produtividade.db').as_posix()}"


def is_railway() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_ID"))


class Settings(BaseSettings):
    database_url: str = _default_sqlite_url()
    upload_dir: str = str(_ROOT / "data" / "uploads")
    cors_origins: str = "*"
    port: int = 8000

    model_config = {"env_file": str(_ROOT / ".env"), "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return is_railway()

    @property
    def database_kind(self) -> str:
        return "sqlite" if self.is_sqlite else "postgresql"

    def ensure_persistent_database(self) -> None:
        if self.is_production and self.is_sqlite:
            raise RuntimeError(
                "Produção no Railway exige DATABASE_URL do PostgreSQL. "
                "SQLite não persiste dados entre deploys. "
                "Vincule o plugin PostgreSQL e defina DATABASE_URL=${{Postgres.DATABASE_URL}}."
            )


settings = Settings()
