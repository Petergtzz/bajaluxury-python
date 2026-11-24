from dataclasses import dataclass

from baja.models import User, UserSession


@dataclass(frozen=True)
class AuthSubject:
    """Who is calling: a user with a session cookie, or nobody."""

    user: User | None
    session: UserSession | None


ANONYMOUS = AuthSubject(user=None, session=None)
