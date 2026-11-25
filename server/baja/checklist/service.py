from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from baja.exceptions import BajaError, Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now
from baja.models import (
    Checklist,
    ChecklistItem,
    ChecklistRecipient,
    ChecklistTemplateItem,
    Property,
    RecipientKind,
    User,
)
from baja.property.repository import PropertyRepository
from baja.property.service import property as property_service
from baja.recipient.service import check_recipients
from baja.worker import enqueue_job

from .repository import (
    ChecklistItemRepository,
    ChecklistRecipientRepository,
    ChecklistRepository,
    TemplateItemRepository,
)
from .schemas import (
    ChecklistCreate,
    ChecklistItemUpdate,
    ChecklistRecipientsUpdate,
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
        self, session: AsyncSession, user: User, checklist: Checklist
    ) -> Checklist:
        """
        Freezes it and emails its report, after the request commits, to its
        property's recipients as they are now: changing them later changes
        who hears about the next one, not who heard about this one.
        """
        if checklist.completed_at is not None:
            raise ChecklistCompleted()
        recipients = await ChecklistRecipientRepository.from_session(session).list_for(
            checklist.property_id
        )
        await ChecklistRepository.from_session(session).update(
            checklist,
            {
                "completed_at": utc_now(),
                "emailed_to": _emails(recipients, RecipientKind.to),
                "emailed_cc": _emails(recipients, RecipientKind.cc),
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


@dataclass(frozen=True)
class PropertyRecipients:
    property: Property
    recipients: list[ChecklistRecipient]


class ChecklistRecipientService:
    async def list(
        self, session: AsyncReadSession, user: User
    ) -> list[PropertyRecipients]:
        """Every active property, with who hears about its checklists."""
        properties = await PropertyRepository.from_session(session).list_visible(
            user, is_archived=False
        )
        by_property: dict[UUID, list[ChecklistRecipient]] = {}
        for recipient in await ChecklistRecipientRepository.from_session(
            session
        ).list_for():
            by_property.setdefault(recipient.property_id, []).append(recipient)
        return [
            PropertyRecipients(property, by_property.get(property.id, []))
            for property in properties
        ]

    async def set(
        self,
        session: AsyncSession,
        user: User,
        property_id: UUID,
        update: ChecklistRecipientsUpdate,
    ) -> PropertyRecipients:
        property = await property_service.get_open(session, user, property_id)
        chosen = await check_recipients(session, property, update.recipients)
        repository = ChecklistRecipientRepository.from_session(session)
        await repository.replace(
            property.id,
            [
                ChecklistRecipient(property_id=property.id, user_id=user_id, kind=kind)
                for user_id, kind in chosen.items()
            ],
        )
        return PropertyRecipients(property, await repository.list_for(property.id))


def _emails(recipients: list[ChecklistRecipient], kind: RecipientKind) -> list[str]:
    return [r.user.email for r in recipients if r.kind == kind]


checklist_template = TemplateService()
checklist = ChecklistService()
checklist_recipients = ChecklistRecipientService()
