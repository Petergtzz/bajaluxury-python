import datetime as dt
import io
from typing import Any

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from baja.kit.db.postgres import AsyncSession
from baja.models import Company, MonthlyReport, Role, User
from baja.monthly_report import tasks
from baja.monthly_report.service import previous_month, queue_due
from baja.worker import collect_jobs
from tests.email.test_tasks import RecordingSender
from tests.fixtures import (
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

NOVEMBER = dt.date(2026, 11, 1)


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    sender = RecordingSender()
    monkeypatch.setattr(tasks, "get_email_sender", lambda: sender)
    return sender


async def homeowner(
    save_fixture: SaveFixture, email: str, *properties: Any, receives: bool = True
) -> User:
    user = await create_user(
        save_fixture, Role.homeowner, email=email, name="Lore Gutierrez"
    )
    user.receives_monthly_report = receives
    await assign_properties(save_fixture, user, *properties)
    return user


async def queue(session: AsyncSession, **kwargs: Any) -> tuple[list[str], list[Any]]:
    async with collect_jobs() as jobs:
        queued = await queue_due(session, NOVEMBER, **kwargs)
        return queued, list(jobs)


def test_the_report_is_for_the_last_whole_month() -> None:
    assert previous_month(dt.date(2026, 12, 2)) == NOVEMBER
    assert previous_month(dt.date(2027, 1, 31)) == dt.date(2026, 12, 1)


async def test_queues_homeowners_who_asked_for_it_once(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    sold = await create_property(save_fixture, name="Sold", is_archived=True)
    await homeowner(save_fixture, "lore@example.com", campo)
    await homeowner(save_fixture, "no@example.com", campo, receives=False)
    await homeowner(save_fixture, "sold@example.com", sold)
    owner = await create_user(save_fixture, Role.owner, email="boss@example.com")
    owner.receives_monthly_report = True

    dry, dry_jobs = await queue(session, dry_run=True)
    first, jobs = await queue(session)

    assert (dry, dry_jobs) == (["lore@example.com"], [])
    assert first == ["lore@example.com"]
    [report] = (await session.execute(select(MonthlyReport))).scalars()
    assert jobs == [("monthly_report.send", (str(report.id),))]


async def test_a_claim_is_queued_again_until_it_is_sent(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    await homeowner(save_fixture, "lore@example.com", campo)
    _, jobs = await queue(session)

    _, lost_and_queued_again = await queue(session)
    report = (await session.execute(select(MonthlyReport))).scalar_one()
    report.sent_at = dt.datetime(2026, 12, 2, tzinfo=dt.UTC)
    sent, none = await queue(session)
    dry, _ = await queue(session, dry_run=True)

    assert lost_and_queued_again == jobs
    assert (sent, none, dry) == ([], [], [])
    assert len((await session.execute(select(MonthlyReport))).all()) == 1


async def test_sends_a_statement_for_each_property(
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    worker_resources: None,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    await create_transaction(
        save_fixture, campo, date=dt.date(2026, 11, 10), amount="8500"
    )
    await create_transaction(save_fixture, campo, date=dt.date(2026, 12, 1), amount="7")
    await homeowner(save_fixture, "lore@example.com", campo, colinas)
    await create_user(save_fixture, Role.owner, email="boss@example.com")
    await create_user(save_fixture, Role.manager, email="angel@example.com")
    _, jobs = await queue(session)

    await tasks.send_monthly_report(*jobs[0][1])

    [email] = sender.sent
    assert email.to == ("lore@example.com",)
    assert email.bcc == ("boss@example.com",)
    assert email.subject == "Your November 2026 statement"
    assert "Hola, Lore." in email.text
    assert "Campo 9, Colinas 21" in email.text
    assert "Hola, Lore." in email.html
    assert "Campo\u00a09, Colinas\u00a021" in email.html
    assert [a.filename for a in email.attachments] == [
        "campo-9-statement-2026-11-01-2026-11-30.pdf",
        "colinas-21-statement-2026-11-01-2026-11-30.pdf",
    ]
    text = PdfReader(io.BytesIO(email.attachments[0].content)).pages[0].extract_text()
    assert "8,500.00" in text
    assert "7.00" not in text
    report = (await session.execute(select(MonthlyReport))).scalar_one()
    await session.refresh(report)
    assert report.sent_at is not None


async def test_a_report_is_sent_once(
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    worker_resources: None,
) -> None:
    campo = await create_property(save_fixture)
    await homeowner(save_fixture, "lore@example.com", campo)
    _, jobs = await queue(session)

    await tasks.send_monthly_report(*jobs[0][1])
    await tasks.send_monthly_report(*jobs[0][1])

    assert len(sender.sent) == 1


async def test_nothing_is_sent_to_someone_gone(
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    worker_resources: None,
) -> None:
    campo = await create_property(save_fixture)
    await homeowner(save_fixture, "lore@example.com", campo)
    _, jobs = await queue(session)
    campo.is_archived = True
    await session.flush()

    await tasks.send_monthly_report(*jobs[0][1])

    assert sender.sent == []
