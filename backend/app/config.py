from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration; secrets belong in environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MyMusic AI API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./mymusic_dev.db"
    audio_storage_dir: str = "./audio_storage"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    music_model_backend: str = "unconfigured"
    ace_step_base_url: str = "http://127.0.0.1:8001"
    ace_step_api_key: str = ""
    ace_step_timeout_seconds: int = 900
    ace_step_poll_seconds: float = 2.0
    default_generation_duration_seconds: int = 30

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
