from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Property, User
from baja.postgres import get_db_read_session, get_db_session

from .schemas import PropertyCreate, PropertySchema, PropertyUpdate
from .service import PropertyNameTaken
from .service import property as property_service

router = APIRouter(prefix="/properties", tags=["properties"])

ReadUser = Annotated[User, Depends(Authorize(Permission.properties_read))]
ManageUser = Annotated[User, Depends(Authorize(Permission.properties_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}
NameTaken: dict[int | str, dict[str, Any]] = {
    409: {"model": PropertyNameTaken.schema()}
}


@router.get("/", response_model=list[PropertySchema], responses=Errors)
async def list_properties(
    user: ReadUser,
    is_archived: bool | None = Query(
        None, description="Only archived (`true`) or active (`false`) properties."
    ),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[Property]:
    """The properties the caller may see: all of them, or a homeowner's own."""
    return await property_service.list(session, user, is_archived=is_archived)


@router.post(
    "/",
    response_model=PropertySchema,
    status_code=201,
    responses={**Errors, **NameTaken},
)
async def create_property(
    property_create: PropertyCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Property:
    return await property_service.create(session, property_create)


@router.get(
    "/{property_id}", response_model=PropertySchema, responses={**Errors, **NotFound}
)
async def get_property(
    property_id: UUID,
    user: ReadUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Property:
    return await property_service.get(session, user, property_id)


@router.patch(
    "/{property_id}",
    response_model=PropertySchema,
    responses={**Errors, **NotFound, **NameTaken},
)
async def update_property(
    property_id: UUID,
    property_update: PropertyUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Property:
    """Renames, moves or archives a property. Archived ones take no new work."""
    property = await property_service.get(session, user, property_id)
    return await property_service.update(session, property, property_update)
