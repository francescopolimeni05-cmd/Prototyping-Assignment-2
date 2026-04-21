"""
Populate the travel knowledge base.

Hybrid strategy (chosen by Francesco, option C):
1. Wikipedia scrape — fetch top ~40 destinations, extract the sections
   Tourism / Culture / Transport / Food / Climate. Split into ~600-char
   chunks with city metadata.
2. Curated tips — generate once with OpenAI per city (scams, etiquette,
   neighbourhoods, budget tips). Cache as JSON on disk so we don't re-spend
   tokens on every ingest.
3. Embed all chunks with OpenAI and upsert into Chroma.

Run with: `python -m backend.rag.ingest` (from the repo root).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import wikipediaapi

from .. import config
from ..services.openai_client import chat_json, embed
from .store import get_collection


# Top destinations — curated to balance Europe / Asia / Americas / etc.
DEFAULT_CITIES = [
    "Paris", "Rome", "Barcelona", "Amsterdam", "London", "Berlin", "Vienna",
    "Prague", "Lisbon", "Madrid", "Istanbul", "Athens", "Dublin", "Copenhagen",
    "Stockholm", "Oslo", "Reykjavik",
    "New York City", "Los Angeles", "San Francisco", "Chicago", "Miami",
    "Mexico City", "Buenos Aires", "Rio de Janeiro",
    "Tokyo", "Kyoto", "Seoul", "Bangkok", "Singapore", "Hong Kong",
    "Bali", "Hanoi", "Kuala Lumpur", "Dubai",
    "Cairo", "Marrakech", "Cape Town",
    "Sydney", "Auckland",
]

SECTIONS_OF_INTEREST = {
    "tourism", "culture", "cuisine", "food", "transport", "transportation",
    "climate", "economy", "history", "neighbourhoods", "neighborhoods",
    "districts", "sights", "attractions", "nightlife",
}

CACHE_DIR = Path(config.DATA_DIR) / "rag_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def _chunk(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    """Split on sentence-ish boundaries into ~`size`-char chunks."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        # Snap to nearest sentence end if possible.
        snap = text.rfind(". ", i, end)
        if snap > i + size // 2:
            end = snap + 1
        chunks.append(text[i:end].strip())
        i = max(end - overlap, end)
    return [c for c in chunks if len(c) > 60]


def _chunk_id(city: str, source: str, text: str) -> str:
    h = hashlib.sha1(f"{city}|{source}|{text[:120]}".encode("utf-8")).hexdigest()[:16]
    return f"{city.lower().replace(' ', '_')}__{source}__{h}"


# ── Wikipedia ──────────────────────────────────────────────────────────────

def _wiki_sections(city: str) -> list[tuple[str, str]]:
    """Return [(section_title, text)] for travel-relevant sections of `city`."""
    wiki = wikipediaapi.Wikipedia(
        user_agent="VoyageAI/1.0 (educational prototype)",
        language="en",
    )
    page = wiki.page(city)
    if not page.exists():
        return []

    out: list[tuple[str, str]] = []

    def walk(sections, depth=0):
        for s in sections:
            title_lower = s.title.lower().strip()
            if any(k in title_lower for k in SECTIONS_OF_INTEREST):
                text = s.text.strip()
                if text and len(text) > 200:
                    out.append((s.title, text))
            if depth < 2:
                walk(s.sections, depth + 1)

    # Lead paragraph is always useful.
    if page.summary:
        out.append(("Overview", page.summary))
    walk(page.sections)
    return out


# ── Curated tips layer ─────────────────────────────────────────────────────

CURATED_SYSTEM = """You are a well-travelled local guide. Produce concise, practical travel tips as strict JSON.
No marketing fluff. Prefer specifics (neighbourhood names, average prices in EUR, common scams)."""

CURATED_SCHEMA = """{
  "neighbourhoods": [{"name":"string","vibe":"string","stay_here_if":"string"}],
  "scams": [{"name":"string","how_it_works":"string","how_to_avoid":"string"}],
  "etiquette": ["short bullet", "..."],
  "budget_tips": ["short bullet", "..."],
  "transport": ["short bullet", "..."],
  "best_time_to_visit": "1-2 sentences"
}"""


def _curated_tips(city: str) -> dict:
    cache = CACHE_DIR / f"{city.lower().replace(' ', '_')}.json"
    if cache.exists():
        return json.loads(cache.read_text())

    data = chat_json(
        [
            {"role": "system", "content": CURATED_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Write travel tips for {city} following this schema:\n{CURATED_SCHEMA}\n"
                    "5 neighbourhoods, 3 scams, 6 etiquette, 6 budget tips, 6 transport tips."
                ),
            },
        ],
        max_tokens=1800,
        temperature=0.4,
    )
    cache.write_text(json.dumps(data, indent=2))
    return data


def _curated_chunks(city: str, tips: dict) -> list[tuple[str, str]]:
    """Flatten the curated JSON into retrievable text chunks."""
    chunks: list[tuple[str, str]] = []

    for n in tips.get("neighbourhoods", []) or []:
        chunks.append(("neighbourhoods", f"{city} — {n.get('name','')}: {n.get('vibe','')} Stay here if {n.get('stay_here_if','')}"))
    for s in tips.get("scams", []) or []:
        chunks.append(("scams", f"{city} scam — {s.get('name','')}: {s.get('how_it_works','')} Avoid: {s.get('how_to_avoid','')}"))
    if tips.get("etiquette"):
        chunks.append(("etiquette", f"{city} etiquette: " + " • ".join(tips["etiquette"])))
    if tips.get("budget_tips"):
        chunks.append(("budget", f"{city} budget tips: " + " • ".join(tips["budget_tips"])))
    if tips.get("transport"):
        chunks.append(("transport", f"{city} transport: " + " • ".join(tips["transport"])))
    if tips.get("best_time_to_visit"):
        chunks.append(("season", f"{city} best time to visit: {tips['best_time_to_visit']}"))
    return chunks


# ── Driver ─────────────────────────────────────────────────────────────────

def ingest(cities: list[str] | None = None, include_wikipedia: bool = True, include_curated: bool = True) -> dict:
    cities = cities or DEFAULT_CITIES
    coll = get_collection()

    total_added = 0
    per_city: dict[str, int] = {}

    for city in cities:
        print(f"→ {city}")
        chunks: list[tuple[str, str, str]] = []  # (source, text, subsection)

        if include_wikipedia:
            for section_title, text in _wiki_sections(city):
                for piece in _chunk(text):
                    chunks.append((f"wikipedia:{section_title}", piece, section_title))

        if include_curated:
            try:
                tips = _curated_tips(city)
            except Exception as e:
                print(f"  curated tips failed for {city}: {e}")
                tips = {}
            for source, piece in _curated_chunks(city, tips):
                chunks.append((f"curated:{source}", piece, source))

        if not chunks:
            continue

        # Embed in batches of 64 to stay well under OpenAI request limits.
        ids, docs, metas = [], [], []
        for source, text, subsection in chunks:
            ids.append(_chunk_id(city, source, text))
            docs.append(text)
            metas.append({
                "city": city,
                "city_lower": city.lower(),
                "source": source,
                "subsection": subsection,
            })

        B = 64
        vecs: list[list[float]] = []
        for i in range(0, len(docs), B):
            try:
                vecs.extend(embed(docs[i : i + B]))
            except Exception as e:
                print(f"  embed failed batch {i}: {e}")
                break
            time.sleep(0.2)

        if len(vecs) != len(docs):
            print(f"  partial embed ({len(vecs)}/{len(docs)}) — skipping {city}")
            continue

        coll.upsert(ids=ids, embeddings=vecs, documents=docs, metadatas=metas)
        per_city[city] = len(docs)
        total_added += len(docs)
        print(f"  +{len(docs)} chunks (total in coll: {coll.count()})")

    return {"total_added": total_added, "per_city": per_city}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", nargs="*", help="Subset of cities to ingest")
    parser.add_argument("--no-wikipedia", action="store_true")
    parser.add_argument("--no-curated", action="store_true")
    args = parser.parse_args()

    result = ingest(
        cities=args.cities,
        include_wikipedia=not args.no_wikipedia,
        include_curated=not args.no_curated,
    )
    print(json.dumps(result, indent=2))
