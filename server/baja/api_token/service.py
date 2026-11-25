from collections.abc import Sequence
from uuid import UUID

from baja.auth.repository import ApiTokenRepository
from baja.auth.service import auth as auth_service
from baja.authz.permission import Permission, has_permission
from baja.exceptions import ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import ApiToken, User


def _sees_all(user: User) -> bool:
    return has_permission(user.role, Permission.api_tokens_manage_all)


class ApiTokenService:
    async def list(self, session: AsyncReadSession, user: User) -> Sequence[ApiToken]:
        """An owner's view is every device; anyone else's, their own."""
        tokens = await ApiTokenRepository.from_session(session).list_all()
        return [t for t in tokens if _sees_all(user) or t.user_id == user.id]

    async def issue(
        self, session: AsyncSession, user: User, label: str
    ) -> tuple[str, ApiToken]:
        """A token for one of the caller's own devices, acting as them."""
        return await auth_service.issue_api_token(session, user, label=label)

    async def revoke(self, session: AsyncSession, user: User, token_id: UUID) -> None:
        for token in await self.list(session, user):
            if token.id == token_id:
                await auth_service.revoke_api_token(session, token)
                return
        raise ResourceNotFound()


api_token = ApiTokenService()
