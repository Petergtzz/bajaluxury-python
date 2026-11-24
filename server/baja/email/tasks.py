import logging

from baja.config import settings
from baja.kit.crypto import SealedValueInvalid, unseal
from baja.worker import actor, get_message_id

from .renderer import render_email
from .sender import Email, EmailRejected, get_email_sender

log = logging.getLogger("baja.email")

LOGIN_CODE_PURPOSE = "login-code"


@actor("email.send_login_code", throws=(EmailRejected,))
async def send_login_code(to: str, sealed_code: str) -> None:
    """The code travels sealed: Redis never holds one anyone could read and use."""
    try:
        code = unseal(
            sealed_code,
            secret=settings.SECRET,
            purpose=LOGIN_CODE_PURPOSE,
            max_age=settings.LOGIN_CODE_TTL,
        )
    except SealedValueInvalid:
        log.warning("Login code for %s expired before it was sent", to)
        return
    minutes = int(settings.LOGIN_CODE_TTL.total_seconds() // 60)
    html, text = render_email("login_code", code=code, minutes=minutes)
    await get_email_sender().send(
        Email(
            to=(to,),
            subject=f"Your Baja Luxury login code: {code}",
            html=html,
            text=text,
        ),
        idempotency_key=get_message_id(),
    )
