from sqlalchemy import delete, func

from baja.kit.repository import RepositoryBase
from baja.kit.utils import utc_now
from baja.models import LoginCode


class LoginCodeRepository(RepositoryBase[LoginCode]):
    model = LoginCode

    async def get_valid_by_email(self, email: str) -> LoginCode | None:
        statement = self.get_base_statement().where(
            func.lower(LoginCode.email) == email.lower(),
            LoginCode.expires_at > utc_now(),
        )
        return await self.get_one_or_none(statement)

    async def delete_by_email(self, email: str) -> None:
        """Hard delete: a used or replaced code is worth nothing as history."""
        await self.session.execute(
            delete(LoginCode).where(func.lower(LoginCode.email) == email.lower())
        )
