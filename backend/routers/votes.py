"""
Voting endpoints — power the prof-requested "do users prefer AI-optimized
vs manual planning?" question and the per-feature thumbs up/down.
"""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import User, Vote
from ..schemas import VoteIn, VoteOut, VoteStats

router = APIRouter(prefix="/votes", tags=["votes"])


@router.post("", response_model=VoteOut)
def cast_vote(
    payload: VoteIn,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> Vote:
    vote = Vote(user_id=user.id, **payload.model_dump())
    db.add(vote)
    db.commit()
    db.refresh(vote)
    return vote


@router.get("/stats", response_model=VoteStats)
def vote_stats(
    target_type: str = Query(...),
    target_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> VoteStats:
    q = db.query(Vote).filter(Vote.target_type == target_type)
    if target_id:
        q = q.filter(Vote.target_id == target_id)
    rows = q.all()
    counts = Counter(r.choice for r in rows)
    return VoteStats(target_type=target_type, total=len(rows), counts=dict(counts))
