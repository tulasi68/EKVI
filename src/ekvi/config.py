from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EKVI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://ekvi:ekvi@localhost:5432/ekvi"
    database_url_sync: str = "postgresql://ekvi:ekvi@localhost:5432/ekvi"

    storage_backend: str = "local"
    storage_local_path: str = "./data/object_store"

    queue_backend: str = "memory"

    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    max_upload_size_mb: int = 50
    allowed_mime_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "text/csv,text/plain,text/markdown"
    )

    log_level: str = "INFO"

    @property
    def allowed_mime_list(self) -> List[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
