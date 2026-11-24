from datetime import timedelta

from baja.exceptions import BajaError
from baja.redis import Redis


class TooManyRequests(BajaError):
    def __init__(
        self,
        retry_after: int,
        message: str = "Too many attempts. Please wait before trying again.",
    ) -> None:
        super().__init__(message, 429, headers={"Retry-After": str(retry_after)})


async def charge(redis: Redis, key: str, window: timedelta) -> int:
    """
    Counts one attempt in a fixed window and returns the count so far.

    Starting the window and counting run in one MULTI, so a counter can never
    exist without its expiry and lock someone out for good.
    """
    async with redis.pipeline(transaction=True) as pipeline:
        pipeline.set(key, 0, ex=int(window.total_seconds()), nx=True)
        pipeline.incr(key)
        _, count = await pipeline.execute()
    return int(count)


async def retry_after(redis: Redis, key: str) -> int:
    return max(int(await redis.ttl(key)), 1)


async def limit(redis: Redis, key: str, window: timedelta, maximum: int) -> None:
    """Charges an attempt and refuses it once the window holds more than `maximum`."""
    if await charge(redis, key, window) > maximum:
        raise TooManyRequests(await retry_after(redis, key))
