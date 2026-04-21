"""Chroma persistent collection handle, shared across ingest + retrieval."""
from __future__ import annotations

import chromadb
from chromadb.config import Settings

from .. import config

_collection = None


def get_collection():
    """Return (creating if missing) the 'travel_kb' collection."""
    global _collection
    if _collection is not None:
        return _collection

    client = chromadb.PersistentClient(
        path=config.CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = client.get_or_create_collection(
        name="travel_kb",
        metadata={"hnsw:space": "cosine"},
    )
    return _collection
