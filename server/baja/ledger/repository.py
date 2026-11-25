import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, case, func, select

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import (
    Property,
    Transaction,
    TransactionType,
    User,
)

from .schemas import PropertyBalance, TransactionFilters, TransactionSummary

# Income adds to a balance, an expense takes from it.
SIGNED_AMOUNT = case(
    (Transaction.type == TransactionType.income, Transaction.amount),
    else_=-Transaction.amount,
)


class TransactionRepository(RepositoryBase[Transaction]):
    model = Transaction

    def get_visible_statement(self, user: User) -> Select[Transaction]:
        return self.get_base_statement().where(
            visible_properties(user, Transaction.property_id)
        )

    def get_list_statement(
        self, user: User, filters: TransactionFilters
    ) -> Select[Transaction]:
        statement = self.get_visible_statement(user).order_by(
            Transaction.date.desc(), Transaction.created_at.desc()
        )
        if filters.property_id is not None:
            statement = statement.where(Transaction.property_id == filters.property_id)
        if filters.type is not None:
            statement = statement.where(Transaction.type == filters.type)
        if filters.payment_method is not None:
            statement = statement.where(
                Transaction.payment_method == filters.payment_method
            )
        if filters.category is not None:
            statement = statement.where(
                func.lower(Transaction.category) == filters.category.lower()
            )
        if filters.start_date is not None:
            statement = statement.where(Transaction.date >= filters.start_date)
        if filters.end_date is not None:
            statement = statement.where(Transaction.date <= filters.end_date)
        return statement

    async def summarize(self, statement: Select[Transaction]) -> TransactionSummary:
        """Counts and sums what `statement` lists."""
        listed = statement.order_by(None).subquery()
        income = func.coalesce(
            func.sum(listed.c.amount).filter(listed.c.type == TransactionType.income),
            0,
        )
        expense = func.coalesce(
            func.sum(listed.c.amount).filter(listed.c.type == TransactionType.expense),
            0,
        )
        count, income_total, expense_total = (
            await self.session.execute(select(func.count(), income, expense))
        ).one()
        return TransactionSummary(
            count=count, income_total=income_total, expense_total=expense_total
        )

    async def get_visible(self, user: User, transaction_id: UUID) -> Transaction | None:
        return await self.get_one_or_none(
            self.get_visible_statement(user).where(Transaction.id == transaction_id)
        )

    def get_by_external_id_statement(
        self, source: str, external_id: str
    ) -> Select[Transaction]:
        """Deleted ones too: their key stays taken."""
        return select(Transaction).where(
            Transaction.source == source, Transaction.external_id == external_id
        )

    async def get_balance_before(self, property_id: UUID, day: dt.date) -> Decimal:
        """The property's balance at the start of `day`."""
        balance = await self.session.scalar(
            select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)).where(
                Transaction.property_id == property_id,
                Transaction.deleted_at.is_(None),
                Transaction.affects_balance,
                Transaction.date < day,
            )
        )
        return Decimal(balance or 0)

    async def list_between(
        self, property_id: UUID, start: dt.date, end: dt.date
    ) -> list[Transaction]:
        """In the order they happened, as far as the ledger knows it."""
        return await self.get_all(
            self.get_base_statement()
            .where(
                Transaction.property_id == property_id,
                Transaction.date >= start,
                Transaction.date <= end,
            )
            .order_by(Transaction.date, Transaction.created_at, Transaction.id)
        )

    async def list_categories(self, user: User, type: TransactionType) -> list[str]:
        """The categories in use, most used first."""
        statement = (
            select(Transaction.category)
            .where(
                Transaction.deleted_at.is_(None),
                Transaction.type == type,
                visible_properties(user, Transaction.property_id),
            )
            .group_by(Transaction.category)
            .order_by(func.count().desc(), Transaction.category)
        )
        return list((await self.session.execute(statement)).scalars())

    async def list_balances(
        self, visible: ColumnElement[bool], *, is_archived: bool | None = None
    ) -> list[PropertyBalance]:
        balance = func.coalesce(
            func.sum(SIGNED_AMOUNT).filter(Transaction.affects_balance), 0
        ).label("balance")
        statement = (
            select(
                Property.id,
                Property.name,
                balance,
                func.min(Transaction.date).label("first_activity_date"),
                func.max(Transaction.date)
                .filter(Transaction.type == TransactionType.income)
                .label("last_income_date"),
                func.max(Transaction.date).label("last_activity_date"),
            )
            .outerjoin(
                Transaction,
                and_(
                    Transaction.property_id == Property.id,
                    Transaction.deleted_at.is_(None),
                ),
            )
            .where(Property.deleted_at.is_(None), visible)
            .group_by(Property.id)
            .order_by(balance, func.lower(Property.name))
        )
        if is_archived is not None:
            statement = statement.where(Property.is_archived.is_(is_archived))
        result = await self.session.execute(statement)
        return [
            PropertyBalance(
                property_id=id,
                property_name=name,
                balance=balance,
                first_activity_date=first_activity_date,
                last_income_date=last_income_date,
                last_activity_date=last_activity_date,
            )
            for (
                id,
                name,
                balance,
                first_activity_date,
                last_income_date,
                last_activity_date,
            ) in result
        ]
