from httpx import AsyncClient

from baja.kit.db.postgres import AsyncSession
from baja.models import Role, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_user,
)


async def test_owners_add_homeowners_to_their_properties(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await login(user)

    response = await client.post(
        "/v1/users/",
        json={
            "email": "lore@example.com",
            "name": " Lore ",
            "role": "homeowner",
            "property_ids": [str(campo.id)],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert {k: v for k, v in body.items() if k != "id"} == {
        "email": "lore@example.com",
        "name": "Lore",
        "role": "homeowner",
        "property_ids": [str(campo.id)],
    }
    listed = (await client.get("/v1/users/")).json()
    assert [u["email"] for u in listed] == [user.email, "lore@example.com"]


async def test_a_new_user_can_ask_for_a_login_code(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    sent_jobs: list[tuple[str, tuple[object, ...]]],
) -> None:
    await login(user)
    await client.post(
        "/v1/users/", json={"email": "manager@example.com", "role": "manager"}
    )

    await client.post(
        "/v1/auth/login-code/request", json={"email": "manager@example.com"}
    )

    assert [(name, args[0]) for name, args in sent_jobs] == [
        ("email.send_login_code", "manager@example.com")
    ]


async def test_emails_are_unique_ignoring_case(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.post(
        "/v1/users/", json={"email": user.email.upper(), "role": "manager"}
    )

    assert (response.status_code, response.json()["error"]) == (409, "EmailTaken")


async def test_only_homeowners_get_properties(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    response = await client.post(
        "/v1/users/",
        json={
            "email": "m@example.com",
            "role": "manager",
            "property_ids": [str(campo.id)],
        },
    )

    assert (response.status_code, response.json()["error"]) == (
        422,
        "InvalidAssignment",
    )


async def test_unknown_properties_are_refused(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.post(
        "/v1/users/",
        json={
            "email": "h@example.com",
            "role": "homeowner",
            "property_ids": ["01a09900-0000-7000-8000-000000000000"],
        },
    )

    assert response.status_code == 422


async def test_managers_see_users_but_only_owners_change_them(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    await login(await create_user(save_fixture, Role.manager))

    listed = await client.get("/v1/users/")
    created = await client.post(
        "/v1/users/", json={"email": "x@example.com", "role": "manager"}
    )

    assert listed.status_code == 200
    assert (created.status_code, created.json()["detail"]) == (
        403,
        "Only an owner can manage users.",
    )


async def test_homeowners_cannot_see_users(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    await login(await create_user(save_fixture, Role.homeowner))

    assert (await client.get("/v1/users/")).status_code == 403


async def test_assignments_are_replaced_and_dropped_with_the_role(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, campo)
    await login(user)

    moved = await client.patch(
        f"/v1/users/{homeowner.id}", json={"property_ids": [str(colinas.id)]}
    )
    promoted = await client.patch(f"/v1/users/{homeowner.id}", json={"role": "manager"})

    assert moved.json()["property_ids"] == [str(colinas.id)]
    assert (promoted.json()["role"], promoted.json()["property_ids"]) == (
        "manager",
        [],
    )


async def test_owners_cannot_change_their_own_role(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.patch(f"/v1/users/{user.id}", json={"role": "manager"})

    assert (response.status_code, response.json()["error"]) == (
        409,
        "CannotChangeYourself",
    )


async def test_a_changed_email_must_be_verified_again(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    session: AsyncSession,
) -> None:
    manager = await create_user(save_fixture, Role.manager)
    await login(user)

    response = await client.patch(
        f"/v1/users/{manager.id}", json={"email": "new@example.com"}
    )

    assert response.json()["email"] == "new@example.com"
    await session.refresh(manager)
    assert manager.email_verified is False


async def test_a_deleted_user_is_logged_out_and_gone(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    manager = await create_user(save_fixture, Role.manager)
    await login(manager)
    assert (await client.get("/v1/users/me")).status_code == 200
    await login(user)

    response = await client.delete(f"/v1/users/{manager.id}")

    assert response.status_code == 204
    assert [u["email"] for u in (await client.get("/v1/users/")).json()] == [user.email]
    assert (await client.patch(f"/v1/users/{manager.id}", json={})).status_code == 404


async def test_owners_cannot_delete_themselves(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    assert (await client.delete(f"/v1/users/{user.id}")).status_code == 409
