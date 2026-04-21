"""
RAG chatbot logic.

Flow:
  trip_context (from client)  ─┐
  retrieved chunks (Chroma)   ─┼─→ system prompt → LLM → answer + sources
  conversation history        ─┘

The knowledge base is populated by `backend/rag/ingest.py` and persisted in
Chroma under `config.CHROMA_DIR`. If the KB is empty (fresh deploy) we still
return an answer — just without retrieval sources, matching the A2 behaviour.
"""
from __future__ import annotations

from typing import Any

from ..schemas import ChatRequest, ChatSource
from .openai_client import chat_completion
from ..rag.retriever import retrieve


SYSTEM_TEMPLATE = """You are VoyageAI, a friendly travel assistant with access to the user's trip data and a curated travel knowledge base.

USER'S TRIP DATA:
{trip_context}

RELEVANT BACKGROUND KNOWLEDGE (retrieved, cite as [1], [2]... when used):
{knowledge}

Rules:
- Always prefer the user's trip data for specifics (their flight, hotel, dates).
- Use the retrieved knowledge for destination info, scams, etiquette, transport tips.
- Cite retrieved sources inline with bracket numbers when they inform the answer.
- Respond in the user's language. Be concise and practical.
"""


def _format_sources(chunks: list[dict]) -> tuple[str, list[ChatSource]]:
    """Turn retrieved chunks into a numbered block + list of ChatSource objects."""
    lines = []
    sources: list[ChatSource] = []
    for i, c in enumerate(chunks, start=1):
        snippet = c["text"][:400].replace("\n", " ")
        lines.append(f"[{i}] ({c['source']}): {snippet}")
        sources.append(ChatSource(source=c["source"], score=c["score"], snippet=snippet))
    return "\n".join(lines) if lines else "(no retrieval hits)", sources


def answer_with_rag(payload: ChatRequest) -> dict[str, Any]:
    # Latest user question drives the retrieval query.
    last_user = next(
        (m.content for m in reversed(payload.messages) if m.role == "user"),
        "",
    )

    chunks: list[dict] = []
    if payload.use_rag and last_user:
        chunks = retrieve(last_user, destination_hint=payload.trip_context or "")

    knowledge_block, sources = _format_sources(chunks)

    system_msg = SYSTEM_TEMPLATE.format(
        trip_context=payload.trip_context or "(no trip data yet)",
        knowledge=knowledge_block,
    )

    messages = [{"role": "system", "content": system_msg}]
    # Trim history to last 12 turns to keep context manageable.
    for m in payload.messages[-12:]:
        messages.append({"role": m.role, "content": m.content})

    content = chat_completion(messages, max_tokens=900, temperature=0.7)
    return {"content": content, "sources": sources}
