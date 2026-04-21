"""Pydantic request/response schemas. Kept flat so Streamlit-side can build dicts."""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Users ──────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ── Trips ──────────────────────────────────────────────────────────────────
class TripIn(BaseModel):
    origin_city: Optional[str] = None
    destination_city: str
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    travelers: Optional[int] = None
    budget_eur: Optional[int] = None
    style: Optional[str] = None
    interests: Optional[list[str]] = None
    food_prefs: Optional[list[str]] = None
    params_snapshot: Optional[dict[str, Any]] = None


class TripOut(TripIn):
    id: str
    user_id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ── Chat ───────────────────────────────────────────────────────────────────
class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    trip_id: Optional[str] = None
    messages: list[ChatTurn]
    trip_context: Optional[str] = None
    # When True, run retrieval augmentation; when False, behave like the A2 chatbot.
    use_rag: bool = True


class ChatSource(BaseModel):
    source: str
    score: float
    snippet: str


class ChatResponse(BaseModel):
    content: str
    sources: list[ChatSource] = Field(default_factory=list)
    message_id: str


# ── Votes ──────────────────────────────────────────────────────────────────
class VoteIn(BaseModel):
    trip_id: Optional[str] = None
    target_type: str
    target_id: Optional[str] = None
    choice: str


class VoteOut(VoteIn):
    id: str
    user_id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


class VoteStats(BaseModel):
    """Aggregate voting results for a given target_type (across all users)."""
    target_type: str
    total: int
    counts: dict[str, int]  # {choice: count}


# ── Feedback ───────────────────────────────────────────────────────────────
class FeedbackIn(BaseModel):
    trip_id: Optional[str] = None
    target_type: str
    target_id: Optional[str] = None
    helpful: Optional[int] = None  # 1, 0, None
    note: Optional[str] = None


class FeedbackOut(FeedbackIn):
    id: str
    user_id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ── Itineraries ────────────────────────────────────────────────────────────
class ItineraryIn(BaseModel):
    trip_id: Optional[str] = None
    destination: str
    days: Optional[int] = None
    markdown: Optional[str] = None
    structured: Optional[dict[str, Any]] = None
    source: Optional[str] = None


class ItineraryOut(ItineraryIn):
    id: str
    user_id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


class ItineraryGenerateRequest(BaseModel):
    """Request a new multi-day structured itinerary from the LLM."""
    trip_id: Optional[str] = None
    destination: str
    depart_date: str
    return_date: str
    days: int
    travelers: int
    style: str
    interests: list[str]
    food_prefs: list[str]
    daily_budget: float
    enriched_context: Optional[str] = None
    weather_summary: Optional[str] = None


class DayBlock(BaseModel):
    label: str  # "morning" | "afternoon" | "evening"
    activity: str
    location: Optional[str] = None
    travel_minutes: Optional[int] = None
    estimated_cost_eur: Optional[float] = None
    notes: Optional[str] = None


class DayPlan(BaseModel):
    day_n: int
    title: str
    blocks: list[DayBlock]


class StructuredItinerary(BaseModel):
    destination: str
    days: list[DayPlan]
    summary: Optional[str] = None


# ── Agentic planner ────────────────────────────────────────────────────────
class AgentPlanRequest(BaseModel):
    goal: str  # freeform "I want 4 days in Tokyo, €2000, love arts and street food"
    trip_id: Optional[str] = None


class AgentStep(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    output_summary: Optional[str] = None


class AgentPlanResponse(BaseModel):
    steps: list[AgentStep]
    final_plan: Optional[StructuredItinerary] = None
    final_message: str
