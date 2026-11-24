from collections.abc import Awaitable, Callable

from baja.auth.dependencies import CurrentUser
from baja.exceptions import NotPermitted
from baja.models import User

from .permission import DENIED, Permission, has_permission


def Authorize(permission: Permission) -> Callable[[User], Awaitable[User]]:
    """The calling user, once their role is known to hold `permission`."""

    async def authorize(user: CurrentUser) -> User:
        if not has_permission(user.role, permission):
            raise NotPermitted(DENIED[permission])
        return user

    return authorize
