from httpx import AsyncClient

from baja.auth.service import auth as auth_service
from baja.kit.db.postgres import AsyncSession
from baja.models import Role, User
from scripts.api_tokens import run
from tests.fixtures import LoginFixture, SaveFixture, create_user


async def test_a_bearer_token_identifies_its_user(
    client: AsyncClient, session: AsyncSession, user: User
) -> None:
    token, api_token = await auth_service.issue_api_token(
        session, user, label="Lore's iPhone"
    )

    response = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {token}\n"}
    )

    assert response.json()["email"] == user.email
    assert token.startswith("bl_at_")
    assert api_token.token != token
    await session.refresh(api_token)
    assert api_token.last_used_at is not None


async def test_a_token_carries_its_users_role(
    client: AsyncClient, session: AsyncSession, save_fixture: SaveFixture
) -> None:
    homeowner = await create_user(save_fixture, Role.homeowner)
    token, _ = await auth_service.issue_api_token(session, homeowner, label="iPad")

    response = await client.get(
        "/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


async def test_revoked_and_unknown_tokens_are_anonymous(
    client: AsyncClient, session: AsyncSession, user: User
) -> None:
    token, api_token = await auth_service.issue_api_token(session, user, label="old")
    await auth_service.revoke_api_token(session, api_token)

    revoked = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    unknown = await client.get(
        "/v1/users/me", headers={"Authorization": "Bearer bl_at_made-up"}
    )

    assert (revoked.status_code, unknown.status_code) == (401, 401)


async def test_a_wrong_token_does_not_fall_back_to_the_cookie(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.get(
        "/v1/users/me", headers={"Authorization": "Bearer bl_at_made-up"}
    )

    assert response.status_code == 401


async def test_the_script_issues_lists_and_revokes(
    client: AsyncClient, session: AsyncSession, user: User
) -> None:
    issued = await run(session, ["issue", user.email.upper(), "Lore's iPhone"])
    assert issued is not None
    token = issued.splitlines()[-1]
    token_id = issued.split()[1]

    listed = await run(session, ["list"])
    revoked = await run(session, ["revoke", token_id])
    response = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert listed is not None
    assert "Lore's iPhone" in listed
    assert "never" in listed
    assert revoked == f'Revoked {token_id}, "Lore\'s iPhone".'
    assert response.status_code == 401
    assert await run(session, ["revoke", "nope"]) == (
        "'nope' is not a token id: see `list`."
    )
    assert await run(session, ["issue", "nobody@example.com", "x"]) == (
        "No user with the email nobody@example.com."
    )
    assert await run(session, ["bogus"]) is None
