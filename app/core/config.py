# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Literal
import os, logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    groq_api_key: str
    database_url: str
    upstash_redis_url: str
    upstash_redis_token: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str = "app_builder_patterns"
    github_token: str
    github_default_org: str = ""
    e2b_api_key: str
    tavily_api_key: str
    langchain_api_key: str
    langchain_project: str = "app-builder-agent"
    langchain_tracing_v2: bool = True
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    guardrails_api_key: str = ""
    app_env: Literal["development", "staging", "production"] = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v):
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg:// driver")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt(cls, v):
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be >= 32 chars")
        return v

    @model_validator(mode="after")
    def set_langsmith_env(self):
        os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = self.langchain_project
        os.environ["LANGCHAIN_TRACING_V2"] = str(self.langchain_tracing_v2).lower()
        return self


settings = Settings()
