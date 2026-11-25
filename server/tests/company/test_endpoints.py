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
