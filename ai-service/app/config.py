from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which provider every LLM call goes to. Switched by hand, e.g. to "gemini" when the OpenAI
    # credit is about to run out; takes effect on the next start (or redeploy).
    llm_provider: Literal["openai", "gemini"] = "openai"

    openai_api_key: str = ""
    llm_model: str = "gpt-4o"  # the OpenAI model

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    # Gemini's OpenAI-compatible endpoint, so the same OpenAI SDK calls work for both providers.
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    internal_api_key: str = ""
    llm_timeout_seconds: float = 60.0

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value):
        # An empty LLM_PROVIDER= means the default rather than failing startup.
        return (value.strip().lower() or "openai") if isinstance(value, str) else value


settings = Settings()
