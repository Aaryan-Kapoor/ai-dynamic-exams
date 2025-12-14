from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI-Powered Adaptive Examination System"
    environment: str = "dev"
    secret_key: str = "change-me"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite:///./data/app.db"

    upload_dir: Path = Path("./data/uploads")

    chunk_size_chars: int = Field(default=1200, ge=200)
    chunk_overlap_chars: int = Field(default=200, ge=0)
    max_context_chars: int = Field(default=6000, ge=1000)
    context_chunks: int = Field(default=5, ge=1, le=20)

    llm_provider: str = "openai_compat"  # openai_compat | mock
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.1"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=700, ge=64, le=4096)
    llm_timeout_seconds: int = Field(default=60, ge=5, le=600)
    llm_fallback_to_mock: bool = True

    embedding_provider: str = "sentence_transformers"  # sentence_transformers | hash
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str | None = None  # e.g. "cpu", "cuda"
    embedding_dim: int = Field(default=384, ge=64, le=4096)

    exam_default_max_duration_minutes: int = Field(default=30, ge=1, le=600)
    exam_default_max_attempts: int = Field(default=3, ge=1, le=10)
    exam_default_max_questions: int = Field(default=10, ge=1, le=200)
    exam_default_stop_consecutive_incorrect: int = Field(default=3, ge=1, le=50)
    exam_default_stop_slow_seconds: int = Field(default=300, ge=10, le=7200)
    exam_default_difficulty_min: int = Field(default=2, ge=1, le=5)
    exam_default_difficulty_max: int = Field(default=4, ge=1, le=5)

    score_weight_correctness: float = Field(default=0.6, ge=0.0, le=1.0)
    score_weight_speed: float = Field(default=0.2, ge=0.0, le=1.0)
    score_weight_consistency: float = Field(default=0.2, ge=0.0, le=1.0)

    max_upload_mb: int = Field(default=25, ge=1, le=200)

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
