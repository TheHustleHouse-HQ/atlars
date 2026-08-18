from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MongoDB
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "atlars"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # OpenRouter
    openrouter_api_key: str = ""

    # Embeddings
    embedding_model: str = "nvidia/nemotron-3-embed-1b:free"
    embedding_dimensions: int = 2048

    # App
    env: str = "development"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:8081"

    # Voice Uploads
    upload_dir: str = "uploads/"
    max_audio_size_bytes: int = 25 * 1024 * 1024
    allowed_audio_extensions: str = ".mp3,.wav,.m4a,.webm"

    # Transcription
    transcription_provider: str = "mock"
    whisper_model: str = "base"
    whisper_language: str = "en"
    whisper_device: str = "auto"

    @property
    def allowed_audio_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.allowed_audio_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
