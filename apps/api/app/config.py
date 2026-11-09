"""Settings loaded from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./factor.db")
    # Always set JWT_SECRET in any real deployment. The default is for local development only.
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-secret-change-me-before-deploying-0123456789")
    jwt_minutes: int = int(os.environ.get("JWT_MINUTES", "720"))
    google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    # Service-account JSON is mounted only in the API environment, never sent to a browser.
    google_service_account_json: str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    # Set to verify X-Hub-Signature-256 on Meta webhooks. Leave empty only in local development.
    meta_app_secret: str = os.environ.get("META_APP_SECRET", "")
    # Comma-separated browser origins allowed to call the API.
    cors_origins: str = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    # Gnani.ai Voice & Indic Speech Integrator
    gnani_api_key: str = os.environ.get("GNANI_API_KEY", "")
    gnani_token: str = os.environ.get("GNANI_TOKEN", os.environ.get("GNANI_API_KEY", ""))
    gnani_access_key: str = os.environ.get("GNANI_ACCESS_KEY", "")
    gnani_lang_code: str = os.environ.get("GNANI_LANG_CODE", "en-IN")
    gnani_asr_url: str = os.environ.get("GNANI_ASR_URL", "https://asr.gnani.ai/v1/recognize")
    gnani_stt_url: str = os.environ.get("GNANI_STT_URL", "https://api.vachana.ai/stt/v3")
    gnani_tts_url: str = os.environ.get("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")
    courier_encryption_key: str = os.environ.get("COURIER_ENCRYPTION_KEY", "")


settings = Settings()
