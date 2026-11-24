from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from baja.app import create_app
from baja.kit.db.postgres import AsyncSessionMaker
from baja.redis import Redis
from tests.fixtures.database import app_sessions


class StateInjectingApp:
    """Hands the app the test's sessions in place of what its lifespan would open."""

    def __init__(
        self, app: ASGIApp, sessionmaker: AsyncSessionMaker, redis: Redis
    ) -> None:
        self.app = app
        self.sessionmaker = sessionmaker
        self.redis = redis

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            scope["state"] = {
                "async_sessionmaker": self.sessionmaker,
                "redis": self.redis,
            }
        await self.app(scope, receive, send)


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(
    app: FastAPI, connection: AsyncConnection, redis: Redis
) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(
        app=StateInjectingApp(app, app_sessions(connection), redis)
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
