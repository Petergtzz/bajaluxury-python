import pytest
from httpx import AsyncClient

from baja.models import Role, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_user,
)


@pytest.mark.parametrize("role", [Role.owner, Role.manager])
async def test_owners_and_managers_add_properties(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture, role: Role
) -> None:
    await login(await create_user(save_fixture, role))

    response = await client.post(
        "/v1/properties/",
        json={"name": " Campo 9 ", "address": "Campo 9, Todos Santos"},
    )

    assert response.status_code == 201
    body = response.json()
    assert (
        body["name"],
        body["address"],
        body["is_archived"],
        body["balance_methods"],
    ) == ("Campo 9", "Campo 9, Todos Santos", False, ["cash"])
    assert (await client.get(f"/v1/properties/{body['id']}")).json() == body


async def test_names_are_unique_ignoring_case(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Campo 9")
    await login(user)

    response = await client.post("/v1/properties/", json={"name": "CAMPO 9"})

    assert response.status_code == 409
    assert response.json() == {
        "error": "PropertyNameTaken",
        "detail": "Another property already has this name.",
    }


async def test_homeowners_cannot_add_properties(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    await login(await create_user(save_fixture, Role.homeowner))

    response = await client.post("/v1/properties/", json={"name": "Campo 9"})

    assert (response.status_code, response.json()["detail"]) == (
        403,
        "Only owners and managers can manage properties.",
    )


async def test_anonymous_callers_see_nothing(client: AsyncClient) -> None:
    assert (await client.get("/v1/properties/")).status_code == 401


async def test_owners_see_every_property_by_name(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    for name in ("Pescadero 7", "campo 9", "Colinas 21"):
        await create_property(save_fixture, name=name)
    await login(user)

    response = await client.get("/v1/properties/")

    assert [p["name"] for p in response.json()] == [
        "campo 9",
        "Colinas 21",
        "Pescadero 7",
    ]


async def test_homeowners_see_only_their_properties(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    listed = (await client.get("/v1/properties/")).json()
    other = await client.get(f"/v1/properties/{theirs.id}")

    assert [p["name"] for p in listed] == ["Campo 9"]
    assert other.status_code == 404


async def test_list_filters_archived(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Active")
    await create_property(save_fixture, name="Sold", is_archived=True)
    await login(user)

    active = await client.get("/v1/properties/", params={"is_archived": "false"})
    archived = await client.get("/v1/properties/", params={"is_archived": "true"})

    assert [p["name"] for p in active.json()] == ["Active"]
    assert [p["name"] for p in archived.json()] == ["Sold"]


async def test_update_renames_and_archives(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture, name="Campo 9")
    await login(user)

    recased = await client.patch(
        f"/v1/properties/{property.id}", json={"name": "CAMPO 9"}
    )
    archived = await client.patch(
        f"/v1/properties/{property.id}", json={"is_archived": True}
    )

    assert recased.json()["name"] == "CAMPO 9"
    assert (archived.json()["name"], archived.json()["is_archived"]) == (
        "CAMPO 9",
        True,
    )


async def test_renaming_to_a_taken_name_is_refused(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Campo 9")
    property = await create_property(save_fixture, name="Colinas 21")
    await login(user)

    response = await client.patch(
        f"/v1/properties/{property.id}", json={"name": "campo 9"}
    )

    assert response.status_code == 409


async def test_managers_set_which_methods_come_out_of_the_balance(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture, name="Soleil")
    await login(await create_user(save_fixture, Role.manager))

    response = await client.patch(
        f"/v1/properties/{property.id}",
        json={"balance_methods": ["debit card", "withdrawal", "debit card"]},
    )
    renamed = await client.patch(
        f"/v1/properties/{property.id}", json={"name": "Soleil 1"}
    )

    assert response.json()["balance_methods"] == ["debit card", "withdrawal"]
    assert renamed.json()["balance_methods"] == ["debit card", "withdrawal"]


async def test_balance_methods_must_be_payment_methods(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.post(
        "/v1/properties/", json={"name": "Campo 9", "balance_methods": ["gold"]}
    )

    assert response.status_code == 422
