from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Checklist, ChecklistTemplateItem, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived
from baja.recipient.service import RecipientsInvalid, to_schemas

from .schemas import (
    ChecklistCreate,
    ChecklistItemUpdate,
    ChecklistPropertySchema,
    ChecklistRecipientsUpdate,
    ChecklistSchema,
    TemplateItemCreate,
    TemplateItemSchema,
    TemplateItemUpdate,
    TemplateOrder,
)
from .service import ChecklistCompleted, OrderInvalid, PropertyRecipients
from .service import checklist as checklist_service
from .service import checklist_recipients as recipient_service
from .service import checklist_template as template_service

router = APIRouter(tags=["checklists"])

ReadUser = Annotated[User, Depends(Authorize(Permission.checklists_read))]
ManageUser = Annotated[User, Depends(Authorize(Permission.checklists_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}
Completed: dict[int | str, dict[str, Any]] = {
    409: {"model": ChecklistCompleted.schema()}
}


@router.get(
    "/checklist-templates/", response_model=list[TemplateItemSchema], responses=Errors
)
async def list_template_items(
    user: ManageUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> list[ChecklistTemplateItem]:
    """Every type's items, in order."""
    return await template_service.list(session)


@router.post(
    "/checklist-templates/",
    response_model=TemplateItemSchema,
    status_code=201,
    responses=Errors,
)
async def create_template_item(
    item_create: TemplateItemCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ChecklistTemplateItem:
    """Added at the end of its type."""
    return await template_service.create(session, item_create)


@router.put(
    "/checklist-templates/order",
    response_model=list[TemplateItemSchema],
    responses={**Errors, 422: {"model": OrderInvalid.schema()}},
)
async def reorder_template_items(
    order: TemplateOrder,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Sequence[ChecklistTemplateItem]:
    return await template_service.reorder(session, order)


@router.patch(
    "/checklist-templates/{item_id}",
    response_model=TemplateItemSchema,
    responses={**Errors, **NotFound},
)
async def update_template_item(
    item_id: UUID,
    item_update: TemplateItemUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ChecklistTemplateItem:
    """Checklists already started keep the wording they were given."""
    item = await template_service.get(session, item_id)
    return await template_service.update(session, item, item_update)


@router.delete(
    "/checklist-templates/{item_id}", status_code=204, responses={**Errors, **NotFound}
)
async def delete_template_item(
    item_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    item = await template_service.get(session, item_id)
    await template_service.delete(session, item)


def _recipients_schema(view: PropertyRecipients) -> ChecklistPropertySchema:
    return ChecklistPropertySchema(
        property_id=view.property.id,
        property_name=view.property.name,
        recipients=to_schemas(view.recipients),
    )


@router.get(
    "/checklists/properties",
    response_model=list[ChecklistPropertySchema],
    responses=Errors,
)
async def list_checklist_properties(
    user: ManageUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> list[ChecklistPropertySchema]:
    """Every active property, with who hears about its checklists."""
    return [
        _recipients_schema(view) for view in await recipient_service.list(session, user)
    ]


@router.put(
    "/checklists/properties/{property_id}",
    response_model=ChecklistPropertySchema,
    responses={
        **Errors,
        **NotFound,
        409: {"model": PropertyArchived.schema()},
        422: {"model": RecipientsInvalid.schema()},
    },
)
async def set_checklist_recipients(
    property_id: UUID,
    update: ChecklistRecipientsUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ChecklistPropertySchema:
    """Replaces who hears about the property's checklists; nobody is allowed."""
    return _recipients_schema(
        await recipient_service.set(session, user, property_id, update)
    )


@router.get("/checklists/", response_model=list[ChecklistSchema], responses=Errors)
async def list_checklists(
    user: ReadUser,
    property_id: UUID | None = None,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[Checklist]:
    """Newest first, from the properties the caller may see."""
    return await checklist_service.list(session, user, property_id=property_id)


@router.post(
    "/checklists/",
    response_model=ChecklistSchema,
    status_code=201,
    responses={**Errors, **NotFound, 409: {"model": PropertyArchived.schema()}},
)
async def create_checklist(
    checklist_create: ChecklistCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Checklist:
    """Starts one with its type's template items."""
    return await checklist_service.create(session, user, checklist_create)


@router.get(
    "/checklists/{checklist_id}",
    response_model=ChecklistSchema,
    responses={**Errors, **NotFound},
)
async def get_checklist(
    checklist_id: UUID,
    user: ReadUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Checklist:
    return await checklist_service.get(session, user, checklist_id)


@router.patch(
    "/checklists/{checklist_id}/items/{item_id}",
    response_model=ChecklistSchema,
    responses={**Errors, **NotFound, **Completed},
)
async def update_checklist_item(
    checklist_id: UUID,
    item_id: UUID,
    item_update: ChecklistItemUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Checklist:
    """Ticks or unticks an item, or notes on it."""
    checklist = await checklist_service.get(session, user, checklist_id)
    return await checklist_service.update_item(
        session, user, checklist, item_id, item_update
    )


@router.post(
    "/checklists/{checklist_id}/complete",
    response_model=ChecklistSchema,
    responses={**Errors, **NotFound, **Completed},
)
async def complete_checklist(
    checklist_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Checklist:
    """Freezes it and emails its report to its property's recipients."""
    checklist = await checklist_service.get(session, user, checklist_id)
    return await checklist_service.complete(session, user, checklist)


@router.delete(
    "/checklists/{checklist_id}", status_code=204, responses={**Errors, **NotFound}
)
async def delete_checklist(
    checklist_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    checklist = await checklist_service.get(session, user, checklist_id)
    await checklist_service.delete(session, checklist)
