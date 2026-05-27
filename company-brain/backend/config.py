"""Central config – reads from .env file or environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings

# .env may live in backend/ OR one level up (company-brain/)
_HERE = Path(__file__).parent
_ENV_PATHS = [_HERE / ".env", _HERE.parent / ".env"]


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

    model_config = {
        "env_file": [str(p) for p in _ENV_PATHS if p.exists()],
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
