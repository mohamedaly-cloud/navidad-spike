"""Navidad results API."""

import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Response, status
from redis.exceptions import RedisError

DRAW_KEY = "navidad:draw"
PRIZES_KEY = "navidad:prizes"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One client and connection pool per process
    app.state.redis = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        socket_connect_timeout=1,  # fail fast instead of hanging a request or a probe
        socket_timeout=1,
        decode_responses=True,
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(title="Navidad results API", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    """Liveness: the process is up. Never touches Redis."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(response: Response):
    """Readiness: Redis answers and a draw has been published."""
    try:
        published = await app.state.redis.exists(DRAW_KEY, PRIZES_KEY) == 2
    except RedisError as e:
        logger.warning("readiness check failed: %s", e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "redis unavailable"}

    if not published:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "no draw published"}
    return {"status": "ready"}
