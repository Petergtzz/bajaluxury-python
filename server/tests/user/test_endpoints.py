from httpx import AsyncClient

from baja.models import User
from tests.fixtures import LoginFixture


async def test_people_rename_themselves(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.patch("/v1/users/me", json={"name": "  Pedro G.  "})

    assert response.status_code == 200
    assert response.json()["name"] == "Pedro G."
    assert (await client.get("/v1/users/me")).json()["name"] == "Pedro G."


async def test_people_choose_the_currency_they_read(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)
    before = (await client.get("/v1/users/me")).json()["display_currency"]

    chosen = await client.patch("/v1/users/me", json={"display_currency": "USD"})
    renamed = await client.patch("/v1/users/me", json={"name": "Pedro"})
    reset = await client.patch("/v1/users/me", json={"display_currency": None})
    unknown = await client.patch("/v1/users/me", json={"display_currency": "EUR"})

    assert before is None
    assert chosen.json()["display_currency"] == "USD"
    assert renamed.json()["display_currency"] == "USD"
    assert reset.json()["display_currency"] is None
    assert unknown.status_code == 422


async def test_nobody_changes_their_own_role(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.patch("/v1/users/me", json={"role": "homeowner"})

    assert response.status_code == 422
