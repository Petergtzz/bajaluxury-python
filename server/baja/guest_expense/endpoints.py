import datetime as dt
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.pagination import ListResource, PaginationParamsQuery
from baja.models import GuestExpense, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived

from .schemas import GuestExpenseCreate, GuestExpenseSchema, GuestExpenseUpdate
from .service import GuestExpenseDeleted
from .service import guest_expense as guest_expense_service

router = APIRouter(prefix="/guest-expenses", tags=["guest expenses"])

ReadUser = Annotated[User, Depends(Authorize(Permission.guest_expenses_read))]
ManageUser = Annotated[User, Depends(Authorize(Permission.guest_expenses_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}
Refused: dict[int | str, dict[str, Any]] = {
    409: {"model": PropertyArchived.schema() | GuestExpenseDeleted.schema()}
}


@router.get("/", response_model=ListResource[GuestExpenseSchema], responses=Errors)
async def list_guest_expenses(
    user: ReadUser,
    pagination: PaginationParamsQuery,
    property_id: UUID | None = None,
    category: str | None = Query(None, description="Ignoring case."),
    start_date: dt.date | None = Query(None, description="From this day on."),
    end_date: dt.date | None = Query(None, description="Up to and including."),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> ListResource[GuestExpenseSchema]:
    """Newest first, from the properties the caller may see."""
    guest_expenses, count = await guest_expense_service.list(
        session,
        user,
        pagination=pagination,
        property_id=property_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    return ListResource.from_paginated_results(
        [GuestExpenseSchema.model_validate(g) for g in guest_expenses],
        count,
        pagination,
    )


@router.post(
    "/",
    response_model=GuestExpenseSchema,
    status_code=201,
    responses={**Errors, **NotFound, **Refused},
)
async def create_guest_expense(
    guest_expense_create: GuestExpenseCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> GuestExpense:
    guest_expense, _ = await guest_expense_service.record(
        session, user, guest_expense_create, source="web"
    )
    return guest_expense


@router.get(
    "/{guest_expense_id}",
    response_model=GuestExpenseSchema,
    responses={**Errors, **NotFound},
)
async def get_guest_expense(
    guest_expense_id: UUID,
    user: ReadUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> GuestExpense:
    return await guest_expense_service.get(session, user, guest_expense_id)


@router.patch(
    "/{guest_expense_id}",
    response_model=GuestExpenseSchema,
    responses={**Errors, **NotFound, **Refused},
)
async def update_guest_expense(
    guest_expense_id: UUID,
    guest_expense_update: GuestExpenseUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> GuestExpense:
    guest_expense = await guest_expense_service.get(session, user, guest_expense_id)
    return await guest_expense_service.update(
        session, user, guest_expense, guest_expense_update
    )


@router.delete("/{guest_expense_id}", status_code=204, responses={**Errors, **NotFound})
async def delete_guest_expense(
    guest_expense_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    guest_expense = await guest_expense_service.get(session, user, guest_expense_id)
    await guest_expense_service.delete(session, guest_expense)
