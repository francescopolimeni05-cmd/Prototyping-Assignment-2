"""
Chat endpoint — RAG-augmented chatbot.

Flow:
1. Take incoming user messages + optional trip_context (pre-built string of
   flights/hotels/etc. from the Streamlit client).
2. Retrieve top-k relevant chunks from the travel knowledge base in Chroma.
3. Compose a system prompt that fuses trip_context + retrieved snippets.
4. Call the LLM, store user+assistant messages in DB, return with sources.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_or_create_user
from ..models import Message, User
from ..schemas import ChatRequest, ChatResponse, ChatSource
from ..services.chat_service import answer_with_rag

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    result = answer_with_rag(payload)

    # Persist user + assistant turn.
    last_user = next(
        (m for m in reversed(payload.messages) if m.role == "user"),
        None,
    )
    if last_user:
        db.add(Message(
            user_id=user.id,
            trip_id=payload.trip_id,
            role="user",
            content=last_user.content,
        ))

    assistant_msg = Message(
        user_id=user.id,
        trip_id=payload.trip_id,
        role="assistant",
        content=result["content"],
        sources=[s.model_dump() for s in result["sources"]],
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        content=result["content"],
        sources=result["sources"],
        message_id=assistant_msg.id,
    )


@router.get("/history", response_model=list[dict])
def chat_history(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
    trip_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    q = db.query(Message).filter(Message.user_id == user.id)
    if trip_id:
        q = q.filter(Message.trip_id == trip_id)
    rows = q.order_by(Message.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "sources": r.sources,
            "created_at": r.created_at.isoformat(),
        }
        for r in reversed(rows)
    ]
