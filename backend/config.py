"""AUSHADHI — application settings.

All values come from environment variables (see .env.example at repo root).
Nothing here reads secrets from disk except via the .env files listed below.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- GCP ----
    google_cloud_project: str = "aushadhi-hackathon"
    google_cloud_region: str = "us-central1"
    google_application_credentials: Optional[str] = None

    # ---- Gemini ----
    google_api_key: str = ""  # AI Studio only; unused in Vertex AI mode
    # Vertex AI endpoint for the model. gemini-3.5-flash is served from the
    # "global" endpoint only — regional endpoints such as us-central1 return
    # 404 NOT_FOUND for it. Kept separate from google_cloud_region, which is
    # where Cloud Run/Firestore live.
    vertex_location: str = "global"
    gemini_model: str = "gemini-3.5-flash"
    gemini_thinking_level: Literal["minimal", "low", "medium", "high"] = "low"
    gemini_max_tokens: int = 8192
    # Free-tier gemini-3.5-flash allows 5 requests/minute; raise this once
    # the project has billing enabled.
    gemini_max_requests_per_minute: int = 5

    # ---- Auth ----
    aushadhi_api_key: str = ""

    # ---- Firestore ----
    firestore_database_id: str = "(default)"

    # ---- Pub/Sub ----
    pubsub_topic_prefix: str = "aushadhi"

    # ---- Agent settings ----
    sentinel_poll_interval_minutes: int = 30
    critical_threshold_percentage: int = 15
    low_threshold_percentage: int = 30
    outbreak_detection_window_days: int = 7
    use_gemma_fallback: bool = False
    gemma_model: str = "gemma-2-9b-it"

    # ---- App settings ----
    app_name: str = "AUSHADHI"
    app_version: str = "1.0.0"
    run_mode: Literal["api", "agents"] = "api"
    # The API process also runs the four Pub/Sub subscriber loops, so a single
    # `uvicorn main:app` starts the whole system. Set false only when running
    # multiple API replicas, where every replica would otherwise consume the
    # same subscriptions and duplicate the Gemini calls.
    agents_in_process: bool = True
    log_level: str = "INFO"
    environment: Literal["development", "staging", "production"] = "development"
    # Browsers send the exact page origin, so every host the dashboard is
    # served from has to be listed verbatim. Cloud Run answers on both URL
    # forms for the same service (the project-number one and the legacy
    # -mnpwpjt7xq-uc hash), and either can end up in the address bar — list
    # both or a preflight from the other one comes back "Disallowed CORS
    # origin". CORS_ORIGINS (comma-separated) overrides this default.
    cors_origins: List[str] = [
        "https://aushadhi-frontend-230802283586.us-central1.run.app",
        "https://aushadhi-frontend-mnpwpjt7xq-uc.a.run.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",  # Lovable dev server default
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    # ---- Derived helpers ----
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def topic(self, name: str) -> str:
        """Fully qualified Pub/Sub topic name, e.g. topic("sentinel-alerts")."""
        return f"{self.pubsub_topic_prefix}-{name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
