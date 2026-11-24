from dataclasses import dataclass

from baja.models import ApiToken, User, UserSession


@dataclass(frozen=True)
class AuthSubject:
    """Who is calling: a user with a session cookie or an API token, or nobody."""

    user: User | None
    session: UserSession | None = None
    api_token: ApiToken | None = None


ANONYMOUS = AuthSubject(user=None)
