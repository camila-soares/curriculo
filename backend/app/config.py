from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="backend/.env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    business_timezone: str = "America/Recife"
    exam_duration_min: int = 30
    business_hours_start: str = "08:00"
    business_hours_end: str = "18:00"

    google_calendar_id: str = "primary"

    # Service Account mode
    google_service_account_file: str | None = None
    google_workspace_subject_email: str | None = None

    # OAuth mode (token generated offline)
    google_oauth_client_file: str = "backend/credentials.json"
    google_oauth_token_file: str = "backend/token.json"

    sqlite_path: str = "backend/app.db"


settings = Settings()

