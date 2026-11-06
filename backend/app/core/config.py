from functools import lru_cache
from uuid import UUID

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    dev_auth_enabled: bool = False
    dev_user_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    session_cookie_name: str = "campus_session"
    session_max_age: int = Field(default=604800, ge=60, le=2592000)
    database_url: str = "sqlite:///./backend/data/campus.db"
    local_web_preview_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    @model_validator(mode="after")
    def validate_dev_auth(self):
        if self.dev_auth_enabled and self.app_env != "development":
            raise ValueError("DEV_AUTH_ENABLED requires APP_ENV=development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
