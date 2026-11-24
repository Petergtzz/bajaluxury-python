from httpx import AsyncClient

from baja.config import settings
from baja.kit.db.postgres import AsyncSession
from baja.kit.utils import utc_now
from baja.models import User
from tests.fixtures import LoginFixture


async def test_anonymous_callers_are_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/v1/users/me")

    assert (response.status_code, response.json()["error"]) == (401, "Unauthorized")


async def test_a_session_cookie_identifies_the_user(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.get("/v1/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == user.email


async def test_an_unknown_cookie_is_anonymous(client: AsyncClient) -> None:
    client.cookies.set(settings.USER_SESSION_COOKIE_KEY, "bl_us_made-up")

    assert (await client.get("/v1/users/me")).status_code == 401


async def test_a_deleted_user_is_logged_out(
    client: AsyncClient, login: LoginFixture, user: User, session: AsyncSession
) -> None:
    await login(user)
    user.deleted_at = utc_now()
    await session.flush()

    assert (await client.get("/v1/users/me")).status_code == 401


async def test_logout_ends_the_session(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    token = await login(user)

    response = await client.post("/v1/auth/logout")

    assert response.status_code == 204
    assert 'baja_session=""' in response.headers["set-cookie"]
    client.cookies.set(settings.USER_SESSION_COOKIE_KEY, token)
    assert (await client.get("/v1/users/me")).status_code == 401
