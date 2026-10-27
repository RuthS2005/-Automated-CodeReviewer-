"""Environment-backed runtime configuration."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables (never checked-in secrets)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: SecretStr = Field(validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="gemini-2.5-flash", validation_alias="GEMINI_MODEL"
    )
    agent_workspace: Path = Field(
        default_factory=Path.cwd, validation_alias="AGENT_WORKSPACE"
    )
    max_agent_iterations: int = Field(
        default=8, ge=1, le=30, validation_alias="MAX_AGENT_ITERATIONS"
    )
