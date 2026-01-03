"""
Database configuration settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Database configuration settings."""

    # PostgreSQL connection settings
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_money_development"

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    # For testing
    testing: bool = False
    test_database_url: str | None = None

    @property
    def database_url(self) -> str:
        """Get the async database URL for SQLAlchemy."""
        if self.testing and self.test_database_url:
            return self.test_database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Get the sync database URL for Alembic migrations."""
        if self.testing and self.test_database_url:
            # Convert async URL to sync
            return self.test_database_url.replace("+psycopg", "")
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
