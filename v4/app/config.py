
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "NexusAI"
    app_env: str = "development"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    embedding_model: str = "nomic-embed-text"

    max_parallel_tasks: int = 3
    max_task_attempts: int = 2

    max_revision_attempts: int = 2

    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_k: int = 4

    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"
    sales_db_path: Path = PROJECT_ROOT / "data" / "sales.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
