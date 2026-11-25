import datetime as dt
from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.pagination import ListResource, PaginationParamsQuery
from baja.models import PaymentMethod, Transaction, TransactionType, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived

from .schemas import (
    PropertyBalance,
    TransactionCreate,
    TransactionFilters,
    TransactionSchema,
    TransactionSummary,
    TransactionUpdate,
)
from .service import TransactionDeleted
from .service import ledger as ledger_service

router = APIRouter(tags=["ledger"])

ReadUser = Annotated[User, Depends(Authorize(Permission.transactions_read))]
ManageUser = Annotated[User, Depends(Authorize(Permission.transactions_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}
Refused: dict[int | str, dict[str, Any]] = {
    409: {"model": PropertyArchived.schema() | TransactionDeleted.schema()}
}


def get_filters(
    property_id: UUID | None = None,
    type: TransactionType | None = None,
    payment_method: PaymentMethod | None = None,
    category: str | None = Query(None, description="Ignoring case."),
    start_date: dt.date | None = Query(None, description="From this day on."),
    end_date: dt.date | None = Query(None, description="Up to and including."),
) -> TransactionFilters:
    return TransactionFilters(
        property_id=property_id,
        type=type,
        payment_method=payment_method,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


FiltersQuery = Annotated[TransactionFilters, Depends(get_filters)]


@router.get(
    "/transactions/",
    response_model=ListResource[TransactionSchema],
    responses=Errors,
)
async def list_transactions(
    user: ReadUser,
    filters: FiltersQuery,
    pagination: PaginationParamsQuery,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> ListResource[TransactionSchema]:
    """Newest first, from the properties the caller may see."""
    transactions, count = await ledger_service.list(
        session, user, filters, pagination=pagination
    )
    return ListResource.from_paginated_results(
        [TransactionSchema.model_validate(t) for t in transactions], count, pagination
    )


@router.get(
    "/transactions/summary",
    response_model=TransactionSummary,
    responses=Errors,
)
async def summarize_transactions(
    user: ReadUser,
    filters: FiltersQuery,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> TransactionSummary:
    """What the same filters list, counted and added up across every page."""
    return await ledger_service.summarize(session, user, filters)


@router.post(
    "/transactions/",
    response_model=TransactionSchema,
    status_code=201,
    responses={**Errors, **NotFound, **Refused},
)
async def create_transaction(
    transaction_create: TransactionCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Transaction:
    transaction, _ = await ledger_service.record(
        session, user, transaction_create, source="web"
    )
    return transaction


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionSchema,
    responses={**Errors, **NotFound},
)
async def get_transaction(
    transaction_id: UUID,
    user: ReadUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Transaction:
    return await ledger_service.get(session, user, transaction_id)


@router.patch(
    "/transactions/{transaction_id}",
    response_model=TransactionSchema,
    responses={**Errors, **NotFound, **Refused},
)
async def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Transaction:
    """Moving it to another property or method decides its balance effect again."""
    transaction = await ledger_service.get(session, user, transaction_id)
    return await ledger_service.update(session, user, transaction, transaction_update)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=204,
    responses={**Errors, **NotFound},
)
async def delete_transaction(
    transaction_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    transaction = await ledger_service.get(session, user, transaction_id)
    await ledger_service.delete(session, transaction)


@router.get("/balances/", response_model=list[PropertyBalance], responses=Errors)
async def list_balances(
    user: ReadUser,
    is_archived: bool | None = Query(
        None, description="Only archived (`true`) or active (`false`) properties."
    ),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Sequence[PropertyBalance]:
    """Each visible property's balance with us, the most owed first."""
    return await ledger_service.list_balances(session, user, is_archived=is_archived)
