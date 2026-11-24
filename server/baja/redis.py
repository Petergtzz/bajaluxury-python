from typing import Literal

from fastapi import Request
from redis.asyncio import Redis

from baja.config import settings

type ProcessName = Literal["app", "worker", "scheduler", "script"]


def create_redis(process_name: ProcessName) -> Redis:
    return Redis.from_url(
        settings.get_redis_url(),
        decode_responses=True,
        client_name=f"{settings.ENV.value}.{process_name}",
    )


async def get_redis(request: Request) -> Redis:
    redis: Redis = request.state.redis
    return redis


__all__ = ["Redis", "create_redis", "get_redis"]
