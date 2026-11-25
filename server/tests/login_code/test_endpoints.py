from datetime import timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from baja.config import settings
from baja.kit.crypto import unseal
from baja.kit.db.postgres import AsyncSession
from baja.kit.utils import utc_now
from baja.models import LoginCode, User, UserSession

type SentJobs = list[tuple[str, tuple[Any, ...]]]


async def request_code(client: AsyncClient, email: str) -> None:
    response = await client.post("/v1/auth/login-code/request", json={"email": email})
    assert response.status_code == 202


def code_from(sent_jobs: SentJobs) -> str:
    [(actor_name, (_, sealed))] = sent_jobs
    assert actor_name == "email.send_login_code"
    return unseal(
        sealed,
        secret=settings.SECRET,
        purpose="login-code",
        max_age=settings.LOGIN_CODE_TTL,
    )


async def test_a_user_gets_a_code_by_email(
    client: AsyncClient, user: User, session: AsyncSession, sent_jobs: SentJobs
) -> None:
    await request_code(client, " OWNER@bajaluxurymgmt.com ")

    code = code_from(sent_jobs)
    assert len(code) == settings.LOGIN_CODE_LENGTH
    assert code.isdigit()
    assert sent_jobs[0][1][0] == user.email
    stored = (await session.execute(select(LoginCode))).scalars().all()
    assert [row.email for row in stored] == [user.email]
    assert stored[0].code_hash != code


async def test_an_unknown_address_is_answered_the_same_without_an_email(
    client: AsyncClient, session: AsyncSession, sent_jobs: SentJobs
) -> None:
    await request_code(client, "stranger@example.com")

    assert sent_jobs == []
    assert (await session.execute(select(LoginCode))).scalars().all() == []


async def test_asking_again_replaces_the_previous_code(
    client: AsyncClient, user: User, session: AsyncSession, sent_jobs: SentJobs
) -> None:
    await request_code(client, user.email)
    await request_code(client, user.email)

    assert len((await session.execute(select(LoginCode))).scalars().all()) == 1


async def test_requests_per_address_are_limited(
    client: AsyncClient, user: User
) -> None:
    for _ in range(settings.LOGIN_CODE_MAX_REQUESTS_PER_WINDOW):
        await request_code(client, user.email)

    response = await client.post(
        "/v1/auth/login-code/request", json={"email": user.email}
    )

    assert response.status_code == 429
    assert response.json()["error"] == "TooManyRequests"
    assert int(response.headers["Retry-After"]) > 0


async def test_the_right_code_logs_in_once(
    client: AsyncClient, user: User, session: AsyncSession, sent_jobs: SentJobs
) -> None:
    await request_code(client, user.email)
    payload = {"email": user.email, "code": code_from(sent_jobs)}

    response = await client.post("/v1/auth/login-code/authenticate", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": user.email,
        "name": "Pedro Gutierrez",
        "role": "owner",
        "display_currency": None,
    }
    assert response.cookies.get(settings.USER_SESSION_COOKIE_KEY)
    sessions = (await session.execute(select(UserSession))).scalars().all()
    assert [s.user_id for s in sessions] == [user.id]
    again = await client.post("/v1/auth/login-code/authenticate", json=payload)
    assert again.status_code == 401


async def test_a_wrong_code_is_refused(
    client: AsyncClient, user: User, sent_jobs: SentJobs
) -> None:
    await request_code(client, user.email)
    wrong = "000000" if code_from(sent_jobs) != "000000" else "111111"

    response = await client.post(
        "/v1/auth/login-code/authenticate", json={"email": user.email, "code": wrong}
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": "LoginCodeInvalidOrExpired",
        "detail": "This login code is invalid or has expired.",
    }


async def test_an_expired_code_is_refused(
    client: AsyncClient, user: User, session: AsyncSession, sent_jobs: SentJobs
) -> None:
    await request_code(client, user.email)
    code = code_from(sent_jobs)
    login_code = (await session.execute(select(LoginCode))).scalar_one()
    login_code.expires_at = utc_now() - timedelta(seconds=1)
    await session.flush()

    response = await client.post(
        "/v1/auth/login-code/authenticate", json={"email": user.email, "code": code}
    )

    assert response.status_code == 401


async def test_guesses_are_limited_even_before_the_right_code(
    client: AsyncClient, user: User, sent_jobs: SentJobs
) -> None:
    await request_code(client, user.email)
    code = code_from(sent_jobs)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.LOGIN_CODE_MAX_ATTEMPTS_PER_WINDOW):
        await client.post(
            "/v1/auth/login-code/authenticate",
            json={"email": user.email, "code": wrong},
        )

    response = await client.post(
        "/v1/auth/login-code/authenticate", json={"email": user.email, "code": code}
    )

    assert response.status_code == 429
