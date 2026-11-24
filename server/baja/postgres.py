from typing import Literal

from fastapi import Request

from baja.config import settings
from baja.kit.db.postgres import AsyncEngine, AsyncReadSession, AsyncSession
from baja.kit.db.postgres import create_async_engine as _create_async_engine

type ProcessName = Literal["app", "worker", "scheduler", "script"]


def create_async_engine(process_name: ProcessName) -> AsyncEngine:
    return _create_async_engine(
        dsn=settings.get_postgres_dsn(),
        application_name=f"{settings.ENV.value}.{process_name}",
        debug=settings.SQLALCHEMY_DEBUG,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    )


async def get_db_session(request: Request) -> AsyncSession:
    session: AsyncSession = request.state.async_session
    return session


async def get_db_read_session(request: Request) -> AsyncReadSession:
    return await get_db_session(request)
