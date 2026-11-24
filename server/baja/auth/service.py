from datetime import datetime

from fastapi import Request, Response

from baja.config import settings
from baja.kit.crypto import generate_token_hash_pair, get_token_hash
from baja.kit.db.postgres import AsyncSession
from baja.kit.utils import utc_now
from baja.models import ApiToken, User, UserSession

from .models import ANONYMOUS, AuthSubject
from .repository import ApiTokenRepository, UserSessionRepository

USER_SESSION_TOKEN_PREFIX = "bl_us_"
API_TOKEN_PREFIX = "bl_at_"


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
        self, session: AsyncSession, request: Request
    ) -> AuthSubject:
        """
        Who sent the request: an `Authorization: Bearer` API token, else the
        session cookie. A bearer token that is wrong is anonymous: it never
        falls back to the cookie.
        """
        scheme, _, credentials = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer":
            api_token = await self._authenticate_api_token(session, credentials)
            if api_token is None:
                return ANONYMOUS
            return AuthSubject(user=api_token.user, api_token=api_token)

        token = request.cookies.get(settings.USER_SESSION_COOKIE_KEY)
        if token is None or not token.isascii():
            return ANONYMOUS
        user_session = await UserSessionRepository.from_session(
            session
        ).get_active_by_token_hash(get_token_hash(token, secret=settings.SECRET))
        if user_session is None:
            return ANONYMOUS
        return AuthSubject(user=user_session.user, session=user_session)

    async def issue_api_token(
        self, session: AsyncSession, user: User, *, label: str
    ) -> tuple[str, ApiToken]:
        """The token itself exists only here: show it now or it is lost."""
        token, token_hash = generate_token_hash_pair(
            secret=settings.SECRET, prefix=API_TOKEN_PREFIX
        )
        api_token = ApiToken(token=token_hash, label=label, user=user)
        await ApiTokenRepository.from_session(session).create(api_token)
        return token, api_token

    async def revoke_api_token(
        self, session: AsyncSession, api_token: ApiToken
    ) -> None:
        await ApiTokenRepository.from_session(session).soft_delete(api_token)

    async def _authenticate_api_token(
        self, session: AsyncSession, token: str
    ) -> ApiToken | None:
        # Shortcuts keeps the trailing newline of a pasted token.
        token = token.strip()
        if not token or not token.isascii():
            return None
        repository = ApiTokenRepository.from_session(session)
        api_token = await repository.get_active_by_token_hash(
            get_token_hash(token, secret=settings.SECRET)
        )
        if api_token is not None:
            await repository.update(api_token, {"last_used_at": utc_now()})
        return api_token

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
