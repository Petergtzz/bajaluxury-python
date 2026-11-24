from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from .models import ANONYMOUS, AuthSubject
from .service import auth as auth_service


class AuthSubjectMiddleware:
    """Works out who is calling, once per request, inside its transaction."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        user_session = await auth_service.authenticate(
            scope["state"]["async_session"], Request(scope)
        )
        scope["state"]["auth_subject"] = (
            AuthSubject(user=user_session.user, session=user_session)
            if user_session is not None
            else ANONYMOUS
        )
        await self.app(scope, receive, send)
