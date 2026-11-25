from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from baja.company.service import get_company
from baja.email.renderer import render_email
from baja.email.sender import Email, EmailRejected, get_email_sender
from baja.models import Checklist, ChecklistType, Property, User
from baja.user.repository import UserRepository
from baja.worker import actor, job_session

from .service import SEND_REPORT

TITLES = {
    ChecklistType.check_in: "Check-in completed",
    ChecklistType.check_out: "Check-out completed",
    ChecklistType.weekly: "Inspection report",
}


@actor(SEND_REPORT, throws=(EmailRejected,))
async def send_checklist_report(checklist_id: str) -> None:
    """What was checked, and what wasn't, with the notes on each."""
    async with job_session() as session:
        checklist = (
            await session.execute(
                select(Checklist)
                .where(Checklist.id == UUID(checklist_id))
                .options(selectinload(Checklist.items))
            )
        ).scalar_one_or_none()
        if checklist is None or checklist.completed_at is None:
            return
        property = await session.get_one(Property, checklist.property_id)
        author = (
            await session.get(User, checklist.created_by_id)
            if checklist.created_by_id
            else None
        )
        company = await get_company(session)
        completed = checklist.completed_at.astimezone(ZoneInfo(company.timezone))
        title = TITLES[checklist.type]
        html, text = render_email(
            "checklist_report",
            title=title,
            property=property.name,
            author=(author.name or author.email) if author else None,
            completed=f"{completed:%b %-d, %Y at %-I:%M %p}",
            checked=[item for item in checklist.items if item.is_checked],
            unchecked=[item for item in checklist.items if not item.is_checked],
            company=company.name,
        )
        recipients = {email.lower() for email in checklist.emailed_to}
        await get_email_sender().send(
            Email(
                to=tuple(checklist.emailed_to),
                bcc=tuple(
                    email
                    for email in await UserRepository.from_session(
                        session
                    ).list_owner_emails()
                    if email.lower() not in recipients
                ),
                subject=f"{title} · {property.name}",
                html=html,
                text=text,
            ),
            idempotency_key=f"checklist-report-{checklist.id}",
        )
