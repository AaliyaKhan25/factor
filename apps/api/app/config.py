"""Settings loaded from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./factor.db")
    # Always set JWT_SECRET in any real deployment. The default is for local development only.
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-secret-change-me-before-deploying-0123456789")
    jwt_minutes: int = int(os.environ.get("JWT_MINUTES", "720"))


settings = Settings()
