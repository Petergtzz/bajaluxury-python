import datetime as dt
from collections import defaultdict
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from baja.company.service import get_company
from baja.exceptions import BajaError
from baja.kit.db.postgres import AsyncReadSession
from baja.ledger.repository import TransactionRepository
from baja.models import Currency, PaymentMethod, TransactionType, User
from baja.property.service import property as property_service

from .schemas import CategoryTotal, MethodTotal, Statement, StatementEntry

CENT = Decimal("0.01")


class PeriodInvalid(BajaError):
    def __init__(self) -> None:
        super().__init__("The period ends before it starts.", 422)


async def build_statement(
    session: AsyncReadSession,
    user: User,
    property_id: UUID,
    start: dt.date,
    end: dt.date,
    *,
    currency: Currency | None = None,
) -> Statement:
    """A visible property's statement for `start` to `end`, both included."""
    if end < start:
        raise PeriodInvalid()
    property = await property_service.get(session, user, property_id)
    company = await get_company(session)
    currency = currency or company.currency
    convert = _converter(company.currency, currency, company.usd_exchange_rate)

    repository = TransactionRepository.from_session(session)
    opening = convert(await repository.get_balance_before(property.id, start))
    balance = opening
    entries = []
    for transaction in await repository.list_between(property.id, start, end):
        amount = convert(transaction.amount)
        if transaction.affects_balance:
            balance += amount if transaction.type == TransactionType.income else -amount
        entries.append(
            StatementEntry(
                id=transaction.id,
                date=transaction.date,
                type=transaction.type,
                category=transaction.category,
                concept=transaction.concept,
                payment_method=transaction.payment_method,
                description=transaction.description,
                amount=amount,
                affects_balance=transaction.affects_balance,
                balance_after=balance,
            )
        )

    expenses = [e for e in entries if e.type == TransactionType.expense]
    by_method: dict[PaymentMethod | None, Decimal] = defaultdict(Decimal)
    by_category: dict[str, list[StatementEntry]] = defaultdict(list)
    for expense in expenses:
        by_method[expense.payment_method] += expense.amount
        by_category[expense.category].append(expense)

    return Statement(
        property_id=property.id,
        property_name=property.name,
        start=start,
        end=end,
        currency=currency,
        exchange_rate=(
            company.usd_exchange_rate if currency != company.currency else None
        ),
        opening_balance=opening,
        closing_balance=balance,
        income_total=sum(
            (e.amount for e in entries if e.type == TransactionType.income),
            Decimal(0),
        ),
        expense_total=sum((e.amount for e in expenses), Decimal(0)),
        balance_expense_total=sum(
            (e.amount for e in expenses if e.affects_balance), Decimal(0)
        ),
        expenses_by_method=sorted(
            (MethodTotal(payment_method=m, total=t) for m, t in by_method.items()),
            key=lambda method: -method.total,
        ),
        expenses_by_category=sorted(
            (
                CategoryTotal(
                    category=category,
                    total=sum((e.amount for e in items), Decimal(0)),
                    entries=sorted(items, key=lambda e: -e.amount),
                )
                for category, items in by_category.items()
            ),
            key=lambda category: (-category.total, category.category),
        ),
        entries=entries,
    )


def _converter(
    company_currency: Currency, currency: Currency, usd_rate: Decimal
) -> Callable[[Decimal], Decimal]:
    """From the company's currency to `currency`, to the cent."""
    if currency == company_currency:
        return lambda amount: amount
    if currency == Currency.USD:
        return lambda amount: (amount / usd_rate).quantize(CENT, ROUND_HALF_UP)
    return lambda amount: (amount * usd_rate).quantize(CENT, ROUND_HALF_UP)
