from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://root:change_me@localhost:27017/?authSource=admin"
    mongodb_db: str = "users_db"
    jwt_secret: str = ""
    access_token_expiry_seconds: int = 1800
    refresh_token_expiry_days: int = 30
    google_client_id: str = ""
    google_client_secret: str = ""
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = True
    log_level: str = "INFO"


settings = Settings()
