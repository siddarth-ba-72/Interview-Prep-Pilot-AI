from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://root:change_me@localhost:27017/?authSource=admin"
    mongodb_db: str = "topics_db"
    ai_service_url: str = "http://localhost:8000"
    internal_api_key: str = ""
    log_level: str = "INFO"


settings = Settings()
