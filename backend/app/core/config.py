from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "AutoAnalyst AI"
    APP_DESCRIPTION: str = "Your Autonomous Data Analyst — Powered by Saniya."
    APP_VERSION: str = "0.2.1"
    ENVIRONMENT: str = "development"

    # Allow single origin string or comma-separated list
    FRONTEND_ORIGIN: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://auto-analyst-ai.vercel.app",
        "https://autoanalyst-ai.vercel.app",
    ]
    # Restricted Vercel preview regex (restricted to AutoAnalyst AI preview deployments)
    FRONTEND_ORIGIN_REGEX: Optional[str] = (
        r"^https://(autoanalyst-ai|auto-analyst-ai)(-[a-zA-Z0-9_-]+)?\.vercel\.app$"
    )

    # Dataset upload & profiling configuration
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_DATASET_ROWS: int = 100_000
    MAX_DATASET_COLUMNS: int = 200
    PREVIEW_ROW_LIMIT: int = 50
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]

    # AI / LLM Configuration (Phase 4.1)
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-3.8-flash"
    AI_TIMEOUT_SECONDS: int = 30
    AI_CACHE_ENABLED: bool = True
    PROMPT_SCHEMA_VERSION: str = "v1"

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    @field_validator("UPLOAD_DIR", mode="after")
    @classmethod
    def resolve_upload_dir(cls, v: str) -> str:
        path = Path(v)
        if not path.is_absolute():
            return str(BASE_DIR / path)
        return str(path)

    @field_validator("FRONTEND_ORIGIN", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        default_local = ["http://localhost:5173", "http://127.0.0.1:5173"]
        if isinstance(v, str):
            if not v.strip():
                return default_local
            origins = [item.strip().rstrip("/") for item in v.split(",") if item.strip()]
            for loc in default_local:
                if loc not in origins:
                    origins.append(loc)
            return origins
        elif isinstance(v, list):
            clean = [str(item).strip().rstrip("/") for item in v if str(item).strip()]
            for loc in default_local:
                if loc not in clean:
                    clean.append(loc)
            return clean
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
