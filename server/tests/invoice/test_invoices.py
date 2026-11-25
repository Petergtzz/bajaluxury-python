import io
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from baja.invoice import tasks
from baja.models import Company, Property, Role, User
from tests.email.test_tasks import RecordingSender
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    create_guest_expense,
    create_property,
    create_user,
)


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    sender = RecordingSender()
    monkeypatch.setattr(tasks, "get_email_sender", lambda: sender)
    return sender


def invoice(property: Property, **changes: Any) -> dict[str, Any]:
    return {
        "property_id": str(property.id),
        "recipient_name": "Ana Guest",
        "email": "ana@example.com",
        "issued_on": "2026-11-25",
        "due_on": "2026-12-10",
        "lines": [
            {"description": "Airport pickup", "unit_price": "1500"},
            {"description": "Groceries", "quantity": "2", "unit_price": "333.33"},
        ],
        **changes,
    }


async def test_an_invoice_adds_up_and_takes_the_next_number(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    first = await client.post("/v1/invoices/", json=invoice(campo))
    second = await client.post(
        "/v1/invoices/", json=invoice(campo, tax_rate="0", exchange_rate="18.25")
    )
    next_year = await client.post(
        "/v1/invoices/",
        json=invoice(campo, issued_on="2027-01-02", due_on="2027-01-02"),
    )

    assert first.status_code == 201, first.text
    body = first.json()
    assert [(line["position"], line["amount"]) for line in body["lines"]] == [
        (1, 1500.0),
        (2, 666.66),
    ]
    assert (body["subtotal"], body["tax"], body["total"]) == (2166.66, 346.67, 2513.33)
    assert (body["tax_rate"], body["exchange_rate"]) == ("0.1600", "16.5000")
    assert (body["created_by_id"], body["sent_at"]) == (str(user.id), None)
    assert [r.json()["number"] for r in (first, second, next_year)] == [
        "INV-2026-001",
        "INV-2026-002",
        "INV-2027-001",
    ]
    assert (second.json()["total"], second.json()["exchange_rate"]) == (
        2166.66,
        "18.2500",
    )


async def test_a_deleted_invoices_number_is_not_given_again(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)
    first = (await client.post("/v1/invoices/", json=invoice(campo))).json()

    deleted = await client.delete(f"/v1/invoices/{first['id']}")
    after = (await client.post("/v1/invoices/", json=invoice(campo))).json()

    assert deleted.status_code == 204
    assert (await client.get(f"/v1/invoices/{first['id']}")).status_code == 404
    assert after["number"] == "INV-2026-002"


async def test_guest_expenses_are_billed_once(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    pickup = await create_guest_expense(save_fixture, campo, amount="456.50")
    other = await create_guest_expense(save_fixture, campo, concept="groceries")
    await login(user)
    line = {"description": "Airport pickup", "unit_price": "456.50"}

    billed = await client.post(
        "/v1/invoices/",
        json=invoice(campo, lines=[{**line, "guest_expense_id": str(pickup.id)}]),
    )
    twice = await client.post(
        "/v1/invoices/",
        json=invoice(campo, lines=[{**line, "guest_expense_id": str(pickup.id)}]),
    )
    open_ = await client.get("/v1/guest-expenses/", params={"invoiced": "false"})
    shown = await client.get(f"/v1/guest-expenses/{pickup.id}")
    await client.delete(f"/v1/invoices/{billed.json()['id']}")
    freed = await client.get(f"/v1/guest-expenses/{pickup.id}")

    assert billed.json()["lines"][0]["guest_expense_id"] == str(pickup.id)
    assert (twice.status_code, twice.json()["detail"]) == (
        409,
        "A guest expense on it is already billed by INV-2026-001.",
    )
    assert [g["id"] for g in open_.json()["items"]] == [str(other.id)]
    assert shown.json()["invoice_id"] == billed.json()["id"]
    assert freed.json()["invoice_id"] is None


@pytest.mark.parametrize("case", ["twice", "elsewhere", "made up"])
async def test_lines_bill_this_propertys_guest_expenses(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    case: str,
) -> None:
    campo = await create_property(save_fixture)
    colinas = await create_property(save_fixture, name="Colinas 21")
    ours = await create_guest_expense(save_fixture, campo)
    theirs = await create_guest_expense(save_fixture, colinas)
    await login(user)
    ids: list[str] = {
        "twice": [str(ours.id), str(ours.id)],
        "elsewhere": [str(theirs.id)],
        "made up": ["0190d7f2-0000-7000-8000-000000000000"],
    }[case]

    response = await client.post(
        "/v1/invoices/",
        json=invoice(
            campo,
            lines=[
                {"description": "x", "unit_price": "1", "guest_expense_id": id}
                for id in ids
            ],
        ),
    )

    assert (response.status_code, response.json()["error"]) == (
        422,
        "InvoiceLinesInvalid",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"lines": []},
        {"due_on": "2026-11-24"},
        {"tax_rate": "1.5"},
        {"lines": [{"description": "x", "quantity": "0", "unit_price": "1"}]},
        {"email": "not an email"},
    ],
)
async def test_what_an_invoice_must_be(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    changes: dict[str, Any],
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    response = await client.post("/v1/invoices/", json=invoice(campo, **changes))

    assert response.status_code == 422


async def test_issuing_sends_it_with_its_pdf_once(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    sent_jobs: list[tuple[str, tuple[Any, ...]]],
    worker_resources: None,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await create_user(save_fixture, Role.owner, email="boss@example.com")
    await login(user)
    issued = (
        await client.post(
            "/v1/invoices/",
            json=invoice(campo, payment_details="CLABE 0123", notes="Thanks!"),
        )
    ).json()

    assert sent_jobs == [("invoice.send", (issued["id"],))]
    await tasks.send_invoice(issued["id"])
    await tasks.send_invoice(issued["id"])

    [email] = sender.sent
    assert email.to == ("ana@example.com",)
    assert set(email.bcc) == {user.email, "boss@example.com"}
    assert email.subject == "Invoice INV-2026-001 · Campo 9"
    assert "2,513.33 MXN, due Dec 10, 2026" in email.text
    [attachment] = email.attachments
    assert attachment.filename == "INV-2026-001.pdf"
    text = PdfReader(io.BytesIO(attachment.content)).pages[0].extract_text()
    for expected in (
        "INV-2026-001",
        "Ana Guest",
        "Campo 9",
        "Issued Nov 25, 2026",
        "Due Dec 10, 2026",
        "666.66",
        "VAT (16%)",
        "2,513.33",
        "152.32",  # the total in dollars, at 16.5
        "CLABE 0123",
        "Thanks!",
    ):
        assert expected in text
    sent = (await client.get(f"/v1/invoices/{issued['id']}")).json()
    assert sent["sent_at"] is not None


async def test_the_pdf_can_be_had_again(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)
    issued = (await client.post("/v1/invoices/", json=invoice(campo))).json()

    response = await client.get(f"/v1/invoices/{issued['id']}.pdf")
    listed = await client.get("/v1/invoices/", params={"property_id": str(campo.id)})

    assert response.headers["content-disposition"] == (
        'attachment; filename="INV-2026-001.pdf"'
    )
    assert (
        "Airport pickup"
        in PdfReader(io.BytesIO(response.content)).pages[0].extract_text()
    )
    assert [i["number"] for i in listed.json()] == ["INV-2026-001"]


async def test_homeowners_have_no_invoices(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    await login(await create_user(save_fixture, Role.homeowner))

    assert (await client.get("/v1/invoices/")).status_code == 403
