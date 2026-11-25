from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import Company, GuestExpense, Invoice, User


class InvoiceRepository(RepositoryBase[Invoice]):
    model = Invoice

    def get_visible_statement(self, user: User) -> Select[Invoice]:
        return (
            self.get_base_statement()
            .where(visible_properties(user, Invoice.property_id))
            .options(selectinload(Invoice.lines))
        )

    async def list_visible(
        self, user: User, *, property_id: UUID | None
    ) -> list[Invoice]:
        statement = self.get_visible_statement(user).order_by(
            Invoice.year.desc(), Invoice.sequence.desc()
        )
        if property_id is not None:
            statement = statement.where(Invoice.property_id == property_id)
        return await self.get_all(statement)

    async def get_visible(
        self, user: User, invoice_id: UUID, *, fresh: bool = False
    ) -> Invoice | None:
        statement = self.get_visible_statement(user).where(Invoice.id == invoice_id)
        if fresh:
            statement = statement.execution_options(populate_existing=True)
        return await self.get_one_or_none(statement)

    async def next_sequence(self, year: int) -> int:
        """
        The year's next number. Holds the company row until the transaction
        ends, so two invoices issued at once are numbered one after the other.
        """
        await self.session.execute(select(Company.id).with_for_update())
        last = await self.session.scalar(
            # Deleted ones too: a number is never given out twice.
            select(func.max(Invoice.sequence)).where(Invoice.year == year)
        )
        return (last or 0) + 1

    async def get_guest_expenses(
        self, ids: Collection[UUID]
    ) -> dict[UUID, GuestExpense]:
        result = await self.session.execute(
            select(GuestExpense).where(
                GuestExpense.id.in_(ids), GuestExpense.deleted_at.is_(None)
            )
        )
        return {guest_expense.id: guest_expense for guest_expense in result.scalars()}
