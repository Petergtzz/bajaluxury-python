from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI

from baja.api import router as api_router
from baja.auth.middlewares import AuthSubjectMiddleware
from baja.exception_handlers import add_exception_handlers
from baja.health.endpoints import router as health_router
from baja.kit.db.postgres import AsyncSessionMaker, create_async_sessionmaker
from baja.middlewares import TransactionalMiddleware
from baja.postgres import create_async_engine
from baja.redis import Redis, create_redis


class State(TypedDict):
    async_sessionmaker: AsyncSessionMaker
    redis: Redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    engine = create_async_engine("app")
    redis = create_redis("app")
    yield {"async_sessionmaker": create_async_sessionmaker(engine), "redis": redis}
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Baja Luxury API", lifespan=lifespan)
    # Added inside out: the transaction wraps everything, auth runs inside it.
    app.add_middleware(AuthSubjectMiddleware)
    app.add_middleware(TransactionalMiddleware)
    add_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
