from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://weather:weather@localhost:5432/weather"
    cache_max_age_seconds: int = 300  # freshness window for cached readings

    http_connect_timeout: float = 3.0
    http_read_timeout: float = 10.0
    http_max_attempts: int = 3
    http_backoff_base: float = 0.5

    cors_origins: str = "http://localhost:3000"

    @property
    def cache_max_age(self) -> timedelta:
        return timedelta(seconds=self.cache_max_age_seconds)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
