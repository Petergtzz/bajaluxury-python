from typing import Annotated, Any

from fastapi import APIRouter, Depends

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import BadRequest, NotPermitted, Unauthorized
from baja.guest_expense.service import GuestExpenseDeleted
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.ledger.service import TransactionDeleted
from baja.models import TransactionType, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived

from .schemas import Categories, ShortcutConfirmation, ShortcutEntry, Villas
from .service import shortcut as shortcut_service

router = APIRouter(prefix="/shortcut", tags=["shortcut"])

# Recording needs guest expenses too; today both go to the same roles.
RecordingUser = Annotated[User, Depends(Authorize(Permission.transactions_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}


@router.get("/villas", response_model=Villas, responses=Errors)
async def list_villas(
    user: RecordingUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> Villas:
    """Active villas, by name, for the villa picker."""
    return Villas(villas=await shortcut_service.list_villas(session, user))


@router.get("/categories", response_model=Categories, responses=Errors)
async def list_categories(
    user: RecordingUser,
    type: TransactionType = TransactionType.expense,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Categories:
    """Most used first, from history, so the list needs no upkeep."""
    return Categories(
        categories=await shortcut_service.list_categories(session, user, type)
    )


@router.post(
    "/expenses",
    response_model=ShortcutConfirmation,
    responses={
        **Errors,
        400: {"model": BadRequest.schema()},
        409: {
            "model": PropertyArchived.schema()
            | TransactionDeleted.schema()
            | GuestExpenseDeleted.schema()
        },
    },
)
async def create_entry(
    entry: ShortcutEntry,
    user: RecordingUser,
    session: AsyncSession = Depends(get_db_session),
) -> ShortcutConfirmation:
    """
    Records an expense, income or guest expense for one or more villas.

    Safe to resend: an entry already saved is not saved again, and the
    confirmation says so.
    """
    return await shortcut_service.record(session, user, entry)
