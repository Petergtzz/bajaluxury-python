import datetime as dt
from collections.abc import Callable
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

import baja.company.service
from baja.kit.db.postgres import AsyncSession
from baja.models import (
    Company,
    PaymentMethod,
    Property,
    RecurringCharge,
    Role,
    Transaction,
    User,
)
from baja.recurring.service import recurring_charge as recurring_charge_service
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_user,
)

type Clock = Callable[[dt.datetime], None]


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    def set_now(now: dt.datetime) -> None:
        monkeypatch.setattr(baja.company.service, "utc_now", lambda: now)

    return set_now


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.UTC)


async def create_charge(
    save_fixture: SaveFixture,
    property: Property,
    *,
    day_of_month: int = 10,
    charged_through: dt.date = dt.date(2026, 11, 9),
    amount: str = "8500",
    payment_method: PaymentMethod = PaymentMethod.cash,
) -> RecurringCharge:
    charge = RecurringCharge(
        property_id=property.id,
        amount=Decimal(amount),
        payment_method=payment_method,
        category="staff",
        concept="property management",
        description="monthly property management fee",
        day_of_month=day_of_month,
        charged_through=charged_through,
    )
    await save_fixture(charge)
    return charge


async def charged(session: AsyncSession) -> list[tuple[str, dt.date, Decimal]]:
    rows = await session.execute(
        select(Property.name, Transaction.date, Transaction.amount)
        .join(Property, Property.id == Transaction.property_id)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Property.name, Transaction.date)
    )
    return [tuple(row) for row in rows]  # type: ignore[misc]


async def test_charges_what_fell_due_once(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    charge = await create_charge(save_fixture, campo)
    clock(utc(2026, 11, 10, 7, 5))

    first = await recurring_charge_service.charge_due(session)
    second = await recurring_charge_service.charge_due(session)

    assert (first, second) == (1, 0)
    [transaction] = (await session.execute(select(Transaction))).scalars()
    assert (
        transaction.date,
        transaction.amount,
        transaction.concept,
        transaction.source,
        transaction.external_id,
        transaction.affects_balance,
        transaction.entered_by_id,
    ) == (
        dt.date(2026, 11, 10),
        Decimal("8500.00"),
        "property management",
        "recurring",
        f"{charge.id}:2026-11",
        True,
        None,
    )
    assert charge.charged_through == dt.date(2026, 11, 10)


async def test_the_day_starts_where_the_company_is(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    campo = await create_property(save_fixture)
    await create_charge(save_fixture, campo)
    clock(utc(2026, 11, 10, 6, 59))  # still the 9th in Mazatlan

    assert await recurring_charge_service.charge_due(session) == 0


async def test_a_missed_month_is_caught_up(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await create_charge(save_fixture, campo, day_of_month=31)
    clock(utc(2027, 1, 2, 12))

    await recurring_charge_service.charge_due(session)

    assert [date for _, date, _ in await charged(session)] == [
        dt.date(2026, 11, 30),
        dt.date(2026, 12, 31),
    ]


async def test_a_month_is_charged_once_even_if_the_cursor_goes_back(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    campo = await create_property(save_fixture)
    charge = await create_charge(save_fixture, campo)
    clock(utc(2026, 11, 20, 12))
    await recurring_charge_service.charge_due(session)
    charge.charged_through = dt.date(2026, 11, 1)
    charge.day_of_month = 15

    assert await recurring_charge_service.charge_due(session) == 0


async def test_archived_properties_are_skipped_for_good(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    sold = await create_property(save_fixture, is_archived=True)
    charge = await create_charge(save_fixture, sold)
    clock(utc(2026, 12, 20, 12))
    await recurring_charge_service.charge_due(session)
    sold.is_archived = False

    await recurring_charge_service.charge_due(session)

    assert await charged(session) == []
    assert charge.charged_through == dt.date(2026, 12, 20)


async def test_deleted_charges_stop(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    campo = await create_property(save_fixture)
    charge = await create_charge(save_fixture, campo)
    charge.deleted_at = utc(2026, 11, 1)
    clock(utc(2026, 12, 20, 12))

    assert await recurring_charge_service.charge_due(session) == 0


async def test_card_charges_leave_the_balance_alone(
    session: AsyncSession, save_fixture: SaveFixture, company: Company, clock: Clock
) -> None:
    colinas = await create_property(save_fixture, name="Colinas 21")
    await create_charge(
        save_fixture,
        colinas,
        amount="1305",
        payment_method=PaymentMethod.credit_card,
    )
    clock(utc(2026, 11, 10, 12))

    await recurring_charge_service.charge_due(session)

    [transaction] = (await session.execute(select(Transaction))).scalars()
    assert transaction.affects_balance is False


async def test_without_a_company_nothing_is_charged(session: AsyncSession) -> None:
    with pytest.raises(baja.company.service.CompanyNotSetUp):
        await recurring_charge_service.charge_due(session)


ENTRY = {
    "amount": "8500",
    "payment_method": "cash",
    "category": "staff",
    "concept": "property management",
    "description": "monthly property management fee",
    "day_of_month": 10,
}


@pytest.mark.parametrize("role", [Role.owner, Role.manager])
async def test_managers_set_up_charges_starting_today(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
    role: Role,
) -> None:
    campo = await create_property(save_fixture)
    await login(await create_user(save_fixture, role))
    clock(utc(2026, 11, 25, 12))

    response = await client.post(
        "/v1/recurring-charges/", json={**ENTRY, "property_id": str(campo.id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["amount"], body["day_of_month"], body["next_charge_on"]) == (
        8500.0,
        10,
        "2026-12-10",
    )
    assert (await client.get(f"/v1/recurring-charges/{body['id']}")).json() == body


async def test_a_charge_due_today_is_charged_today(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await login(user)
    clock(utc(2026, 11, 25, 12))

    response = await client.post(
        "/v1/recurring-charges/",
        json={**ENTRY, "property_id": str(campo.id), "day_of_month": 25},
    )
    await recurring_charge_service.charge_due(session)

    assert response.json()["next_charge_on"] == "2026-11-25"
    assert [date for _, date, _ in await charged(session)] == [dt.date(2026, 11, 25)]


async def test_starts_on_delays_the_first_charge(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)
    clock(utc(2026, 11, 25, 12))

    response = await client.post(
        "/v1/recurring-charges/",
        json={**ENTRY, "property_id": str(campo.id), "starts_on": "2027-01-01"},
    )

    assert response.json()["next_charge_on"] == "2027-01-10"


async def test_changes_apply_from_the_next_charge(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    session: AsyncSession,
    save_fixture: SaveFixture,
    company: Company,
    clock: Clock,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    charge = await create_charge(save_fixture, campo)
    clock(utc(2026, 11, 20, 12))
    await recurring_charge_service.charge_due(session)
    await login(user)

    response = await client.patch(
        f"/v1/recurring-charges/{charge.id}",
        json={"amount": "9000", "day_of_month": 31, "description": None},
    )
    clock(utc(2026, 12, 31, 12))
    await session.refresh(charge)
    await recurring_charge_service.charge_due(session)

    assert response.json()["next_charge_on"] == "2026-11-30"
    assert [(date, amount) for _, date, amount in await charged(session)] == [
        (dt.date(2026, 11, 10), Decimal("8500.00")),
        (dt.date(2026, 12, 31), Decimal("9000.00")),
    ]


async def test_list_and_delete(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    colinas = await create_property(save_fixture, name="Colinas 21")
    campo = await create_property(save_fixture, name="Campo 9")
    late = await create_charge(save_fixture, campo, day_of_month=31)
    early = await create_charge(save_fixture, campo, day_of_month=1)
    other = await create_charge(save_fixture, colinas)
    await login(user)

    listed = await client.get("/v1/recurring-charges/")
    deleted = await client.delete(f"/v1/recurring-charges/{early.id}")
    after = await client.get(
        "/v1/recurring-charges/", params={"property_id": str(campo.id)}
    )

    assert [c["id"] for c in listed.json()] == [
        str(early.id),
        str(late.id),
        str(other.id),
    ]
    assert deleted.status_code == 204
    assert [c["id"] for c in after.json()] == [str(late.id)]


async def test_archived_properties_take_no_new_charges(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    sold = await create_property(save_fixture, is_archived=True)
    await login(user)

    response = await client.post(
        "/v1/recurring-charges/", json={**ENTRY, "property_id": str(sold.id)}
    )

    assert response.status_code == 409


async def test_homeowners_cannot_see_or_set_charges(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, campo)
    await login(homeowner)

    listed = await client.get("/v1/recurring-charges/")
    created = await client.post(
        "/v1/recurring-charges/", json={**ENTRY, "property_id": str(campo.id)}
    )

    assert (listed.status_code, created.status_code) == (403, 403)


@pytest.mark.parametrize("day", [0, 32])
async def test_days_are_days_of_a_month(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    day: int,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    response = await client.post(
        "/v1/recurring-charges/",
        json={**ENTRY, "property_id": str(campo.id), "day_of_month": day},
    )

    assert response.status_code == 422
