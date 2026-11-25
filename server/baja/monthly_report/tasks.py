import calendar
import logging
from uuid import UUID

from baja.company.service import get_company
from baja.company.service import today as company_today
from baja.config import settings
from baja.email.renderer import render_email
from baja.email.sender import Attachment, Email, EmailRejected, get_email_sender
from baja.kit.utils import utc_now
from baja.property.repository import PropertyRepository
from baja.statement.endpoints import PDF, statement_filename
from baja.statement.pdf import render_statement_pdf
from baja.statement.service import build_statement
from baja.user.repository import UserRepository
from baja.worker import actor, job_session

from .service import SEND, MonthlyReportRepository

log = logging.getLogger("baja.monthly_report")


@actor(SEND, throws=(EmailRejected,))
async def send_monthly_report(report_id: str) -> None:
    """
    One homeowner's month: a statement for each property they have.

    Sent once: the email carries the report's id as its idempotency key, so
    a retry after a send whose commit failed is dropped by the provider.
    """
    async with job_session() as session:
        report = await MonthlyReportRepository.from_session(session).get_with_user(
            UUID(report_id)
        )
        if report is None or report.sent_at is not None:
            return
        user = report.user
        properties = await PropertyRepository.from_session(session).list_visible(
            user, is_archived=False
        )
        if user.deleted_at is not None or not properties:
            log.info("Monthly report %s has no one left to send to", report_id)
            return

        month = report.month
        end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
        company = await get_company(session)
        generated = await company_today(session)
        attachments = []
        for property in properties:
            statement = await build_statement(session, user, property.id, month, end)
            attachments.append(
                Attachment(
                    filename=statement_filename(statement, "pdf"),
                    content=render_statement_pdf(
                        statement, company=company.name, generated=generated
                    ),
                    content_type=PDF,
                )
            )
        html, text = render_email(
            "monthly_report",
            first_name=(user.name or "").split(" ")[0],
            month=f"{month:%B %Y}",
            properties=[property.name for property in properties],
            url=settings.FRONTEND_BASE_URL,
            company=company.name,
        )
        await get_email_sender().send(
            Email(
                to=(user.email,),
                bcc=tuple(
                    email
                    for email in await UserRepository.from_session(
                        session
                    ).list_owner_emails()
                    if email.lower() != user.email.lower()
                ),
                subject=f"Your {month:%B %Y} statement",
                html=html,
                text=text,
                attachments=tuple(attachments),
            ),
            idempotency_key=f"monthly-report-{report.id}",
        )
        report.sent_at = utc_now()
