from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie, HTTPBearer

from baja.config import settings
from baja.exceptions import Unauthorized
from baja.models import User

from .models import AuthSubject

session_cookie_scheme = APIKeyCookie(
    name=settings.USER_SESSION_COOKIE_KEY,
    scheme_name="session",
    description="Session cookie set by the login endpoints.",
    auto_error=False,
)
api_token_scheme = HTTPBearer(
    scheme_name="api_token",
    description="An API token, for devices such as the Shortcut.",
    auto_error=False,
)


async def get_auth_subject(
    request: Request,
    _cookie: str | None = Security(session_cookie_scheme),
    _bearer: object = Security(api_token_scheme),
) -> AuthSubject:
    auth_subject: AuthSubject = request.state.auth_subject
    return auth_subject


async def get_current_user(
    auth_subject: Annotated[AuthSubject, Depends(get_auth_subject)],
) -> User:
    if auth_subject.user is None:
        raise Unauthorized()
    return auth_subject.user


CurrentAuthSubject = Annotated[AuthSubject, Depends(get_auth_subject)]
CurrentUser = Annotated[User, Depends(get_current_user)]
