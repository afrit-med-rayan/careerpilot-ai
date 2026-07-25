from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot"

    # Auth
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # LLM
    anthropic_api_key: str = ""

    # Job APIs
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Storage
    storage_backend: str = "local"
    local_upload_dir: str = "uploads"

    # Debug
    debug_log_llm: bool = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
