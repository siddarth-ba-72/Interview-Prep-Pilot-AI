from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret: str = ""
    frontend_origin: str = "http://localhost:3000"
    user_service_url: str = "http://localhost:8081"
    topic_service_url: str = "http://localhost:8082"
    upstream_read_timeout_seconds: float = 300
    log_level: str = "INFO"

    @field_validator("user_service_url", "topic_service_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
