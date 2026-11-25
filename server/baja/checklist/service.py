from collections.abc import Sequence
from uuid import UUID

from baja.exceptions import BajaError, Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now
from baja.models import Checklist, ChecklistItem, ChecklistTemplateItem, User
from baja.property.service import property as property_service
from baja.worker import enqueue_job

from .repository import (
    ChecklistItemRepository,
    ChecklistRepository,
    TemplateItemRepository,
)
from .schemas import (
    ChecklistComplete,
    ChecklistCreate,
    ChecklistItemUpdate,
    TemplateItemCreate,
    TemplateItemUpdate,
    TemplateOrder,
)

SEND_REPORT = "checklist.send_report"


class ChecklistCompleted(Conflict):
    def __init__(self) -> None:
        super().__init__("This checklist is completed: its report stands as sent.")


class OrderInvalid(BajaError):
    def __init__(self) -> None:
        super().__init__(
            "The order must name every item of the type once, and only those.", 422
        )


class TemplateService:
    async def list(self, session: AsyncReadSession) -> list[ChecklistTemplateItem]:
        return await TemplateItemRepository.from_session(session).list_all()

    async def get(
        self, session: AsyncReadSession, item_id: UUID
    ) -> ChecklistTemplateItem:
        item = await TemplateItemRepository.from_session(session).get_by_id(item_id)
        if item is None:
            raise ResourceNotFound()
        return item

    async def create(
        self, session: AsyncSession, item_create: TemplateItemCreate
    ) -> ChecklistTemplateItem:
        """At the end of its type's list."""
        repository = TemplateItemRepository.from_session(session)
        return await repository.create(
            ChecklistTemplateItem(
                type=item_create.type,
                description=item_create.description,
                position=await repository.next_position(item_create.type),
            )
        )

    async def update(
        self,
        session: AsyncSession,
        item: ChecklistTemplateItem,
        item_update: TemplateItemUpdate,
    ) -> ChecklistTemplateItem:
        """Checklists already started keep the wording they were given."""
        return await TemplateItemRepository.from_session(session).update(
            item, {"description": item_update.description}
        )

    async def delete(self, session: AsyncSession, item: ChecklistTemplateItem) -> None:
        await TemplateItemRepository.from_session(session).soft_delete(item)

    async def reorder(
        self, session: AsyncSession, order: TemplateOrder
    ) -> Sequence[ChecklistTemplateItem]:
        repository = TemplateItemRepository.from_session(session)
        items = {item.id: item for item in await repository.list_all(order.type)}
        if len(order.item_ids) != len(items) or set(order.item_ids) != set(items):
            raise OrderInvalid()
        for position, item_id in enumerate(order.item_ids, start=1):
            items[item_id].position = position
        await session.flush()
        return [items[item_id] for item_id in order.item_ids]


class ChecklistService:
    async def list(
        self, session: AsyncReadSession, user: User, *, property_id: UUID | None
    ) -> list[Checklist]:
        return await ChecklistRepository.from_session(session).list_visible(
            user, property_id=property_id
        )

    async def get(
        self, session: AsyncReadSession, user: User, checklist_id: UUID
    ) -> Checklist:
        checklist = await ChecklistRepository.from_session(session).get_visible(
            user, checklist_id
        )
        if checklist is None:
            raise ResourceNotFound()
        return checklist

    async def create(
        self, session: AsyncSession, user: User, checklist_create: ChecklistCreate
    ) -> Checklist:
        """Starts one with its type's template items, as they read today."""
        property = await property_service.get_open(
            session, user, checklist_create.property_id
        )
        checklist = await ChecklistRepository.from_session(session).create(
            Checklist(
                property_id=property.id,
                type=checklist_create.type,
                created_by_id=user.id,
            )
        )
        items = ChecklistItemRepository.from_session(session)
        templates = await TemplateItemRepository.from_session(session).list_all(
            checklist_create.type
        )
        for position, template in enumerate(templates, start=1):
            await items.create(
                ChecklistItem(
                    checklist_id=checklist.id,
                    description=template.description,
                    position=position,
                ),
                flush=False,
            )
        await session.flush()
        return await self._reloaded(session, user, checklist)

    async def update_item(
        self,
        session: AsyncSession,
        user: User,
        checklist: Checklist,
        item_id: UUID,
        item_update: ChecklistItemUpdate,
    ) -> Checklist:
        if checklist.completed_at is not None:
            raise ChecklistCompleted()
        repository = ChecklistItemRepository.from_session(session)
        item = await repository.get_in(checklist.id, item_id)
        if item is None:
            raise ResourceNotFound()
        changes = item_update.model_dump(exclude_unset=True)
        if changes.get("is_checked") is None:
            changes.pop("is_checked", None)
        elif changes["is_checked"] != item.is_checked:
            changes["checked_at"] = utc_now() if changes["is_checked"] else None
        if "note" in changes:
            changes["note"] = changes["note"] or None
        await repository.update(item, changes)
        return await self._reloaded(session, user, checklist)

    async def complete(
        self,
        session: AsyncSession,
        user: User,
        checklist: Checklist,
        checklist_complete: ChecklistComplete,
    ) -> Checklist:
        """Freezes it and emails its report, after the request commits."""
        if checklist.completed_at is not None:
            raise ChecklistCompleted()
        await ChecklistRepository.from_session(session).update(
            checklist,
            {
                "completed_at": utc_now(),
                "emailed_to": list(dict.fromkeys(checklist_complete.recipients)),
            },
        )
        enqueue_job(SEND_REPORT, str(checklist.id))
        return await self._reloaded(session, user, checklist)

    async def delete(self, session: AsyncSession, checklist: Checklist) -> None:
        await ChecklistRepository.from_session(session).soft_delete(checklist)

    async def _reloaded(
        self, session: AsyncSession, user: User, checklist: Checklist
    ) -> Checklist:
        reloaded = await ChecklistRepository.from_session(session).get_visible(
            user, checklist.id, fresh=True
        )
        assert reloaded is not None
        return reloaded


checklist_template = TemplateService()
checklist = ChecklistService()
