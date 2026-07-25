from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    internal_api_key: str = ""
    llm_timeout_seconds: float = 60.0


settings = Settings()
