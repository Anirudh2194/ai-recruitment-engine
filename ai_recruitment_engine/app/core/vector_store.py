"""ChromaDB wrapper for storing and querying resume/job embeddings."""
from functools import lru_cache

import chromadb

from app.config import settings


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def upsert(doc_id: str, embedding: list[float], text: str, metadata: dict):
    collection = get_collection()
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )


def query(embedding: list[float], n_results: int = 5, where: dict | None = None):
    collection = get_collection()
    return collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=where,
    )
