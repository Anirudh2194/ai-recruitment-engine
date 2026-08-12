"""Local, free text embeddings via Sentence-Transformers.

This is deliberately decoupled from any LLM provider: embeddings run
locally regardless of whether the LLM_PROVIDER is Ollama, OpenAI, or
Anthropic, so semantic matching never depends on API availability.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    """Load the model once per process."""
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    model = get_embedder()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()
