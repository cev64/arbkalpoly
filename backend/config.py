from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    allowed_origin: str = "http://localhost:8000"
    minimum_roi: float = 0.01
    minimum_match_confidence: int = 90
    stale_after_seconds: int = 15
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
