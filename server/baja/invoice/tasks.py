from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from baja.company.service import get_company
from baja.email.renderer import render_email
from baja.email.sender import Attachment, Email, EmailRejected, get_email_sender
from baja.kit.utils import utc_now
from baja.models import Invoice, Property
from baja.statement.endpoints import PDF
from baja.user.repository import UserRepository
from baja.worker import actor, job_session

from .pdf import render_invoice_pdf
from .service import SEND


@actor(SEND, throws=(EmailRejected,))
async def send_invoice(invoice_id: str) -> None:
    async with job_session() as session:
        invoice = (
            await session.execute(
                select(Invoice)
                .where(Invoice.id == UUID(invoice_id), Invoice.deleted_at.is_(None))
                .options(selectinload(Invoice.lines))
            )
        ).scalar_one_or_none()
        if invoice is None or invoice.sent_at is not None:
            return
        property = await session.get_one(Property, invoice.property_id)
        company = await get_company(session)
        html, text = render_email(
            "invoice",
            recipient=invoice.recipient_name,
            number=invoice.number,
            property=property.name,
            total=f"{invoice.total:,.2f}",
            due=f"{invoice.due_on:%b %-d, %Y}",
            company=company.name,
        )
        await get_email_sender().send(
            Email(
                to=(invoice.email,),
                bcc=tuple(
                    email
                    for email in await UserRepository.from_session(
                        session
                    ).list_owner_emails()
                    if email.lower() != invoice.email.lower()
                ),
                subject=f"Invoice {invoice.number} · {property.name}",
                html=html,
                text=text,
                attachments=(
                    Attachment(
                        filename=f"{invoice.number}.pdf",
                        content=render_invoice_pdf(
                            invoice, company=company.name, property_name=property.name
                        ),
                        content_type=PDF,
                    ),
                ),
            ),
            idempotency_key=f"invoice-{invoice.id}",
        )
        invoice.sent_at = utc_now()
