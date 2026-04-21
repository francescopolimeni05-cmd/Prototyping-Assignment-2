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
- Each day has a title and three blocks: morning, afternoon, evening.
- Each block has: activity (what to do), location (specific place), travel_minutes (int, from previous block), estimated_cost_eur (float), notes (optional logistics).
- Prefer places that appear in the enriched_context (they have Google ratings/prices).
- Day 1 is arrival, last day is departure — keep activities lighter on those.
- Use the weather summary to avoid outdoor plans on rainy days.
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

    data = chat_json(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=3500,
        temperature=0.6,
    )

    # Normalise — LLM sometimes wraps in extra key.
    if "days" not in data and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict) and "days" in inner:
            data = inner

    # Ensure destination field present for the Pydantic model.
    data.setdefault("destination", req.destination)
    return StructuredItinerary.model_validate(data)


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
