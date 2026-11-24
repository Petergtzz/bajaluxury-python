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


async def test_nobody_changes_their_own_role(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.patch("/v1/users/me", json={"role": "homeowner"})

    assert response.status_code == 422
