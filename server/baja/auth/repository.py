from sqlalchemy.orm import contains_eager

from baja.kit.repository import RepositoryBase
from baja.kit.utils import utc_now
from baja.models import User, UserSession


class UserSessionRepository(RepositoryBase[UserSession]):
    model = UserSession

    async def get_active_by_token_hash(self, token_hash: str) -> UserSession | None:
        statement = (
            self.get_base_statement()
            .join(UserSession.user)
            .where(
                UserSession.token == token_hash,
                UserSession.expires_at > utc_now(),
                User.deleted_at.is_(None),
            )
            .options(contains_eager(UserSession.user))
        )
        return await self.get_one_or_none(statement)
