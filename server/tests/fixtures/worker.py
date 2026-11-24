from collections.abc import Iterator
from typing import Any

import pytest
from dramatiq.brokers.stub import StubBroker
from sqlalchemy.ext.asyncio import AsyncConnection

from baja.redis import Redis
from baja.worker import WorkerResources, broker
from tests.fixtures.database import app_sessions


@pytest.fixture(autouse=True)
def sent_jobs() -> Iterator[list[tuple[str, tuple[Any, ...]]]]:
    """What has been handed to the queue, as (actor name, arguments), in order."""
    assert isinstance(broker, StubBroker)
    broker.flush_all()
    jobs: list[tuple[str, tuple[Any, ...]]] = []
    original = broker.enqueue

    def enqueue(message: Any, *, delay: int | None = None) -> Any:
        jobs.append((message.actor_name, tuple(message.args)))
        return original(message, delay=delay)

    broker.enqueue = enqueue  # type: ignore[method-assign]
    yield jobs
    broker.enqueue = original  # type: ignore[method-assign]
    broker.flush_all()


@pytest.fixture
def worker_resources(connection: AsyncConnection, redis: Redis) -> Iterator[None]:
    """Runs jobs inside the test's transaction, as the worker would outside it."""
    WorkerResources.sessionmaker = app_sessions(connection)
    WorkerResources.redis = redis
    yield
    WorkerResources.sessionmaker = None
    WorkerResources.redis = None
