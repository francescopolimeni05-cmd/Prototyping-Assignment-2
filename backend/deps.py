"""FastAPI dependencies: DB session + user resolution from header."""
from __future__ import annotations

import uuid
from typing import Iterator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import config
from .database import SessionLocal
from .models import User


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def get_or_create_user(
    x_user_id: str | None = Header(default=None, alias=config.USER_ID_HEADER),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the user from the `X-VoyageAI-User` header. The Streamlit client
    generates a UUID on first visit and sends it on every request. If the
    header is missing or malformed we reject (frontend should always send one).
    If the UUID isn't in the DB, we create the user on the fly.
    """
    if not x_user_id or not _is_valid_uuid(x_user_id):
        raise HTTPException(status_code=400, detail=f"Missing or invalid {config.USER_ID_HEADER} header")

    user = db.get(User, x_user_id)
    if user is None:
        user = User(id=x_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
