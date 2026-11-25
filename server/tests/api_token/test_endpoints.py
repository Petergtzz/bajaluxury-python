from httpx import AsyncClient

from baja.models import Role, User
from tests.fixtures import LoginFixture, SaveFixture, create_user


async def test_a_manager_connects_their_own_devices(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    luis = await create_user(save_fixture, Role.manager, email="luis@example.com")
    await login(luis)

    created = await client.post("/v1/api-tokens/", json={"label": " Luis's iPhone "})
    token = created.json()["token"]
    listed = (await client.get("/v1/api-tokens/")).json()
    # The token itself works, as Luis, and is never shown again.
    client.cookies.clear()
    me = await client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert created.status_code == 201
    assert (created.json()["label"], created.json()["user"]["email"]) == (
        "Luis's iPhone",
        "luis@example.com",
    )
    assert [(t["label"], "token" in t) for t in listed] == [("Luis's iPhone", False)]
    assert me.json()["email"] == "luis@example.com"


async def test_an_owner_sees_and_revokes_everyones(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    luis = await create_user(save_fixture, Role.manager, email="luis@example.com")
    await login(luis)
    luis_phone = (await client.post("/v1/api-tokens/", json={"label": "iPhone"})).json()
    await login(user)
    await client.post("/v1/api-tokens/", json={"label": "iPad"})

    everyone = (await client.get("/v1/api-tokens/")).json()
    revoked = await client.delete(f"/v1/api-tokens/{luis_phone['id']}")
    client.cookies.clear()
    after = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {luis_phone['token']}"}
    )

    assert sorted(t["label"] for t in everyone) == ["iPad", "iPhone"]
    assert revoked.status_code == 204
    assert after.status_code == 401


async def test_a_manager_cant_touch_anyone_elses(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await login(user)
    owners = (await client.post("/v1/api-tokens/", json={"label": "iPad"})).json()
    await login(await create_user(save_fixture, Role.manager))

    listed = (await client.get("/v1/api-tokens/")).json()
    revoked = await client.delete(f"/v1/api-tokens/{owners['id']}")

    assert (listed, revoked.status_code) == ([], 404)


async def test_a_device_mints_no_tokens_and_homeowners_none_at_all(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await login(user)
    token = (await client.post("/v1/api-tokens/", json={"label": "iPad"})).json()[
        "token"
    ]

    client.cookies.clear()
    by_device = await client.post(
        "/v1/api-tokens/",
        json={"label": "Another"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await login(await create_user(save_fixture, Role.homeowner))
    homeowner = await client.get("/v1/api-tokens/")

    assert (by_device.status_code, homeowner.status_code) == (403, 403)
