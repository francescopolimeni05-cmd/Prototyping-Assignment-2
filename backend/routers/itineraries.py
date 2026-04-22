"""
Itinerary endpoints.

Two generation paths:
* POST /itineraries            → store a markdown (legacy) or structured plan
* POST /itineraries/generate   → produce a structured multi-day plan via LLM
* POST /itineraries/{id}/regen-day  → regenerate a single day of a stored plan

The structured generator lives in `services/itinerary_service.py` so routes
stay thin.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import Itinerary, User
from ..schemas import (
    ItineraryGenerateRequest,
    ItineraryIn,
    ItineraryOut,
    StructuredItinerary,
)
from ..services.itinerary_service import generate_structured, regen_day

log = logging.getLogger("voyageai.itineraries")

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("", response_model=ItineraryOut)
def save_itinerary(
    payload: ItineraryIn,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Itinerary:
    it = Itinerary(user_id=user.id, **payload.model_dump())
    db.add(it)
    db.commit()
    db.refresh(it)
    return it


@router.get("", response_model=list[ItineraryOut])
def list_itineraries(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> list[Itinerary]:
    return (
        db.query(Itinerary)
        .filter(Itinerary.user_id == user.id)
        .order_by(Itinerary.created_at.desc())
        .limit(50)
        .all()
    )


@router.post("/generate", response_model=ItineraryOut)
def generate_itinerary(
    payload: ItineraryGenerateRequest,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Itinerary:
    try:
        structured = generate_structured(payload)
    except Exception as exc:
        # Log the full traceback to Railway logs so we can debug, but
        # surface a human-readable 422 to the frontend instead of a bare 500.
        log.exception("structured itinerary generation failed: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"Could not generate structured itinerary: {exc}",
        )

    try:
        it = Itinerary(
            user_id=user.id,
            trip_id=payload.trip_id,
            destination=payload.destination,
            days=payload.days,
            structured=structured.model_dump(),
            source="classic",
        )
        db.add(it)
        db.commit()
        db.refresh(it)
        return it
    except Exception as exc:
        log.exception("persisting itinerary failed: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not save itinerary: {exc}",
        )


@router.post("/{itinerary_id}/regen-day/{day_n}", response_model=ItineraryOut)
def regen_day_endpoint(
    itinerary_id: str,
    day_n: int,
    payload: ItineraryGenerateRequest,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Itinerary:
    it = db.get(Itinerary, itinerary_id)
    if not it or it.user_id != user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if not it.structured:
        raise HTTPException(status_code=400, detail="Itinerary has no structured plan to regenerate")

    try:
        structured = StructuredItinerary.model_validate(it.structured)
    except Exception as exc:
        log.exception("stored structured itinerary is corrupt: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Stored itinerary is invalid: {exc}",
        )

    try:
        updated = regen_day(structured, day_n, payload)
    except Exception as exc:
        log.exception("regen_day failed: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"Could not regenerate day {day_n}: {exc}",
        )

    try:
        it.structured = updated.model_dump()
        it.source = "regen_day"
        db.commit()
        db.refresh(it)
        return it
    except Exception as exc:
        log.exception("persisting regen_day result failed: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not save regenerated day: {exc}",
        )
