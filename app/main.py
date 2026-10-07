"""Navidad results API."""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Path, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.exceptions import RedisError

from app.prizes import AMOUNTS

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


# --- Response models ---

class Draw(BaseModel):
    first: str
    second: str
    third: str
    fourth: list[str]
    fifth: list[str]
    pedrea: list[str]


class Prize(BaseModel):
    category: str
    amount_eur: int


class TicketResult(BaseModel):
    number: str
    prizes: list[Prize]
    total_eur: int  # per décimo, all categories combined


# --- Errors ---

@app.exception_handler(RedisError)
async def redis_unavailable(request: Request, exc: RedisError):
    """Map any Redis failure to a 503 without exposing internals."""
    logger.error("redis error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "service temporarily unavailable"},
    )


NOT_PUBLISHED = HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "results not published yet")


# --- Probes ---

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


# --- API ---

@app.get("/v1/results", response_model=Draw)
async def results():
    """The published draw."""
    draw = await app.state.redis.get(DRAW_KEY)
    if draw is None:
        raise NOT_PUBLISHED
    return json.loads(draw)


@app.get("/v1/tickets/{number}", response_model=TicketResult)
async def check_ticket(number: Annotated[str, Path(pattern=r"^\d{5}$")]):
    """Check one décimo. A non-winning number returns an empty list, not a 404."""
    # Both commands go to Redis in one round trip.
    async with app.state.redis.pipeline(transaction=False) as pipe:
        pipe.exists(DRAW_KEY)
        pipe.hget(PRIZES_KEY, number)
        published, categories = await pipe.execute()

    # An empty Redis must return 503, not "no prize" for every ticket.
    if not published:
        raise NOT_PUBLISHED

    prizes = [Prize(category=c, amount_eur=AMOUNTS[c]) for c in json.loads(categories or "[]")]
    return TicketResult(number=number, prizes=prizes, total_eur=sum(p.amount_eur for p in prizes))
