"""Central configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_setting(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


class Settings:
    LLM_PROVIDER: str = _get_setting("LLM_PROVIDER", "ollama")
    OLLAMA_MODEL: str = _get_setting("OLLAMA_MODEL", "llama3:8b")
    OLLAMA_HOST: str = _get_setting("OLLAMA_HOST", "http://localhost:11434")
    OPENAI_API_KEY: str = _get_setting("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = _get_setting("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY: str = _get_setting("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = _get_setting("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_API_KEY: str = _get_setting("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = _get_setting("GEMINI_MODEL", "gemini-flash-lite-latest")
    GROQ_API_KEY: str = _get_setting("GROQ_API_KEY", "")
    GROQ_MODEL: str = _get_setting("GROQ_MODEL", "llama-3.1-8b-instant")

    EMBEDDING_MODEL: str = _get_setting("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHROMA_PERSIST_DIR: str = _get_setting("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma_db"))
    CHROMA_COLLECTION: str = _get_setting("CHROMA_COLLECTION", "resumes")
    DATABASE_URL: str = _get_setting("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    HR_PASSWORD: str = _get_setting("HR_PASSWORD", "admin123")
    RESUME_DIR: Path = BASE_DIR / "data" / "resumes"


settings = Settings()