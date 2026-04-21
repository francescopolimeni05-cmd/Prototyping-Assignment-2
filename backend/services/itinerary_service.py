"""
Multi-day itinerary generator — structured JSON with morning/afternoon/evening
blocks per day. Separate from the A2 markdown itinerary so the UI can render
both formats.
"""
from __future__ import annotations

import json

from ..schemas import DayBlock, DayPlan, ItineraryGenerateRequest, StructuredItinerary
from .openai_client import chat_json

SYSTEM = """You generate detailed, practical multi-day travel itineraries as strict JSON.
Rules:
- Always produce exactly `days` entries, numbered 1..days.
- `days` MUST be a JSON array where each element is an object with these exact
  keys at the top level: `day_n` (integer), `title` (string), `blocks` (array).
- Do NOT wrap days as `{"day_1": {...}, "day_2": {...}}` — each element must
  have `day_n` as a field, not as a key.
- Each day has a title and three blocks: morning, afternoon, evening.
- Each block has: activity (what to do), location (specific place), travel_minutes (int, from previous block), estimated_cost_eur (float), notes (optional logistics).
- Prefer places that appear in the enriched_context (they have Google ratings/prices).
- Day 1 is arrival, last day is departure — keep activities lighter on those.
- Use the weather summary to avoid outdoor plans on rainy days.
- All string fields (activity, location, notes) must be PLAIN TEXT — no
  markdown links `[x](y)`, no URLs, no hyperlinks of any kind.
- Respond with JSON only, no prose outside the JSON."""

SCHEMA_HINT = """{
  "destination": "string",
  "summary": "1-2 sentence overview",
  "days": [
    {
      "day_n": 1,
      "title": "string",
      "blocks": [
        {"label":"morning","activity":"string","location":"string","travel_minutes":0,"estimated_cost_eur":0,"notes":"string"},
        {"label":"afternoon","activity":"string","location":"string","travel_minutes":20,"estimated_cost_eur":15,"notes":"string"},
        {"label":"evening","activity":"string","location":"string","travel_minutes":10,"estimated_cost_eur":40,"notes":"string"}
      ]
    }
  ]
}"""


def generate_structured(req: ItineraryGenerateRequest) -> StructuredItinerary:
    user_prompt = f"""Plan a {req.days}-day trip to {req.destination} from {req.depart_date} to {req.return_date}.
Travelers: {req.travelers}  |  Style: {req.style}
Interests: {', '.join(req.interests)}  |  Food: {', '.join(req.food_prefs)}
Daily budget: €{req.daily_budget:.0f}

Enriched context (use real places from here when possible):
{req.enriched_context or '(none)'}

Weather: {req.weather_summary or '(unknown)'}

Return JSON matching this schema:
{SCHEMA_HINT}"""

    # Scale max_tokens with trip length so 7+ day itineraries don't get
    # truncated mid-JSON (which would raise a JSONDecodeError upstream).
    # ~450 tokens/day + 1200 headroom for structure/summary, capped at 8k.
    max_tokens = min(8000, 1200 + 450 * max(req.days, 1))

    try:
        data = chat_json(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.6,
        )
    except Exception as exc:
        # Surface OpenAI / JSON errors as a readable message rather than a
        # generic 500.
        raise RuntimeError(f"LLM call failed: {type(exc).__name__}: {exc}") from exc

    # Normalise — LLM sometimes wraps in extra key.
    if "days" not in data and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict) and "days" in inner:
            data = inner

    # Normalise day shapes — LLM sometimes returns one of:
    #   a) list[{"day_n": 1, "title": ..., "blocks": ...}]   (correct)
    #   b) list[{"day_1": {"title": ..., "blocks": ...}}]    (wrapped per-day)
    #   c) {"day_1": {...}, "day_2": {...}}                  (dict-of-days)
    data["days"] = _normalise_days(data.get("days"))

    # Defensive cleanup — fill in missing day titles and clean up block shapes
    # so Pydantic validation doesn't fail on fields the LLM sometimes omits.
    for d in data["days"]:
        d.setdefault("title", f"Day {d.get('day_n', '?')}")
        d["blocks"] = _normalise_blocks(d.get("blocks"))

    # Ensure destination field present for the Pydantic model.
    data.setdefault("destination", req.destination)

    try:
        return StructuredItinerary.model_validate(data)
    except Exception as exc:
        # Include a snippet of the raw data in the error so Railway logs show
        # us what shape the LLM actually returned.
        raw_preview = json.dumps(data, default=str)[:600]
        raise RuntimeError(
            f"Itinerary validation failed: {exc} · raw={raw_preview}"
        ) from exc


def _normalise_days(raw: object) -> list[dict]:
    """Coerce various LLM day-list shapes into the canonical form."""
    if raw is None:
        return []

    # Case c: dict with day_N keys → turn into list preserving order.
    if isinstance(raw, dict):
        items = sorted(raw.items(), key=lambda kv: _day_key_num(kv[0]))
        raw = [{k: v} for k, v in items]

    if not isinstance(raw, list):
        return []

    normalised: list[dict] = []
    for i, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            continue

        # Case a: already has day_n/title/blocks at top level.
        if "blocks" in entry or "title" in entry or "day_n" in entry:
            entry.setdefault("day_n", i)
            normalised.append(entry)
            continue

        # Case b: single key like "day_1" wrapping the real payload.
        if len(entry) == 1:
            key, inner = next(iter(entry.items()))
            if isinstance(inner, dict):
                inner = dict(inner)  # copy to avoid mutating caller data
                inner.setdefault("day_n", _day_key_num(key) or i)
                normalised.append(inner)
                continue

        # Unknown shape — best effort: keep the raw dict, stamp day_n.
        entry.setdefault("day_n", i)
        normalised.append(entry)

    return normalised


def _day_key_num(key: str) -> int:
    """Extract the trailing integer from strings like 'day_3' or 'Day 3'."""
    digits = "".join(ch for ch in str(key) if ch.isdigit())
    return int(digits) if digits else 0


_LABEL_ORDER = ["morning", "afternoon", "evening"]


def _normalise_blocks(raw: object) -> list[dict]:
    """
    Make sure every block has the required fields DayBlock expects:
    `label` and `activity`. Coerce numeric fields that arrived as strings
    (e.g. "€40" → 40.0, "30 min" → 30).
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    for i, b in enumerate(raw):
        if not isinstance(b, dict):
            continue
        block = dict(b)

        # label: fall back to positional morning/afternoon/evening.
        label = (block.get("label") or block.get("slot") or "").strip().lower()
        if label not in _LABEL_ORDER:
            label = _LABEL_ORDER[i] if i < len(_LABEL_ORDER) else f"slot_{i+1}"
        block["label"] = label

        # activity: required — fall back to whatever text we have.
        activity = block.get("activity") or block.get("description") or block.get("title")
        if not activity:
            activity = "Free time"
        block["activity"] = str(activity)

        # coerce numeric-ish fields.
        block["estimated_cost_eur"] = _coerce_float(block.get("estimated_cost_eur"))
        block["travel_minutes"] = _coerce_int(block.get("travel_minutes"))

        out.append(block)
    return out


def _coerce_float(v: object) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        # strip currency symbols / non-numeric chars
        s = "".join(ch for ch in str(v) if ch.isdigit() or ch in ".,-")
        s = s.replace(",", ".")
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


def _coerce_int(v: object) -> int | None:
    f = _coerce_float(v)
    return int(f) if f is not None else None


def regen_day(
    existing: StructuredItinerary,
    day_n: int,
    req: ItineraryGenerateRequest,
) -> StructuredItinerary:
    """Ask the LLM to rewrite a single day while keeping the rest intact."""
    other_days_summary = "\n".join(
        f"Day {d.day_n}: {d.title}" for d in existing.days if d.day_n != day_n
    )
    prompt = f"""Regenerate ONLY day {day_n} of this itinerary for {req.destination}.
Keep continuity with the rest of the plan (do not repeat the same activities as other days).

Other days already planned:
{other_days_summary}

Constraints for day {day_n}:
- Style: {req.style}, interests: {', '.join(req.interests)}, food: {', '.join(req.food_prefs)}
- Daily budget: €{req.daily_budget:.0f}
- Use places from enriched context when possible:
{req.enriched_context or '(none)'}
- Weather: {req.weather_summary or '(unknown)'}

Return JSON: {{"day_n": {day_n}, "title": "...", "blocks": [ ... three blocks morning/afternoon/evening ... ]}}"""

    data = chat_json(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.7,
    )
    new_day = DayPlan.model_validate(data)

    # Replace in place.
    updated_days = [new_day if d.day_n == day_n else d for d in existing.days]
    return StructuredItinerary(
        destination=existing.destination,
        days=updated_days,
        summary=existing.summary,
    )
