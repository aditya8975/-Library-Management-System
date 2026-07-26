"""
Centralized application configuration.

All values are read from environment variables (via a local .env file
in development). Nothing here is hardcoded so the same codebase can run
against MySQL in production or SQLite for quick local testing.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///./library.db"

    # Security
    SECRET_KEY: str = "insecure-dev-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Business rules
    ISSUE_PERIOD_DAYS: int = 14
    FINE_PER_DAY: float = 5.0

    # Bootstrap admin (created automatically if no users exist yet)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@library.example"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@123"


settings = Settings()
