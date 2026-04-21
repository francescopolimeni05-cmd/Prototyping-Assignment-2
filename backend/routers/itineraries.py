"""
Itinerary endpoints.

Two generation paths:
* POST /itineraries            → store a markdown (legacy) or structured plan
* POST /itineraries/generate   → produce a structured multi-day plan via LLM
* POST /itineraries/{id}/regen-day  → regenerate a single day of a stored plan

The structured generator lives in `services/itinerary_service.py` so routes
stay thin.
"""
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
    structured = generate_structured(payload)
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

    structured = StructuredItinerary.model_validate(it.structured)
    updated = regen_day(structured, day_n, payload)
    it.structured = updated.model_dump()
    it.source = "regen_day"
    db.commit()
    db.refresh(it)
    return it
