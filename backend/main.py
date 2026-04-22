"""
VoyageAI FastAPI backend.

Run locally:  uvicorn backend.main:app --reload --port 8000
Deploy:       see backend/Dockerfile + backend/railway.toml
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import init_db
from .routers import agent, chat, feedback, itineraries, trips, users, votes


def create_app() -> FastAPI:
    app = FastAPI(
        title="VoyageAI API",
        description="Backend for the VoyageAI travel planner prototype (PDAI Assignment 3).",
        version="0.3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[config.USER_ID_HEADER],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        # `build` is a sentinel to verify which commit is actually live on
        # Railway. Bump manually when you push — if /health doesn't show the
        # new value, Railway didn't rebuild.
        return {
            "status": "ok",
            "version": app.version,
            "build": "2026-04-22-agent-fixes",
        }

    @app.get("/rag/status", tags=["meta"])
    def rag_status() -> dict:
        """How many chunks are indexed? Useful to verify the RAG ingest ran."""
        try:
            from .rag.store import get_collection
            coll = get_collection()
            return {"indexed_chunks": coll.count(), "collection": coll.name}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}", "indexed_chunks": 0}

    app.include_router(users.router)
    app.include_router(trips.router)
    app.include_router(chat.router)
    app.include_router(votes.router)
    app.include_router(feedback.router)
    app.include_router(itineraries.router)
    app.include_router(agent.router)

    return app


app = create_app()
