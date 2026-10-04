"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dfsuser:dfspassword@localhost:5432/dfsdb"

    # JWT
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Storage Nodes
    NODE1_URL: str = "http://localhost:8001"
    NODE2_URL: str = "http://localhost:8002"
    NODE3_URL: str = "http://localhost:8003"

    # Limits
    MAX_FILE_SIZE: int = 104_857_600  # 100 MB

    # Health check
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def node_urls(self) -> dict:
        return {
            "node1": self.NODE1_URL,
            "node2": self.NODE2_URL,
            "node3": self.NODE3_URL,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
