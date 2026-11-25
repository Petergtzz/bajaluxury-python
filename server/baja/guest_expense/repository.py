from uuid import UUID

from sqlalchemy import Select, func, select

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import GuestExpense, User

from .schemas import GuestExpenseFilters, GuestExpenseSummary


class GuestExpenseRepository(RepositoryBase[GuestExpense]):
    model = GuestExpense

    def get_visible_statement(self, user: User) -> Select[GuestExpense]:
        return self.get_base_statement().where(
            visible_properties(user, GuestExpense.property_id)
        )

    def get_list_statement(
        self, user: User, filters: GuestExpenseFilters
    ) -> Select[GuestExpense]:
        statement = self.get_visible_statement(user).order_by(
            GuestExpense.date.desc(), GuestExpense.created_at.desc()
        )
        if filters.property_id is not None:
            statement = statement.where(GuestExpense.property_id == filters.property_id)
        if filters.category is not None:
            statement = statement.where(
                func.lower(GuestExpense.category) == filters.category.lower()
            )
        if filters.start_date is not None:
            statement = statement.where(GuestExpense.date >= filters.start_date)
        if filters.end_date is not None:
            statement = statement.where(GuestExpense.date <= filters.end_date)
        if filters.invoiced is not None:
            billed = GuestExpense.invoice_id.is_not(None)  # type: ignore[attr-defined]
            statement = statement.where(billed if filters.invoiced else ~billed)
        return statement

    async def summarize(self, statement: Select[GuestExpense]) -> GuestExpenseSummary:
        """Counts and sums what `statement` lists, and what of it is billed."""
        listed = statement.order_by(None).subquery()
        count, total, billed = (
            await self.session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(listed.c.amount), 0),
                    func.coalesce(
                        func.sum(listed.c.amount).filter(
                            listed.c.invoice_id.is_not(None)
                        ),
                        0,
                    ),
                )
            )
        ).one()
        return GuestExpenseSummary(count=count, total=total, billed_total=billed)

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
