from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import (
    Checklist,
    ChecklistItem,
    ChecklistTemplateItem,
    ChecklistType,
    User,
)


class TemplateItemRepository(RepositoryBase[ChecklistTemplateItem]):
    model = ChecklistTemplateItem

    async def list_all(
        self, type: ChecklistType | None = None
    ) -> list[ChecklistTemplateItem]:
        statement = self.get_base_statement().order_by(
            ChecklistTemplateItem.type,
            ChecklistTemplateItem.position,
            ChecklistTemplateItem.created_at,
        )
        if type is not None:
            statement = statement.where(ChecklistTemplateItem.type == type)
        return await self.get_all(statement)

    async def get_by_id(self, item_id: UUID) -> ChecklistTemplateItem | None:
        return await self.get_one_or_none(
            self.get_base_statement().where(ChecklistTemplateItem.id == item_id)
        )

    async def next_position(self, type: ChecklistType) -> int:
        position = await self.session.scalar(
            select(func.max(ChecklistTemplateItem.position)).where(
                ChecklistTemplateItem.type == type,
                ChecklistTemplateItem.deleted_at.is_(None),
            )
        )
        return (position or 0) + 1


class ChecklistRepository(RepositoryBase[Checklist]):
    model = Checklist

    def get_visible_statement(self, user: User) -> Select[Checklist]:
        return (
            self.get_base_statement()
            .where(visible_properties(user, Checklist.property_id))
            .options(selectinload(Checklist.items))
        )

    async def list_visible(
        self, user: User, *, property_id: UUID | None
    ) -> list[Checklist]:
        statement = self.get_visible_statement(user).order_by(
            Checklist.created_at.desc()
        )
        if property_id is not None:
            statement = statement.where(Checklist.property_id == property_id)
        return await self.get_all(statement)

    async def get_visible(
        self, user: User, checklist_id: UUID, *, fresh: bool = False
    ) -> Checklist | None:
        """`fresh` reloads it and its items over what the session holds."""
        statement = self.get_visible_statement(user).where(Checklist.id == checklist_id)
        if fresh:
            statement = statement.execution_options(populate_existing=True)
        return await self.get_one_or_none(statement)


class ChecklistItemRepository(RepositoryBase[ChecklistItem]):
    model = ChecklistItem

    async def get_in(self, checklist_id: UUID, item_id: UUID) -> ChecklistItem | None:
        return await self.get_one_or_none(
            self.get_base_statement().where(
                ChecklistItem.checklist_id == checklist_id, ChecklistItem.id == item_id
            )
        )
