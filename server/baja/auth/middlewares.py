from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from .service import auth as auth_service


class AuthSubjectMiddleware:
    """Works out who is calling, once per request, inside its transaction."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        scope["state"]["auth_subject"] = await auth_service.authenticate(
            scope["state"]["async_session"], Request(scope)
        )
        await self.app(scope, receive, send)
