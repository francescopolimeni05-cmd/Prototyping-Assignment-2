"""
Feedback endpoints — "Did this suggestion help your trip?" + optional note.
Kept separate from Vote so we can evolve each model independently (votes are
multi-choice; feedback has helpful/notes semantics).
"""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import Feedback, User
from ..schemas import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    payload: FeedbackIn,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Feedback:
    fb = Feedback(user_id=user.id, **payload.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/summary")
def feedback_summary(
    target_type: str = Query(...),
    target_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Lightweight aggregate — helpful/not-helpful counts + latest notes."""
    q = db.query(Feedback).filter(Feedback.target_type == target_type)
    if target_id:
        q = q.filter(Feedback.target_id == target_id)
    rows = q.order_by(Feedback.created_at.desc()).all()
    counts = Counter(r.helpful for r in rows if r.helpful is not None)
    latest_notes = [r.note for r in rows[:10] if r.note]
    return {
        "target_type": target_type,
        "total": len(rows),
        "helpful": counts.get(1, 0),
        "not_helpful": counts.get(0, 0),
        "latest_notes": latest_notes,
    }
