from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Select, func

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import Property, User


class PropertyRepository(RepositoryBase[Property]):
    model = Property

    def get_visible_statement(self, user: User) -> Select[Property]:
        return self.get_base_statement().where(visible_properties(user, Property.id))

    async def list_visible(
        self, user: User, *, is_archived: bool | None = None
    ) -> list[Property]:
        statement = self.get_visible_statement(user).order_by(func.lower(Property.name))
        if is_archived is not None:
            statement = statement.where(Property.is_archived.is_(is_archived))
        return await self.get_all(statement)

    async def get_visible(self, user: User, property_id: UUID) -> Property | None:
        return await self.get_one_or_none(
            self.get_visible_statement(user).where(Property.id == property_id)
        )

    async def get_by_name(self, name: str) -> Property | None:
        return await self.get_one_or_none(
            self.get_base_statement().where(func.lower(Property.name) == name.lower())
        )

    async def count_existing(self, property_ids: Collection[UUID]) -> int:
        statement = self.get_base_statement().where(Property.id.in_(property_ids))
        return len(await self.get_all(statement))
