import datetime as dt
import io
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

import baja.company.service
from baja.email.sender import EmailRejected
from baja.kit.db.postgres import AsyncSession
from baja.models import Company, Property, Role, User
from baja.report import tasks
from baja.report.service import report as report_service
from baja.worker import collect_jobs
from tests.email.test_tasks import RecordingSender
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

type Clock = Callable[[dt.datetime], None]
Jobs = list[tuple[str, tuple[Any, ...]]]


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    def set_now(now: dt.datetime) -> None:
        monkeypatch.setattr(baja.company.service, "utc_now", lambda: now)

    return set_now


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    sender = RecordingSender()
    monkeypatch.setattr(tasks, "get_email_sender", lambda: sender)
    return sender


def noon(year: int, month: int, day: int) -> dt.datetime:
    return dt.datetime(year, month, day, 19, tzinfo=dt.UTC)


async def lore(save_fixture: SaveFixture, *properties: Property) -> User:
    homeowner = await create_user(
        save_fixture, Role.homeowner, email="lore@example.com", name="Lore"
    )
    await assign_properties(save_fixture, homeowner, *properties)
    return homeowner


async def set_up(
    client: AsyncClient, property: Property, *recipients: tuple[User, str], day: int = 2
) -> Any:
    response = await client.put(
        f"/v1/reports/properties/{property.id}",
        json={
            "send_day": day,
            "recipients": [
                {"user_id": str(u.id), "kind": kind} for u, kind in recipients
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_every_active_property_shows_what_it_sends(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await create_property(save_fixture, name="Colinas 21")
    await create_property(save_fixture, name="Sold", is_archived=True)
    owner = await lore(save_fixture, campo)
    await login(user)

    saved = await set_up(client, campo, (user, "cc"), (owner, "to"), day=5)
    listed = (await client.get("/v1/reports/properties/")).json()

    assert [r["property_name"] for r in listed] == ["Campo 9", "Colinas 21"]
    assert listed[0] == saved
    assert (
        saved["send_day"],
        [(r["email"], r["kind"]) for r in saved["recipients"]],
    ) == (
        5,
        [("lore@example.com", "to"), (user.email, "cc")],
    )
    assert listed[1]["recipients"] == []


@pytest.mark.parametrize(
    ("who", "kinds", "problem"),
    [
        (
            "stranger",
            ["to"],
            "Everyone who receives it must be able to see the property.",
        ),
        ("lore", ["cc"], "Address it to someone: at least one recipient is To."),
        ("twice", ["to", "cc"], "Someone is on it twice."),
    ],
)
async def test_recipients_must_make_sense(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    who: str,
    kinds: list[str],
    problem: str,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    owner = await lore(save_fixture, campo)
    stranger = await create_user(save_fixture, Role.homeowner, email="s@example.com")
    await assign_properties(save_fixture, stranger, colinas)
    await login(user)
    person = stranger if who == "stranger" else owner

    response = await client.put(
        f"/v1/reports/properties/{campo.id}",
        json={"recipients": [{"user_id": str(person.id), "kind": k} for k in kinds]},
    )

    assert (response.status_code, response.json()["detail"]) == (422, problem)


async def test_turning_off_and_archived_properties(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    sold = await create_property(save_fixture, name="Sold", is_archived=True)
    await login(user)
    await set_up(client, campo, (user, "to"))

    off = await client.delete(f"/v1/reports/properties/{campo.id}")
    archived = await client.put(
        f"/v1/reports/properties/{sold.id}",
        json={"recipients": [{"user_id": str(user.id), "kind": "to"}]},
    )

    assert off.status_code == 204
    assert (await client.get("/v1/reports/properties/")).json()[0]["recipients"] == []
    assert archived.status_code == 409


async def test_homeowners_set_up_nothing(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    await login(await lore(save_fixture, campo))

    assert (await client.get("/v1/reports/properties/")).status_code == 403
    response = await client.post(f"/v1/reports/properties/{campo.id}/send", json={})
    assert response.status_code == 403


async def test_sending_now_queues_last_month_and_again_replaces_it(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
    sent_jobs: Jobs,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    owner = await lore(save_fixture, campo)
    await login(user)
    clock(noon(2026, 12, 9))
    off = await client.post(f"/v1/reports/properties/{campo.id}/send", json={})
    await set_up(client, campo, (owner, "to"), (user, "cc"))

    first = await client.post(f"/v1/reports/properties/{campo.id}/send", json={})
    again = await client.post(f"/v1/reports/properties/{campo.id}/send")
    future = await client.post(
        f"/v1/reports/properties/{campo.id}/send", json={"month": "2027-01-01"}
    )

    assert off.status_code == 409
    assert first.status_code == 202
    body = first.json()
    assert (body["month"], body["status"], body["to"], body["cc"]) == (
        "2026-11-01",
        "queued",
        ["lore@example.com"],
        [user.email],
    )
    assert again.json()["id"] == body["id"]
    assert future.status_code == 422
    assert sent_jobs == [("report.send", (body["id"],))] * 2


async def test_the_job_sends_and_keeps_the_statement(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
    sender: RecordingSender,
    sent_jobs: Jobs,
    worker_resources: None,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await create_transaction(
        save_fixture, campo, amount="8500", date=dt.date(2026, 11, 10)
    )
    owner = await lore(save_fixture, campo)
    await login(user)
    clock(noon(2026, 12, 9))
    await set_up(client, campo, (owner, "to"), (user, "cc"))
    send = (await client.post(f"/v1/reports/properties/{campo.id}/send")).json()

    await tasks.send_report(send["id"])
    await tasks.send_report(send["id"])

    [email] = sender.sent
    assert (email.to, email.cc) == (("lore@example.com",), (user.email,))
    assert email.subject == "Campo 9: your November 2026 statement"
    [attachment] = email.attachments
    assert (
        "8,500.00" in PdfReader(io.BytesIO(attachment.content)).pages[0].extract_text()
    )
    [history] = (await client.get("/v1/reports/sends/")).json()
    assert (history["status"], history["has_statement"], history["error"]) == (
        "sent",
        True,
        None,
    )
    download = await client.get(f"/v1/reports/sends/{send['id']}/statement.pdf")
    assert download.content == attachment.content
    assert download.headers["content-disposition"] == (
        'attachment; filename="campo-9-statement-2026-11.pdf"'
    )


async def test_an_address_refused_fails_the_send_with_why(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
    monkeypatch: pytest.MonkeyPatch,
    worker_resources: None,
) -> None:
    class Refusing(RecordingSender):
        async def send(self, email: Any, *, idempotency_key: str | None) -> None:
            raise EmailRejected("lore@example.com is not a valid address")

    monkeypatch.setattr(tasks, "get_email_sender", Refusing)
    campo = await create_property(save_fixture, name="Campo 9")
    await login(user)
    clock(noon(2026, 12, 9))
    await set_up(client, campo, (user, "to"))
    send = (await client.post(f"/v1/reports/properties/{campo.id}/send")).json()

    await tasks.send_report(send["id"])

    [history] = (await client.get("/v1/reports/sends/")).json()
    assert (history["status"], history["has_statement"], history["error"]) == (
        "failed",
        False,
        "lore@example.com is not a valid address",
    )


async def test_the_schedule_sends_each_month_once_on_its_day(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    await login(user)
    await set_up(client, campo, (user, "to"), day=2)
    await set_up(client, colinas, (user, "to"), day=10)

    async def sweep(now: dt.datetime) -> list[str]:
        clock(now)
        async with collect_jobs():
            sends = await report_service.queue_due(session)
        return [
            f"{send.property_id == campo.id and 'campo' or 'colinas'} {send.month}"
            for send in sends
        ]

    assert await sweep(noon(2026, 12, 1)) == []
    assert await sweep(noon(2026, 12, 2)) == ["campo 2026-11-01"]
    assert await sweep(noon(2026, 12, 9)) == []
    assert await sweep(noon(2026, 12, 25)) == ["colinas 2026-11-01"]
    assert await sweep(noon(2027, 1, 2)) == ["campo 2026-12-01"]


async def test_homeowners_read_their_own_history(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    owner = await lore(save_fixture, campo)
    await login(user)
    clock(noon(2026, 12, 9))
    await set_up(client, campo, (owner, "to"))
    await set_up(client, colinas, (user, "to"))
    await client.post(f"/v1/reports/properties/{campo.id}/send")
    other = (await client.post(f"/v1/reports/properties/{colinas.id}/send")).json()
    await login(owner)

    history = (await client.get("/v1/reports/sends/")).json()
    hidden = await client.get(f"/v1/reports/sends/{other['id']}/statement.pdf")

    assert [h["property_name"] for h in history] == ["Campo 9"]
    assert history[0]["has_statement"] is False
    assert hidden.status_code == 404
