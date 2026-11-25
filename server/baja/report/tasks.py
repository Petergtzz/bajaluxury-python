import calendar
import logging
from uuid import UUID

from baja.company.service import get_company
from baja.company.service import today as company_today
from baja.config import settings
from baja.email.renderer import render_email
from baja.email.sender import Attachment, Email, EmailRejected, get_email_sender
from baja.models import SendStatus
from baja.statement.endpoints import PDF, statement_filename
from baja.statement.pdf import render_statement_pdf
from baja.statement.service import statement_of
from baja.worker import actor, get_message_id, job_session

from .repository import ReportSendRepository
from .service import SEND, sent_now

log = logging.getLogger("baja.report")


@actor(SEND, throws=(EmailRejected,))
async def send_report(send_id: str) -> None:
    """
    A property's statement for a month, made from the ledger, emailed to its
    recipients and kept as sent. An address the provider refuses fails the
    send, with the reason, instead of retrying what would be refused again.
    """
    async with job_session() as session:
        send = await ReportSendRepository.from_session(session).get_by_id(UUID(send_id))
        if send is None or send.status != SendStatus.queued:
            return
        month = send.month
        end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
        company = await get_company(session)
        statement = await statement_of(session, send.property, month, end)
        pdf = render_statement_pdf(
            statement, company=company.name, generated=await company_today(session)
        )
        html, text = render_email(
            "monthly_report",
            first_name="",
            month=f"{month:%B %Y}",
            properties=[send.property.name],
            url=settings.FRONTEND_BASE_URL,
            company=company.name,
        )
        try:
            await get_email_sender().send(
                Email(
                    to=tuple(send.to_addresses),
                    cc=tuple(send.cc_addresses),
                    subject=f"{send.property.name}: your {month:%B %Y} statement",
                    html=html,
                    text=text,
                    attachments=(
                        Attachment(
                            filename=statement_filename(statement, "pdf"),
                            content=pdf,
                            content_type=PDF,
                        ),
                    ),
                ),
                # Stable across a job's retries, new for every send asked for.
                idempotency_key=f"report-{get_message_id() or send.id}",
            )
        except EmailRejected as rejected:
            log.warning("Report %s refused: %s", send_id, rejected)
            send.status = SendStatus.failed
            send.error = str(rejected)[:500]
            return
        sent_now(send)
        send.statement = pdf
