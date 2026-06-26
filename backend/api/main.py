"""FastAPI application entrypoint: app factory, CORS, lifespan, router registration."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import ado, assess, clarify, export, ingest, review
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StoryForge AI backend starting up")
    yield
    logger.info("StoryForge AI backend shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="StoryForge AI", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest.router)
    app.include_router(assess.router)
    app.include_router(clarify.router)
    app.include_router(review.router)
    app.include_router(ado.router)
    app.include_router(export.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
