"""
Background jobs, on Dramatiq with Redis.

A request or a job never sends a message itself: it calls `enqueue_job`, which
holds the message until the database transaction has committed. A job for a row
that was rolled back is never sent, and a job never runs before the row it reads
exists.
"""

import asyncio
import contextlib
import contextvars
import functools
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, ClassVar

import dramatiq
from dramatiq import middleware
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware import CurrentMessage

from baja.config import settings
from baja.kit.db.postgres import (
    AsyncEngine,
    AsyncSession,
    AsyncSessionMaker,
    create_async_sessionmaker,
)
from baja.postgres import create_async_engine
from baja.redis import Redis, create_redis

type Job = tuple[str, tuple[Any, ...]]

_queued_jobs: contextvars.ContextVar[list[Job] | None] = contextvars.ContextVar(
    "baja.queued_jobs", default=None
)


class WorkerResources(dramatiq.Middleware):
    """The database and Redis a worker process opens once, at boot."""

    engine: ClassVar[AsyncEngine | None] = None
    sessionmaker: ClassVar[AsyncSessionMaker | None] = None
    redis: ClassVar[Redis | None] = None

    def before_worker_boot(
        self, broker: dramatiq.Broker, worker: dramatiq.Worker
    ) -> None:
        WorkerResources.engine = create_async_engine("worker")
        WorkerResources.sessionmaker = create_async_sessionmaker(WorkerResources.engine)
        WorkerResources.redis = create_redis("worker")

    @classmethod
    def get_sessionmaker(cls) -> AsyncSessionMaker:
        if cls.sessionmaker is None:
            raise RuntimeError("The worker's database is not open")
        return cls.sessionmaker

    @classmethod
    def get_redis(cls) -> Redis:
        if cls.redis is None:
            raise RuntimeError("The worker's Redis is not open")
        return cls.redis


_middleware: list[dramatiq.Middleware] = [
    middleware.ShutdownNotifications(),
    middleware.AsyncIO(),
    WorkerResources(),
    middleware.AgeLimit(),
    middleware.TimeLimit(time_limit=settings.WORKER_TIME_LIMIT_MILLISECONDS),
    middleware.Retries(
        max_retries=settings.WORKER_MAX_RETRIES,
        min_backoff=settings.WORKER_MIN_BACKOFF_MILLISECONDS,
    ),
    middleware.CurrentMessage(),
]
# Tests keep messages in memory, where they can read what a request queued.
broker: dramatiq.Broker = (
    StubBroker(middleware=_middleware)
    if settings.is_testing()
    # Its own namespace: a Redis shared with other apps must not hand their
    # jobs to this worker, or this app's jobs to theirs.
    else RedisBroker(  # type: ignore[no-untyped-call]
        url=settings.get_redis_url(), middleware=_middleware, namespace="baja"
    )
)
dramatiq.set_broker(broker)


def enqueue_job(actor_name: str, *args: Any) -> None:
    """Queues a job to be sent once the current transaction has committed."""
    jobs = _queued_jobs.get()
    if jobs is None:
        raise RuntimeError("Jobs can only be queued inside a request or a job")
    jobs.append((actor_name, args))


@contextlib.asynccontextmanager
async def collect_jobs() -> AsyncIterator[list[Job]]:
    """Collects what `enqueue_job` queues; the caller sends or drops it."""
    jobs: list[Job] = []
    token = _queued_jobs.set(jobs)
    try:
        yield jobs
    finally:
        _queued_jobs.reset(token)


async def send_jobs(jobs: list[Job]) -> None:
    for actor_name, args in jobs:
        message = broker.get_actor(actor_name).message(*args)
        await asyncio.to_thread(broker.enqueue, message)
    jobs.clear()


@contextlib.asynccontextmanager
async def job_session() -> AsyncIterator[AsyncSession]:
    """A job's unit of work: commits when the job succeeds, then sends its jobs."""
    async with collect_jobs() as jobs:
        async with WorkerResources.get_sessionmaker()() as session:
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise
            await session.commit()
        await send_jobs(jobs)


def actor[**P](
    actor_name: str, **options: Any
) -> Callable[[Callable[P, Awaitable[None]]], Callable[P, Awaitable[None]]]:
    def decorator(fn: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
        @functools.wraps(fn)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
            await fn(*args, **kwargs)

        dramatiq.actor(actor_name=actor_name, **options)(wrapped)
        return wrapped

    return decorator


def get_message_id() -> str | None:
    """The running message's id: stable across retries, so an idempotency key."""
    message = CurrentMessage.get_current_message()
    return message.message_id if message is not None else None


__all__ = [
    "WorkerResources",
    "actor",
    "broker",
    "collect_jobs",
    "enqueue_job",
    "get_message_id",
    "job_session",
    "send_jobs",
]
