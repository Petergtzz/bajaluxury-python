from collections.abc import Sequence
from uuid import UUID

from baja.exceptions import Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.pagination import PaginationParams, paginate
from baja.kit.utils import generate_uuid
from baja.models import GuestExpense, User
from baja.property.service import property as property_service

from .repository import GuestExpenseRepository
from .schemas import (
    GuestExpenseCreate,
    GuestExpenseFilters,
    GuestExpenseSummary,
    GuestExpenseUpdate,
)


class GuestExpenseDeleted(Conflict):
    def __init__(self) -> None:
        super().__init__("This entry was recorded and then deleted.")


class GuestExpenseService:
    async def list(
        self,
        session: AsyncReadSession,
        user: User,
        filters: GuestExpenseFilters,
        *,
        pagination: PaginationParams,
    ) -> tuple[Sequence[GuestExpense], int]:
        statement = GuestExpenseRepository.from_session(session).get_list_statement(
            user, filters
        )
        return await paginate(session, statement, pagination=pagination)

    async def summarize(
        self, session: AsyncReadSession, user: User, filters: GuestExpenseFilters
    ) -> GuestExpenseSummary:
        """What `list` would list, added up across its pages."""
        repository = GuestExpenseRepository.from_session(session)
        return await repository.summarize(repository.get_list_statement(user, filters))

    async def get(
        self, session: AsyncReadSession, user: User, guest_expense_id: UUID
    ) -> GuestExpense:
        guest_expense = await GuestExpenseRepository.from_session(session).get_visible(
            user, guest_expense_id
        )
        if guest_expense is None:
            raise ResourceNotFound()
        return guest_expense

    async def record(
        self,
        session: AsyncSession,
        user: User,
        guest_expense_create: GuestExpenseCreate,
        *,
        source: str,
    ) -> tuple[GuestExpense, bool]:
        """Like the ledger's: once per `external_id`; whether it recorded a new one."""
        repository = GuestExpenseRepository.from_session(session)
        external_id = guest_expense_create.external_id or str(generate_uuid())
        existing = repository.get_by_external_id_statement(source, external_id)
        if (found := await repository.get_one_or_none(existing)) is not None:
            return self._replayed(found), False

        await property_service.get_open(session, user, guest_expense_create.property_id)
        guest_expense, created = await repository.create_once(
            GuestExpense(
                **guest_expense_create.model_dump(exclude={"external_id"}),
                source=source,
                external_id=external_id,
                entered_by_id=user.id,
            ),
            existing,
        )
        await self._load_invoice_id(session, guest_expense)
        return self._replayed(guest_expense), created

    async def update(
        self,
        session: AsyncSession,
        user: User,
        guest_expense: GuestExpense,
        guest_expense_update: GuestExpenseUpdate,
    ) -> GuestExpense:
        changes = {
            key: value
            for key, value in guest_expense_update.model_dump(
                exclude_unset=True
            ).items()
            if value is not None or key == "description"
        }
        if changes.get("property_id", guest_expense.property_id) != (
            guest_expense.property_id
        ):
            await property_service.get_open(session, user, changes["property_id"])
        await GuestExpenseRepository.from_session(session).update(
            guest_expense, changes
        )
        await self._load_invoice_id(session, guest_expense)
        return guest_expense

    async def delete(self, session: AsyncSession, guest_expense: GuestExpense) -> None:
        await GuestExpenseRepository.from_session(session).soft_delete(guest_expense)

    async def _load_invoice_id(
        self, session: AsyncReadSession, guest_expense: GuestExpense
    ) -> None:
        """Worked out by the database: read again after a write."""
        await session.refresh(guest_expense, ["invoice_id"])

    def _replayed(self, guest_expense: GuestExpense) -> GuestExpense:
        if guest_expense.deleted_at is not None:
            raise GuestExpenseDeleted()
        return guest_expense


guest_expense = GuestExpenseService()
