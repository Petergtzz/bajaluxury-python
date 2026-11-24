from starlette.types import ASGIApp, Message, Receive, Scope, Send

from baja.kit.db.postgres import AsyncSessionMaker
from baja.worker import collect_jobs, send_jobs


class TransactionalMiddleware:
    """
    One database transaction per request, committed once.

    Services never commit. The response decides: it commits when a success
    starts going out and rolls back on an error status or an exception, so a
    request either happens whole or not at all. Jobs it queued are sent after
    the commit, and dropped with a rollback.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        sessionmaker: AsyncSessionMaker = scope["state"]["async_sessionmaker"]
        async with sessionmaker() as session, collect_jobs() as jobs:
            scope["state"]["async_session"] = session
            finished = False

            async def send_wrapper(message: Message) -> None:
                nonlocal finished
                if message["type"] == "http.response.start" and not finished:
                    finished = True
                    if message["status"] < 400:
                        await session.commit()
                        await send_jobs(jobs)
                    else:
                        await session.rollback()
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except BaseException:
                if not finished:
                    await session.rollback()
                raise
