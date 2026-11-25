import datetime as dt
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import contains_eager, selectinload, undefer

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.kit.utils import utc_now
from baja.models import (
    Property,
    PropertyReport,
    PropertyReportRecipient,
    ReportSend,
    SendStatus,
    User,
)


class PropertyReportRepository(RepositoryBase[PropertyReport]):
    model = PropertyReport

    def _with_recipients(self) -> Select[PropertyReport]:
        return self.get_base_statement().options(
            selectinload(PropertyReport.recipients).joinedload(
                PropertyReportRecipient.user
            )
        )

    async def list_all(self) -> list[PropertyReport]:
        return await self.get_all(self._with_recipients())

    async def get_for(self, property_id: UUID) -> PropertyReport | None:
        return await self.get_one_or_none(
            self._with_recipients()
            .where(PropertyReport.property_id == property_id)
            .execution_options(populate_existing=True)
        )

    async def replace_recipients(
        self, report: PropertyReport, recipients: list[PropertyReportRecipient]
    ) -> None:
        await self.session.execute(
            update(PropertyReportRecipient)
            .where(
                PropertyReportRecipient.property_report_id == report.id,
                PropertyReportRecipient.deleted_at.is_(None),
            )
            .values(deleted_at=utc_now())
        )
        self.session.add_all(recipients)
        await self.session.flush()

    async def list_due(self, month: dt.date, day: int) -> list[PropertyReport]:
        """Reports of active properties whose day has come and whose month hasn't gone."""
        sent = select(ReportSend.property_id).where(
            ReportSend.month == month, ReportSend.deleted_at.is_(None)
        )
        return await self.get_all(
            self._with_recipients()
            .join(PropertyReport.property)
            .options(contains_eager(PropertyReport.property))
            .where(
                PropertyReport.send_day <= day,
                Property.deleted_at.is_(None),
                Property.is_archived.is_(False),
                PropertyReport.property_id.not_in(sent),
            )
        )


class ReportSendRepository(RepositoryBase[ReportSend]):
    model = ReportSend

    def get_visible_statement(self, user: User) -> Select[ReportSend]:
        return (
            self.get_base_statement()
            .join(ReportSend.property)
            .options(contains_eager(ReportSend.property))
            .where(visible_properties(user, ReportSend.property_id))
        )

    async def list_visible(
        self, user: User, *, property_id: UUID | None
    ) -> list[ReportSend]:
        statement = self.get_visible_statement(user).order_by(
            ReportSend.month.desc(), func.lower(Property.name)
        )
        if property_id is not None:
            statement = statement.where(ReportSend.property_id == property_id)
        return await self.get_all(statement)

    async def get_visible(
        self, user: User, send_id: UUID, *, with_statement: bool = False
    ) -> ReportSend | None:
        statement = self.get_visible_statement(user).where(ReportSend.id == send_id)
        if with_statement:
            statement = statement.options(undefer(ReportSend.statement))
        return await self.get_one_or_none(statement)

    async def get_for(self, property_id: UUID, month: dt.date) -> ReportSend | None:
        return await self.get_one_or_none(
            self.get_base_statement().where(
                ReportSend.property_id == property_id, ReportSend.month == month
            )
        )

    async def get_by_id(self, send_id: UUID) -> ReportSend | None:
        return await self.get_one_or_none(
            self.get_base_statement()
            .join(ReportSend.property)
            .options(contains_eager(ReportSend.property))
            .where(ReportSend.id == send_id)
        )

    async def last_sent(self) -> dict[UUID, dt.datetime]:
        result = await self.session.execute(
            select(ReportSend.property_id, func.max(ReportSend.sent_at))
            .where(
                ReportSend.deleted_at.is_(None), ReportSend.status == SendStatus.sent
            )
            .group_by(ReportSend.property_id)
        )
        return {property_id: sent_at for property_id, sent_at in result if sent_at}
