"""Central config – reads from .env file or environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings

# .env may live in backend/ OR one level up (company-brain/)
_HERE = Path(__file__).parent
_ENV_PATHS = [_HERE / ".env", _HERE.parent / ".env"]


class Settings(BaseSettings):
    # Core
    anthropic_api_key: str = ""
    database_url: str = "postgresql://brain:brainpass@localhost:5432/company_brain"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"
    approval_required: bool = True

    # OpenAI (embeddings / fallback LLM)
    openai_api_key: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_cloud_api_key: str = ""
    google_maps_api_key: str = ""

    # Stripe
    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""

    # X / Twitter
    x_api_key: str = ""
    x_api_key_secret: str = ""
    x_bearer_token: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    x_oauth2_client_id: str = ""
    x_client_secret: str = ""

    # SEMrush
    semrush_api_key: str = ""

    # Massive.com
    massive_access_key_id: str = ""
    massive_secret_access_key: str = ""

    # Microsoft Clarity
    clarity_token: str = ""

    # Optional CRM
    hubspot_private_token: str = ""

    model_config = {
        "env_file": [str(p) for p in _ENV_PATHS if p.exists()],
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
