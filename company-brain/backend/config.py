"""Central config – reads from .env file or environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql://brain:brainpass@localhost:5432/company_brain"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"
    approval_required: bool = True  # Always True – never auto-fire actions

    # Optional integrations (blank = use mock data)
    hubspot_private_token: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
