from uuid import UUID

from baja.exceptions import Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Property, User

from .repository import PropertyRepository
from .schemas import PropertyCreate, PropertyUpdate


class PropertyNameTaken(Conflict):
    def __init__(self) -> None:
        super().__init__("Another property already has this name.")


class PropertyArchived(Conflict):
    def __init__(self) -> None:
        super().__init__("This property is archived and takes no new entries.")


class PropertyService:
    async def list(
        self, session: AsyncReadSession, user: User, *, is_archived: bool | None
    ) -> list[Property]:
        return await PropertyRepository.from_session(session).list_visible(
            user, is_archived=is_archived
        )

    async def get(
        self, session: AsyncReadSession, user: User, property_id: UUID
    ) -> Property:
        property = await PropertyRepository.from_session(session).get_visible(
            user, property_id
        )
        if property is None:
            raise ResourceNotFound()
        return property

    async def get_open(
        self, session: AsyncReadSession, user: User, property_id: UUID
    ) -> Property:
        """A property that still takes new work: not archived."""
        property = await self.get(session, user, property_id)
        if property.is_archived:
            raise PropertyArchived()
        return property

    async def create(
        self, session: AsyncSession, property_create: PropertyCreate
    ) -> Property:
        repository = PropertyRepository.from_session(session)
        await self._check_name_free(repository, property_create.name)
        return await repository.create(Property(**property_create.model_dump()))

    async def update(
        self, session: AsyncSession, property: Property, property_update: PropertyUpdate
    ) -> Property:
        repository = PropertyRepository.from_session(session)
        changes = property_update.model_dump(exclude_unset=True)
        for key in ("name", "is_archived", "balance_methods"):
            if changes.get(key) is None:
                changes.pop(key, None)
        if "name" in changes and changes["name"].lower() != property.name.lower():
            await self._check_name_free(repository, changes["name"])
        return await repository.update(property, changes)

    async def _check_name_free(self, repository: PropertyRepository, name: str) -> None:
        if await repository.get_by_name(name) is not None:
            raise PropertyNameTaken()


property = PropertyService()
