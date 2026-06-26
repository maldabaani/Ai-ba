"""Central configuration for StoryForge AI, loaded from environment variables / .env."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _split_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "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")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    CHROMA_PERSIST_PATH: str = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")

    MCP_SERVER_PATH: str = os.getenv("MCP_SERVER_PATH", "")
    ADO_ORGANIZATION: str = os.getenv("ADO_ORGANIZATION", "")
    ADO_PROJECT: str = os.getenv("ADO_PROJECT", "")

    CORS_ORIGINS: list[str] = _split_origins(
        os.getenv("CORS_ORIGINS", "http://localhost:4200")
    )

    JOBS_DIR: str = os.getenv("JOBS_DIR", "./jobs")
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "./uploads")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
