import datetime as dt
from collections.abc import Iterable, Sequence
from decimal import Decimal
from uuid import UUID

from baja.authz.filters import visible_properties
from baja.company.service import get_company
from baja.exceptions import BajaError
from baja.kit.db.postgres import AsyncReadSession
from baja.models import Currency, Transaction, User
from baja.property.service import property as property_service
from baja.statement.service import PeriodInvalid, converter

from .buckets import BY_KEY, UTILITIES
from .repository import UtilitiesRepository
from .schemas import BucketSchema, BucketTotal, UtilitiesMonth, UtilitiesReport


class UnknownBuckets(BajaError):
    def __init__(self, keys: list[str]) -> None:
        super().__init__(
            f"No such buckets: {', '.join(keys)}. They are: {', '.join(BY_KEY)}.", 422
        )


async def build_utilities_report(
    session: AsyncReadSession,
    user: User,
    start: dt.date,
    end: dt.date,
    *,
    property_id: UUID | None = None,
    buckets: Sequence[str] = UTILITIES,
    currency: Currency | None = None,
) -> UtilitiesReport:
    """One property's, or every visible one's, when `property_id` is left out."""
    if end < start:
        raise PeriodInvalid()
    property = (
        await property_service.get(session, user, property_id)
        if property_id is not None
        else None
    )
    company = await get_company(session)
    currency = currency or company.currency
    convert = converter(company.currency, currency, company.usd_exchange_rate)
    keys = list(dict.fromkeys(buckets))
    if unknown := [key for key in keys if key not in BY_KEY]:
        raise UnknownBuckets(unknown)

    months = {month: _empty(keys) for month in _months(start, end)}
    rows = await UtilitiesRepository.from_session(session).sum_by_month_and_bucket(
        visible_properties(user, Transaction.property_id),
        property_id=property_id,
        start=start,
        end=end,
    )
    for month, bucket, total, count in rows:
        if bucket in months[month]:
            months[month][bucket] = BucketTotal(total=convert(total), count=count)

    return UtilitiesReport(
        property_id=property.id if property else None,
        property_name=property.name if property else None,
        start=start,
        end=end,
        currency=currency,
        exchange_rate=(
            company.usd_exchange_rate if currency != company.currency else None
        ),
        buckets=[BucketSchema(key=key, label=BY_KEY[key].label) for key in keys],
        months=[
            UtilitiesMonth(month=month, buckets=cells, total=_sum(cells.values()))
            for month, cells in months.items()
        ],
        totals={
            key: BucketTotal(
                total=_sum(cells[key] for cells in months.values()),
                count=sum(cells[key].count for cells in months.values()),
            )
            for key in keys
        },
        grand_total=_sum(cell for cells in months.values() for cell in cells.values()),
    )


def _months(start: dt.date, end: dt.date) -> list[str]:
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    return months


def _empty(keys: list[str]) -> dict[str, BucketTotal]:
    return {key: BucketTotal(total=Decimal(0), count=0) for key in keys}


def _sum(cells: Iterable[BucketTotal]) -> Decimal:
    return sum((cell.total for cell in cells), Decimal(0))
