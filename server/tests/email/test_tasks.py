import pytest

from baja.config import settings
from baja.email import tasks
from baja.email.sender import Email, EmailSender
from baja.kit.crypto import seal


class RecordingSender(EmailSender):
    def __init__(self) -> None:
        self.sent: list[Email] = []

    async def send(self, email: Email, *, idempotency_key: str | None) -> None:
        self.sent.append(email)


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    sender = RecordingSender()
    monkeypatch.setattr(tasks, "get_email_sender", lambda: sender)
    return sender


async def test_the_login_code_email_carries_the_code(sender: RecordingSender) -> None:
    sealed = seal("482913", secret=settings.SECRET, purpose=tasks.LOGIN_CODE_PURPOSE)

    await tasks.send_login_code("owner@bajaluxurymgmt.com", sealed)

    [email] = sender.sent
    assert email.to == ("owner@bajaluxurymgmt.com",)
    assert email.subject == "Your Baja Luxury login code: 482913"
    assert "482913" in email.html
    assert "482913" in email.text
    assert "10 minutes" in email.text


async def test_a_code_sealed_for_something_else_is_not_sent(
    sender: RecordingSender,
) -> None:
    sealed = seal("482913", secret=settings.SECRET, purpose="something-else")

    await tasks.send_login_code("owner@bajaluxurymgmt.com", sealed)

    assert sender.sent == []
