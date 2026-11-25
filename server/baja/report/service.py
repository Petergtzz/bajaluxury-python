import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from baja.authz.permission import Permission, has_permission
from baja.company.service import today as company_today
from baja.exceptions import BajaError, Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now
from baja.models import (
    Property,
    PropertyMember,
    PropertyReport,
    PropertyReportRecipient,
    RecipientKind,
    ReportSend,
    SendStatus,
    User,
)
from baja.property.repository import PropertyRepository
from baja.property.service import property as property_service
from baja.worker import enqueue_job

from .repository import PropertyReportRepository, ReportSendRepository
from .schemas import ReportUpdate

SEND = "report.send"


class RecipientsInvalid(BajaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class ReportIsOff(Conflict):
    def __init__(self) -> None:
        super().__init__("This property sends no report: choose who receives it first.")


class MonthNotOver(BajaError):
    def __init__(self) -> None:
        super().__init__("A month can be sent once it has started, not before.", 422)


@dataclass(frozen=True)
class ReportView:
    property: Property
    report: PropertyReport | None
    last_sent_at: dt.datetime | None


def previous_month(today: dt.date) -> dt.date:
    """The first day of the last whole month."""
    return (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)


class ReportService:
    async def list(self, session: AsyncReadSession, user: User) -> list[ReportView]:
        """Every active property, with the report it sends, if it sends one."""
        properties = await PropertyRepository.from_session(session).list_visible(
            user, is_archived=False
        )
        reports = {
            report.property_id: report
            for report in await PropertyReportRepository.from_session(
                session
            ).list_all()
        }
        last = await ReportSendRepository.from_session(session).last_sent()
        return [
            ReportView(property, reports.get(property.id), last.get(property.id))
            for property in properties
        ]

    async def set(
        self, session: AsyncSession, user: User, property_id: UUID, update: ReportUpdate
    ) -> ReportView:
        property = await property_service.get_open(session, user, property_id)
        recipients = await self._check_recipients(session, property, update)
        repository = PropertyReportRepository.from_session(session)
        report = await repository.get_for(property.id)
        if report is None:
            report = await repository.create(
                PropertyReport(property_id=property.id, send_day=update.send_day)
            )
        else:
            report.send_day = update.send_day
        await repository.replace_recipients(
            report,
            [
                PropertyReportRecipient(
                    property_report_id=report.id, user_id=user_id, kind=kind
                )
                for user_id, kind in recipients.items()
            ],
        )
        return await self._view(session, property)

    async def turn_off(
        self, session: AsyncSession, user: User, property_id: UUID
    ) -> None:
        property = await property_service.get(session, user, property_id)
        repository = PropertyReportRepository.from_session(session)
        report = await repository.get_for(property.id)
        if report is not None:
            await repository.replace_recipients(report, [])
            await repository.soft_delete(report)

    async def send_now(
        self,
        session: AsyncSession,
        user: User,
        property_id: UUID,
        month: dt.date | None,
    ) -> ReportSend:
        """Sends a month's statement now: anew, if that month already went."""
        property = await property_service.get(session, user, property_id)
        report = await PropertyReportRepository.from_session(session).get_for(
            property.id
        )
        if report is None or not report.recipients:
            raise ReportIsOff()
        today = await company_today(session)
        first = (month or previous_month(today)).replace(day=1)
        if first > today:
            raise MonthNotOver()
        return await self._queue(session, report, first)

    async def queue_due(self, session: AsyncSession) -> Sequence[ReportSend]:
        """
        Queues every statement whose day has come this month: last month's, for
        each property that reports. Safe to run any number of times: a month
        already queued or sent for a property is not queued again.
        """
        today = await company_today(session)
        month = previous_month(today)
        due = await PropertyReportRepository.from_session(session).list_due(
            month, today.day
        )
        return [
            await self._queue(session, report, month)
            for report in due
            if report.recipients
        ]

    async def list_sends(
        self, session: AsyncReadSession, user: User, *, property_id: UUID | None
    ) -> Sequence[ReportSend]:
        return await ReportSendRepository.from_session(session).list_visible(
            user, property_id=property_id
        )

    async def get_send(
        self, session: AsyncReadSession, user: User, send_id: UUID
    ) -> ReportSend:
        send = await ReportSendRepository.from_session(session).get_visible(
            user, send_id
        )
        if send is None:
            raise ResourceNotFound()
        return send

    async def get_statement(
        self, session: AsyncReadSession, user: User, send_id: UUID
    ) -> ReportSend:
        send = await ReportSendRepository.from_session(session).get_visible(
            user, send_id, with_statement=True
        )
        if send is None or send.statement is None:
            raise ResourceNotFound()
        return send

    async def _queue(
        self, session: AsyncSession, report: PropertyReport, month: dt.date
    ) -> ReportSend:
        """Addressed as the report stands now; who it went to is kept with it."""
        to = [r.user.email for r in report.recipients if r.kind == RecipientKind.to]
        cc = [r.user.email for r in report.recipients if r.kind == RecipientKind.cc]
        repository = ReportSendRepository.from_session(session)
        send = await repository.get_for(report.property_id, month)
        values = {
            "status": SendStatus.queued,
            "to_addresses": to,
            "cc_addresses": cc,
            "error": None,
        }
        if send is None:
            send = await repository.create(
                ReportSend(property_id=report.property_id, month=month, **values)
            )
        else:
            await repository.update(send, values)
        enqueue_job(SEND, str(send.id))
        return send

    async def _check_recipients(
        self, session: AsyncReadSession, property: Property, update: ReportUpdate
    ) -> dict[UUID, RecipientKind]:
        chosen = {recipient.user_id: recipient.kind for recipient in update.recipients}
        if len(chosen) != len(update.recipients):
            raise RecipientsInvalid("Someone is on it twice.")
        if RecipientKind.to not in chosen.values():
            raise RecipientsInvalid(
                "Address it to someone: at least one recipient is To."
            )
        users = (
            await session.execute(
                select(User).where(User.id.in_(chosen), User.deleted_at.is_(None))
            )
        ).scalars()
        members = set(
            (
                await session.execute(
                    select(PropertyMember.user_id).where(
                        PropertyMember.property_id == property.id,
                        PropertyMember.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        allowed = {
            user.id
            for user in users
            if has_permission(user.role, Permission.properties_read_all)
            or user.id in members
        }
        if allowed != set(chosen):
            raise RecipientsInvalid(
                "Everyone who receives it must be able to see the property."
            )
        return chosen

    async def _view(self, session: AsyncReadSession, property: Property) -> ReportView:
        report = await PropertyReportRepository.from_session(session).get_for(
            property.id
        )
        last = await ReportSendRepository.from_session(session).last_sent()
        return ReportView(property, report, last.get(property.id))


report = ReportService()


def sent_now(send: ReportSend) -> None:
    send.status = SendStatus.sent
    send.sent_at = utc_now()
    send.error = None
