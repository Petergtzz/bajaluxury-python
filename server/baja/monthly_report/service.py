import datetime as dt
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import contains_eager

from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.repository import RepositoryBase
from baja.models import MonthlyReport, Property, PropertyMember, Role, User
from baja.worker import enqueue_job

SEND = "monthly_report.send"


class MonthlyReportRepository(RepositoryBase[MonthlyReport]):
    model = MonthlyReport

    async def list_recipients(self) -> list[User]:
        """Homeowners who asked for it and have a property still managed."""
        has_property = exists().where(
            PropertyMember.user_id == User.id,
            PropertyMember.deleted_at.is_(None),
            Property.id == PropertyMember.property_id,
            Property.deleted_at.is_(None),
            Property.is_archived.is_(False),
        )
        result = await self.session.execute(
            select(User)
            .where(
                User.deleted_at.is_(None),
                User.role == Role.homeowner,
                User.receives_monthly_report,
                has_property,
            )
            .order_by(func.lower(User.email))
        )
        return list(result.scalars())

    async def get_with_user(self, report_id: UUID) -> MonthlyReport | None:
        return await self.get_one_or_none(
            self.get_base_statement()
            .join(MonthlyReport.user)
            .options(contains_eager(MonthlyReport.user))
            .where(MonthlyReport.id == report_id)
        )


def previous_month(today: dt.date) -> dt.date:
    """The first day of the last whole month."""
    first = today.replace(day=1)
    return (first - dt.timedelta(days=1)).replace(day=1)


async def queue_due(
    session: AsyncSession, month: dt.date, *, dry_run: bool = False
) -> list[str]:
    """
    Queues `month`'s report for everyone who gets one and hasn't had it.

    Safe to run any number of times. Each person's month is claimed once and
    queued again on every run until it is sent: a claim whose job was lost
    (the queue down after the claim committed) is not lost with it, and a
    report queued twice is sent once. Says who it queued, or would queue.
    """
    repository = MonthlyReportRepository.from_session(session)
    queued = []
    for user in await repository.list_recipients():
        claimed = select(MonthlyReport).where(
            MonthlyReport.user_id == user.id, MonthlyReport.month == month
        )
        if dry_run:
            report = await repository.get_one_or_none(claimed)
        else:
            report, _ = await repository.create_once(
                MonthlyReport(user_id=user.id, month=month), claimed
            )
        if report is not None and report.sent_at is not None:
            continue
        if report is not None and not dry_run:
            enqueue_job(SEND, str(report.id))
        queued.append(user.email)
    return queued


async def list_owner_emails(session: AsyncReadSession) -> list[str]:
    result = await session.execute(
        select(User.email).where(User.deleted_at.is_(None), User.role == Role.owner)
    )
    return list(result.scalars())
