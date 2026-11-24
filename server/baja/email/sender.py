import logging
from dataclasses import dataclass, field

import httpx

from baja.config import EmailSenderType, settings

log = logging.getLogger("baja.email")


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True)
class Email:
    to: tuple[str, ...]
    subject: str
    html: str
    text: str
    cc: tuple[str, ...] = ()
    bcc: tuple[str, ...] = ()
    attachments: tuple[Attachment, ...] = field(default=())


class EmailRejected(Exception):
    """Resend refused the message itself: retrying would be refused too."""


class EmailSender:
    async def send(self, email: Email, *, idempotency_key: str | None) -> None:
        raise NotImplementedError


class LoggingEmailSender(EmailSender):
    async def send(self, email: Email, *, idempotency_key: str | None) -> None:
        log.info("Email to %s: %s\n%s", ", ".join(email.to), email.subject, email.text)


class ResendEmailSender(EmailSender):
    async def send(self, email: Email, *, idempotency_key: str | None) -> None:
        import base64

        payload = {
            "from": settings.EMAIL_FROM,
            "to": list(email.to),
            "cc": list(email.cc),
            "bcc": list(email.bcc),
            "subject": email.subject,
            "html": email.html,
            "text": email.text,
            "attachments": [
                {
                    "filename": attachment.filename,
                    "content": base64.b64encode(attachment.content).decode(),
                    "content_type": attachment.content_type,
                }
                for attachment in email.attachments
            ],
        }
        headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}
        if idempotency_key is not None:
            # Resend sends a retried job's message once, not once per try.
            headers["Idempotency-Key"] = idempotency_key
        async with httpx.AsyncClient(base_url=settings.RESEND_API_URL) as client:
            response = await client.post("/emails", json=payload, headers=headers)
        if response.status_code in {400, 403, 422}:
            raise EmailRejected(response.text)
        response.raise_for_status()


def get_email_sender() -> EmailSender:
    if settings.EMAIL_SENDER == EmailSenderType.resend:
        return ResendEmailSender()
    return LoggingEmailSender()
