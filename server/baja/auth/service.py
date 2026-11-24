from datetime import datetime

from fastapi import Request, Response

from baja.config import settings
from baja.kit.crypto import generate_token_hash_pair, get_token_hash
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now
from baja.models import User, UserSession

from .repository import UserSessionRepository

USER_SESSION_TOKEN_PREFIX = "bl_us_"


class AuthService:
    async def create_user_session(
        self, session: AsyncSession, user: User, *, user_agent: str
    ) -> tuple[str, UserSession]:
        token, token_hash = generate_token_hash_pair(
            secret=settings.SECRET, prefix=USER_SESSION_TOKEN_PREFIX
        )
        user_session = UserSession(
            token=token_hash,
            user_agent=user_agent,
            user=user,
            expires_at=utc_now() + settings.USER_SESSION_TTL,
        )
        await UserSessionRepository.from_session(session).create(user_session)
        return token, user_session

    async def authenticate(
        self, session: AsyncReadSession, request: Request
    ) -> UserSession | None:
        token = request.cookies.get(settings.USER_SESSION_COOKIE_KEY)
        if token is None or not token.isascii():
            return None
        return await UserSessionRepository.from_session(
            session
        ).get_active_by_token_hash(get_token_hash(token, secret=settings.SECRET))

    async def delete_user_session(
        self, session: AsyncSession, user_session: UserSession
    ) -> None:
        await UserSessionRepository.from_session(session).soft_delete(user_session)

    def set_session_cookie(
        self, request: Request, response: Response, token: str, expires_at: datetime
    ) -> None:
        response.set_cookie(
            settings.USER_SESSION_COOKIE_KEY,
            value=token,
            expires=expires_at,
            path="/",
            secure=not _is_localhost(request),
            httponly=True,
            samesite="lax",
        )

    def clear_session_cookie(self, request: Request, response: Response) -> None:
        response.delete_cookie(
            settings.USER_SESSION_COOKIE_KEY,
            path="/",
            secure=not _is_localhost(request),
            httponly=True,
            samesite="lax",
        )


def _is_localhost(request: Request) -> bool:
    return request.url.hostname in {"127.0.0.1", "localhost", "test"}


auth = AuthService()
