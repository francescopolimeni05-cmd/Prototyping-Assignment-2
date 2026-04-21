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
        return {"status": "ok", "version": app.version}

    app.include_router(users.router)
    app.include_router(trips.router)
    app.include_router(chat.router)
    app.include_router(votes.router)
    app.include_router(feedback.router)
    app.include_router(itineraries.router)
    app.include_router(agent.router)

    return app


app = create_app()
