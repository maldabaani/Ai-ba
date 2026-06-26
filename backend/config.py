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
    EXPORTS_DIR: str = os.getenv("EXPORTS_DIR", "./exports")

    # "production" (default) uses prompts/system_prompt.py. "selftest" swaps in
    # prompts/system_prompt_selftest.py, used only when assessing SDDs that
    # describe changes to StoryForge AI's own codebase.
    PROMPT_VARIANT: str = os.getenv("PROMPT_VARIANT", "production")

    # "document" (default, for now) writes approved stories to a .docx instead of
    # pushing to ADO. Set to "ado" to re-enable the real Azure DevOps integration
    # for production testing later — create_ado_node itself is unchanged either way.
    OUTPUT_MODE: str = os.getenv("OUTPUT_MODE", "document")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
