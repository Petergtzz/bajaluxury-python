from collections.abc import AsyncIterator

import pytest
from fakeredis import FakeAsyncRedis

from baja.redis import Redis


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    redis = FakeAsyncRedis(decode_responses=True)
    yield redis
    await redis.aclose()
