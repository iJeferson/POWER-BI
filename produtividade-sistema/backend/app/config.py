from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_sqlite_url() -> str:
    return f"sqlite:///{(_ROOT / 'produtividade.db').as_posix()}"


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


settings = Settings()
