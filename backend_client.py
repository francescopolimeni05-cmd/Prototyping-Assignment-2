"""
Thin HTTP client the Streamlit frontend uses to talk to the FastAPI backend.

Design goals:
- Zero hard dependency: if BACKEND_URL is not configured OR the backend is
  unreachable, every helper returns a sensible fallback instead of raising.
  This keeps the A2 behaviour working as a fallback even if Railway is down.
- Single source for the user_id header so every call is attributed to the
  right user.
- Cached in st.session_state where it makes sense (vote stats, feedback
  summary) to avoid hammering the backend on every rerun.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

import requests
import streamlit as st

USER_ID_HEADER = "X-VoyageAI-User"
_DEFAULT_TIMEOUT = 40


# ── Configuration ──────────────────────────────────────────────────────────

def backend_url() -> str:
    """Return the configured backend URL or empty string if not set."""
    try:
        url = st.secrets.get("BACKEND_URL", "")
    except Exception:
        url = ""
    return url or os.environ.get("BACKEND_URL", "")


def is_configured() -> bool:
    return bool(backend_url())


# ── User identity (persisted via query params + session state) ─────────────

_QP_KEY = "uid"


def ensure_user_id() -> str:
    """
    Make sure st.session_state['user_id'] is set. Persist across refreshes
    by echoing it into the URL query string (?uid=...). If the URL already
    has a uid, we adopt it. Otherwise generate a UUID and push it there.
    """
    if "user_id" in st.session_state:
        return st.session_state["user_id"]

    qp_uid = _read_query_uid()
    if qp_uid and _is_uuid(qp_uid):
        st.session_state["user_id"] = qp_uid
        return qp_uid

    new_uid = str(uuid.uuid4())
    st.session_state["user_id"] = new_uid
    _write_query_uid(new_uid)
    return new_uid


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _read_query_uid() -> str:
    # Streamlit >=1.30 exposes st.query_params (MutableMapping).
    try:
        qp = st.query_params
        val = qp.get(_QP_KEY, "")
        if isinstance(val, list):
            val = val[0] if val else ""
        return val
    except Exception:
        try:
            qp = st.experimental_get_query_params()
            return qp.get(_QP_KEY, [""])[0]
        except Exception:
            return ""


def _write_query_uid(uid: str) -> None:
    try:
        st.query_params[_QP_KEY] = uid
    except Exception:
        try:
            st.experimental_set_query_params(**{_QP_KEY: uid})
        except Exception:
            pass  # not critical — session_state still holds it for this run


def _headers() -> dict[str, str]:
    return {USER_ID_HEADER: ensure_user_id(), "Content-Type": "application/json"}


# ── Low-level request helpers with graceful fallbacks ──────────────────────

def _request(method: str, path: str, **kwargs: Any) -> dict | list | None:
    if not is_configured():
        return None
    url = backend_url().rstrip("/") + path
    try:
        r = requests.request(
            method,
            url,
            headers={**_headers(), **kwargs.pop("headers", {})},
            timeout=kwargs.pop("timeout", _DEFAULT_TIMEOUT),
            **kwargs,
        )
        if r.status_code >= 400:
            return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}
        return r.json()
    except requests.RequestException as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def get(path: str, **kwargs: Any) -> dict | list | None:
    return _request("GET", path, **kwargs)


def post(path: str, payload: dict | None = None, **kwargs: Any) -> dict | list | None:
    return _request("POST", path, json=payload or {}, **kwargs)


# ── Domain helpers ─────────────────────────────────────────────────────────

def create_trip(payload: dict) -> dict | None:
    return post("/trips", payload)


def cast_vote(target_type: str, choice: str, trip_id: str | None = None, target_id: str | None = None) -> dict | None:
    return post("/votes", {
        "target_type": target_type,
        "choice": choice,
        "trip_id": trip_id,
        "target_id": target_id,
    })


def vote_stats(target_type: str, target_id: str | None = None) -> dict | None:
    params = {"target_type": target_type}
    if target_id:
        params["target_id"] = target_id
    return get("/votes/stats", params=params)


def submit_feedback(target_type: str, helpful: int | None, note: str | None = None,
                    trip_id: str | None = None, target_id: str | None = None) -> dict | None:
    return post("/feedback", {
        "target_type": target_type,
        "helpful": helpful,
        "note": note,
        "trip_id": trip_id,
        "target_id": target_id,
    })


def feedback_summary(target_type: str, target_id: str | None = None) -> dict | None:
    params = {"target_type": target_type}
    if target_id:
        params["target_id"] = target_id
    return get("/feedback/summary", params=params)


def chat_rag(messages: list[dict], trip_context: str, trip_id: str | None = None, use_rag: bool = True) -> dict | None:
    return post("/chat", {
        "messages": messages,
        "trip_context": trip_context,
        "trip_id": trip_id,
        "use_rag": use_rag,
    })


def generate_structured_itinerary(payload: dict) -> dict | None:
    return post("/itineraries/generate", payload)


def regen_day(itinerary_id: str, day_n: int, payload: dict) -> dict | None:
    return post(f"/itineraries/{itinerary_id}/regen-day/{day_n}", payload)


def run_agent(goal: str, trip_id: str | None = None) -> dict | None:
    # Agent may take ~30s (multiple tool calls + itinerary generation).
    return post("/agent/plan", {"goal": goal, "trip_id": trip_id}, timeout=120)
