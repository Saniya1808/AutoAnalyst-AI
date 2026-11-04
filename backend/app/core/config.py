from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AutoAnalyst AI"
    APP_DESCRIPTION: str = "Your Autonomous Data Analyst — Powered by Saniya."
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # Allow single origin string or comma-separated list
    FRONTEND_ORIGIN: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("FRONTEND_ORIGIN", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v.strip():
                return ["http://localhost:5173", "http://127.0.0.1:5173"]
            origins = [item.strip() for item in v.split(",") if item.strip()]
            if "http://localhost:5173" not in origins:
                origins.append("http://localhost:5173")
            if "http://127.0.0.1:5173" not in origins:
                origins.append("http://127.0.0.1:5173")
            return origins
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
