import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, case, func, or_, select

from baja.kit.repository import RepositoryBase
from baja.models import Property, Transaction, TransactionType

from .buckets import BUCKETS

# Every bucket in order, whichever are asked for: a concept belongs to the
# first that matches it, never to a later one because the first wasn't chosen.
BUCKET = case(
    *(
        (
            or_(
                *(
                    func.lower(Transaction.concept).like(pattern)
                    for pattern in bucket.patterns
                )
            ),
            bucket.key,
        )
        for bucket in BUCKETS
    ),
    else_=None,
)


class UtilitiesRepository(RepositoryBase[Transaction]):
    model = Transaction

    async def sum_by_month_and_bucket(
        self,
        visible: ColumnElement[bool],
        *,
        property_id: UUID | None,
        start: dt.date,
        end: dt.date,
    ) -> list[tuple[str, str, Decimal, int]]:
        """`(YYYY-MM, bucket, total, count)` of the expenses in a bucket."""
        month = func.to_char(Transaction.date, "YYYY-MM")
        bucket = BUCKET.label("bucket")
        statement = (
            select(month, bucket, func.sum(Transaction.amount), func.count())
            .join(Property, Property.id == Transaction.property_id)
            .where(
                Transaction.deleted_at.is_(None),
                Property.deleted_at.is_(None),
                Transaction.type == TransactionType.expense,
                Transaction.date >= start,
                Transaction.date <= end,
                BUCKET.is_not(None),
                visible,
            )
            .group_by(month, bucket)
        )
        if property_id is not None:
            statement = statement.where(Transaction.property_id == property_id)
        result = await self.session.execute(statement)
        return [(m, b, total, count) for m, b, total, count in result]
