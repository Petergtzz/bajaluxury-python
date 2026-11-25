from httpx import AsyncClient

from baja.models import Company, Role
from tests.fixtures import LoginFixture, SaveFixture, create_user


async def test_everyone_signed_in_reads_the_company(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    await login(await create_user(save_fixture, Role.homeowner))

    response = await client.get("/v1/company")

    assert response.json() == {
        "name": "Baja Luxury Management",
        "currency": "MXN",
        "timezone": "America/Mazatlan",
        "usd_exchange_rate": "16.5000",
    }


async def test_nobody_else(client: AsyncClient, company: Company) -> None:
    assert (await client.get("/v1/company")).status_code == 401


async def test_an_owner_changes_the_name_clock_and_rate(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    await login(await create_user(save_fixture, Role.owner))

    response = await client.patch(
        "/v1/company",
        json={
            "name": " Baja Luxury ",
            "timezone": "America/Tijuana",
            "usd_exchange_rate": "17.25",
        },
    )
    wrong = await client.patch("/v1/company", json={"timezone": "Baja/Nowhere"})
    currency = await client.patch("/v1/company", json={"currency": "USD"})

    assert response.json() == {
        "name": "Baja Luxury",
        "currency": "MXN",
        "timezone": "America/Tijuana",
        "usd_exchange_rate": "17.2500",
    }
    assert (wrong.status_code, currency.status_code) == (422, 422)


async def test_managers_read_the_company_but_dont_change_it(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    await login(await create_user(save_fixture, Role.manager))

    response = await client.patch("/v1/company", json={"usd_exchange_rate": "20"})

    assert response.status_code == 403
