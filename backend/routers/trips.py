"""CRUD for saved trips."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import Trip, User
from ..schemas import TripIn, TripOut

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripOut)
def create_trip(
    payload: TripIn,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Trip:
    trip = Trip(user_id=user.id, **payload.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=list[TripOut])
def list_trips(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> list[Trip]:
    return (
        db.query(Trip)
        .filter(Trip.user_id == user.id)
        .order_by(Trip.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: str,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip
