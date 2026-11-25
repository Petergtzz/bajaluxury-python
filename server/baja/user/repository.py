from collections.abc import Collection
from uuid import UUID

from sqlalchemy import case, func, select, update

from baja.kit.repository import RepositoryBase
from baja.kit.utils import utc_now
from baja.models import PropertyMember, Role, User


class UserRepository(RepositoryBase[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        statement = self.get_base_statement().where(
            func.lower(User.email) == email.strip().lower()
        )
        return await self.get_one_or_none(statement)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.get_one_or_none(
            self.get_base_statement().where(User.id == user_id)
        )

    async def list_all(self) -> list[User]:
        return await self.get_all(
            self.get_base_statement().order_by(
                case(
                    {Role.owner: 0, Role.manager: 1, Role.homeowner: 2},
                    value=User.role,
                ),
                func.lower(func.coalesce(User.name, User.email)),
            )
        )

    async def get_property_ids(
        self, user_ids: Collection[UUID]
    ) -> dict[UUID, list[UUID]]:
        """Each user's assigned properties, for the users given."""
        result = await self.session.execute(
            select(PropertyMember.user_id, PropertyMember.property_id).where(
                PropertyMember.user_id.in_(user_ids),
                PropertyMember.deleted_at.is_(None),
            )
        )
        assigned: dict[UUID, list[UUID]] = {user_id: [] for user_id in user_ids}
        for user_id, property_id in result.all():
            assigned[user_id].append(property_id)
        return assigned

    async def set_property_ids(self, user: User, property_ids: set[UUID]) -> None:
        current = set((await self.get_property_ids([user.id]))[user.id])
        if removed := current - property_ids:
            await self.session.execute(
                update(PropertyMember)
                .where(
                    PropertyMember.user_id == user.id,
                    PropertyMember.property_id.in_(removed),
                    PropertyMember.deleted_at.is_(None),
                )
                .values(deleted_at=utc_now())
            )
        for property_id in property_ids - current:
            self.session.add(PropertyMember(user_id=user.id, property_id=property_id))
        await self.session.flush()

    async def list_owner_emails(self) -> list[str]:
        """Who is copied on what the company sends: its owners."""
        result = await self.session.execute(
            select(User.email).where(User.deleted_at.is_(None), User.role == Role.owner)
        )
        return list(result.scalars())
