from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import RecurringCharge, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived

from .schemas import RecurringChargeCreate, RecurringChargeSchema, RecurringChargeUpdate
from .service import recurring_charge as recurring_charge_service

router = APIRouter(prefix="/recurring-charges", tags=["recurring charges"])

ManageUser = Annotated[User, Depends(Authorize(Permission.recurring_charges_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}


@router.get("/", response_model=list[RecurringChargeSchema], responses=Errors)
async def list_recurring_charges(
    user: ManageUser,
    property_id: UUID | None = None,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[RecurringCharge]:
    """By property, then by the day they fall due."""
    return await recurring_charge_service.list(session, user, property_id=property_id)


@router.post(
    "/",
    response_model=RecurringChargeSchema,
    status_code=201,
    responses={**Errors, **NotFound, 409: {"model": PropertyArchived.schema()}},
)
async def create_recurring_charge(
    charge_create: RecurringChargeCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> RecurringCharge:
    """Charged every month from `starts_on`, within the hour after midnight."""
    return await recurring_charge_service.create(session, user, charge_create)


@router.get(
    "/{recurring_charge_id}",
    response_model=RecurringChargeSchema,
    responses={**Errors, **NotFound},
)
async def get_recurring_charge(
    recurring_charge_id: UUID,
    user: ManageUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> RecurringCharge:
    return await recurring_charge_service.get(session, user, recurring_charge_id)


@router.patch(
    "/{recurring_charge_id}",
    response_model=RecurringChargeSchema,
    responses={**Errors, **NotFound},
)
async def update_recurring_charge(
    recurring_charge_id: UUID,
    charge_update: RecurringChargeUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> RecurringCharge:
    """From the next charge on: what was already charged stays as it was."""
    charge = await recurring_charge_service.get(session, user, recurring_charge_id)
    return await recurring_charge_service.update(session, charge, charge_update)


@router.delete(
    "/{recurring_charge_id}", status_code=204, responses={**Errors, **NotFound}
)
async def delete_recurring_charge(
    recurring_charge_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Stops it. What it already charged stays in the ledger."""
    charge = await recurring_charge_service.get(session, user, recurring_charge_id)
    await recurring_charge_service.delete(session, charge)
