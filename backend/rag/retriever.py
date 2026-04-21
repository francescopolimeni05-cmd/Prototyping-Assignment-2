"""
Retrieval interface consumed by the chat service.

Embeds the query, pulls top-k from Chroma, returns a list of dicts
{source, score, text}. If the collection is empty or embeddings fail we
return [] — callers treat that as "no retrieval, answer anyway".
"""
from __future__ import annotations

from typing import Any

from .. import config
from ..services.openai_client import embed
from .store import get_collection


def retrieve(query: str, destination_hint: str = "", k: int | None = None) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    k = k or config.RAG_TOP_K

    try:
        vec = embed([query])[0]
    except Exception:
        return []

    coll = get_collection()
    if coll.count() == 0:
        return []

    # Simple metadata boost: if a destination hint is present, pre-filter
    # to chunks whose `city` metadata contains the hint (case-insensitive).
    where: dict | None = None
    hint = destination_hint.split(",")[0].strip().lower() if destination_hint else ""
    if hint:
        # Chroma's `where` supports exact match; we index `city_lower`.
        where = {"city_lower": {"$eq": hint}}

    try:
        res = coll.query(
            query_embeddings=[vec],
            n_results=k,
            where=where,
        )
    except Exception:
        # Fall back to unfiltered query if the hint doesn't match anything.
        res = coll.query(query_embeddings=[vec], n_results=k)

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    chunks = []
    for text, meta, dist in zip(docs, metas, dists):
        chunks.append({
            "text": text,
            "source": meta.get("source", "unknown"),
            "score": float(1.0 - dist) if dist is not None else 0.0,
        })
    return chunks
