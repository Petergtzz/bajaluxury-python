from collections.abc import Awaitable, Callable
from decimal import Decimal

import pytest
from httpx import AsyncClient

from baja.auth.service import auth as auth_service
from baja.config import settings
from baja.kit.db.postgres import AsyncSession
from baja.models import Company, Currency, Role, User
from tests.fixtures.database import SaveFixture

type LoginFixture = Callable[[User], Awaitable[str]]


async def create_company(
    save_fixture: SaveFixture,
    *,
    name: str = "Baja Luxury Management",
    currency: Currency = Currency.MXN,
    timezone: str = "America/Mazatlan",
    usd_exchange_rate: Decimal = Decimal("16.5"),
) -> Company:
    company = Company(
        name=name,
        currency=currency,
        timezone=timezone,
        usd_exchange_rate=usd_exchange_rate,
    )
    await save_fixture(company)
    return company


async def create_user(
    save_fixture: SaveFixture,
    role: Role = Role.owner,
    *,
    email: str | None = None,
    name: str | None = None,
) -> User:
    user = User(
        email=email or f"{role.value}@bajaluxurymgmt.com",
        name=name,
        role=role,
        email_verified=True,
    )
    await save_fixture(user)
    return user


@pytest.fixture
async def company(save_fixture: SaveFixture) -> Company:
    return await create_company(save_fixture)


@pytest.fixture
async def user(save_fixture: SaveFixture) -> User:
    """An owner: the role that may do everything."""
    return await create_user(save_fixture, Role.owner, name="Pedro Gutierrez")


@pytest.fixture
def login(client: AsyncClient, session: AsyncSession) -> LoginFixture:
    async def _login(user: User) -> str:
        token, _ = await auth_service.create_user_session(
            session, user, user_agent="pytest"
        )
        client.cookies.set(settings.USER_SESSION_COOKIE_KEY, token)
        return token

    return _login
