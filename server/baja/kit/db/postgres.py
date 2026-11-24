from typing import NewType

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine
from sqlalchemy.orm.session import JoinTransactionMode

# Read-only code takes an AsyncReadSession, so the type checker stops it writing.
AsyncReadSession = NewType("AsyncReadSession", _AsyncSession)
AsyncSession = NewType("AsyncSession", AsyncReadSession)
type AsyncSessionMaker = async_sessionmaker[AsyncSession]


def create_async_engine(
    *,
    dsn: str,
    application_name: str,
    debug: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    return _create_async_engine(
        dsn,
        echo=debug,
        connect_args={"server_settings": {"application_name": application_name}},
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


def create_async_sessionmaker(
    bind: AsyncEngine | AsyncConnection,
    *,
    join_transaction_mode: JoinTransactionMode = "conditional_savepoint",
) -> AsyncSessionMaker:
    return async_sessionmaker(  # type: ignore[return-value]
        bind,
        expire_on_commit=False,
        class_=_AsyncSession,
        join_transaction_mode=join_transaction_mode,
    )


__all__ = [
    "AsyncEngine",
    "AsyncReadSession",
    "AsyncSession",
    "AsyncSessionMaker",
    "create_async_engine",
    "create_async_sessionmaker",
]
