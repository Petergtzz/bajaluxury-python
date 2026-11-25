import datetime as dt
from uuid import UUID

from sqlalchemy import Select, func, select

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import GuestExpense, User


class GuestExpenseRepository(RepositoryBase[GuestExpense]):
    model = GuestExpense

    def get_visible_statement(self, user: User) -> Select[GuestExpense]:
        return self.get_base_statement().where(
            visible_properties(user, GuestExpense.property_id)
        )

    def get_list_statement(
        self,
        user: User,
        *,
        property_id: UUID | None = None,
        category: str | None = None,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
        invoiced: bool | None = None,
    ) -> Select[GuestExpense]:
        statement = self.get_visible_statement(user).order_by(
            GuestExpense.date.desc(), GuestExpense.created_at.desc()
        )
        if property_id is not None:
            statement = statement.where(GuestExpense.property_id == property_id)
        if category is not None:
            statement = statement.where(
                func.lower(GuestExpense.category) == category.lower()
            )
        if start_date is not None:
            statement = statement.where(GuestExpense.date >= start_date)
        if end_date is not None:
            statement = statement.where(GuestExpense.date <= end_date)
        if invoiced is not None:
            billed = GuestExpense.invoice_id.is_not(None)  # type: ignore[attr-defined]
            statement = statement.where(billed if invoiced else ~billed)
        return statement

    async def get_visible(
        self, user: User, guest_expense_id: UUID
    ) -> GuestExpense | None:
        return await self.get_one_or_none(
            self.get_visible_statement(user).where(GuestExpense.id == guest_expense_id)
        )

    def get_by_external_id_statement(
        self, source: str, external_id: str
    ) -> Select[GuestExpense]:
        """Deleted ones too: their key stays taken."""
        return select(GuestExpense).where(
            GuestExpense.source == source, GuestExpense.external_id == external_id
        )
