from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.local_settings import local_search_settings


class Settings(BaseSettings):
    """Explicit values, environment and .env override saved local search policy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
    ):
        return (
            init_settings, env_settings, dotenv_settings, local_search_settings, file_secret_settings,
        )

    twikit_auth_token: str | None = Field(
        default=None,
        validation_alias="TWIKIT_AUTH_TOKEN",
        repr=False,
    )
    twikit_ct0: str | None = Field(
        default=None,
        validation_alias="TWIKIT_CT0",
        repr=False,
    )
    twikit_cookies_json: str | None = Field(
        default=None,
        validation_alias="TWIKIT_COOKIES_JSON",
        repr=False,
    )
    http_access_token: str | None = Field(
        default=None, validation_alias="X_RESEARCH_ACCESS_TOKEN", repr=False,
    )
    twikit_cookies_file: str | None = Field(
        default=None, validation_alias="TWIKIT_COOKIES_FILE", repr=False,
    )
    job_db_path: str | None = Field(default=None, validation_alias="X_RESEARCH_JOB_DB")
    twikit_language: str = Field(default="en-US", validation_alias="TWIKIT_LANGUAGE")
    twikit_proxy: str | None = Field(default=None, validation_alias="TWIKIT_PROXY")

    allowed_users: str = Field(
        default="",
        validation_alias="ALLOWED_USERS",
    )
    allow_arbitrary_search: bool = Field(
        default=False,
        validation_alias="ALLOW_ARBITRARY_SEARCH",
    )
    max_pages: int = Field(default=100, ge=1, le=500, validation_alias="MAX_PAGES")
    max_results: int = Field(default=2000, ge=1, le=10000, validation_alias="MAX_RESULTS")
    page_size: int = Field(default=20, ge=1, le=100, validation_alias="PAGE_SIZE")
    x_pagination_diagnostics: bool = Field(
        default=False,
        validation_alias="X_PAGINATION_DIAGNOSTICS",
    )

    max_concurrent_requests: int = Field(
        default=1,
        ge=1,
        le=10,
        validation_alias="X_MAX_CONCURRENT_REQUESTS",
    )
    min_request_interval_seconds: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        validation_alias="X_MIN_REQUEST_INTERVAL_SECONDS",
    )
    rate_limit_per_minute: float = Field(
        default=60.0,
        gt=0.0,
        le=600.0,
        validation_alias="X_RATE_LIMIT_PER_MINUTE",
    )
    max_retries: int = Field(default=2, ge=0, le=3, validation_alias="X_MAX_RETRIES")
    retry_base_seconds: float = Field(
        default=1.0,
        gt=0.0,
        le=30.0,
        validation_alias="X_RETRY_BASE_SECONDS",
    )
    retry_max_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=120.0,
        validation_alias="X_RETRY_MAX_SECONDS",
    )

    user_cache_ttl_seconds: float = Field(
        default=300.0,
        ge=0.0,
        le=86400.0,
        validation_alias="X_USER_CACHE_TTL_SECONDS",
    )
    tweet_cache_ttl_seconds: float = Field(
        default=120.0,
        ge=0.0,
        le=86400.0,
        validation_alias="X_TWEET_CACHE_TTL_SECONDS",
    )
    search_cache_ttl_seconds: float = Field(
        default=30.0,
        ge=0.0,
        le=86400.0,
        validation_alias="X_SEARCH_CACHE_TTL_SECONDS",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
