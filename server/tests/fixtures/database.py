import asyncio
import pathlib
from collections.abc import AsyncIterator, Callable, Coroutine

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from baja.config import settings
from baja.kit.db.models import Model
from baja.kit.db.postgres import (
    AsyncSession,
    AsyncSessionMaker,
    create_async_engine,
    create_async_sessionmaker,
)
from tests.widget import Widget

ALEMBIC_CONFIG_FILE = pathlib.Path(__file__).parents[2] / "alembic.ini"
TEST_ONLY_TABLES = [Model.metadata.tables[Widget.__tablename__]]


def get_database_name(worker_id: str) -> str:
    return f"{settings.POSTGRES_DATABASE}_{worker_id}"


async def execute_on_server(*statements: str) -> None:
    engine = create_async_engine(
        dsn=settings.get_postgres_dsn("postgres"), application_name="testing.setup"
    )
    async with engine.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


def apply_migrations(dsn: str) -> None:
    config = Config(ALEMBIC_CONFIG_FILE)
    config.attributes["sqlalchemy.url"] = dsn
    command.upgrade(config, "head")


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def initialize_test_database(worker_id: str) -> AsyncIterator[None]:
    """A fresh database per pytest worker, built by the real migrations."""
    name = get_database_name(worker_id)
    dsn = settings.get_postgres_dsn(name)
    await execute_on_server(
        f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)',
        f'CREATE DATABASE "{name}" TEMPLATE template0',
    )
    await asyncio.to_thread(apply_migrations, dsn)
    engine = create_async_engine(dsn=dsn, application_name="testing.setup")
    async with engine.begin() as connection:
        await connection.run_sync(Model.metadata.create_all, tables=TEST_ONLY_TABLES)
    await engine.dispose()
    yield
    await execute_on_server(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
async def connection(worker_id: str) -> AsyncIterator[AsyncConnection]:
    """One transaction per test, rolled back at the end: tests never see each other."""
    engine = create_async_engine(
        dsn=settings.get_postgres_dsn(get_database_name(worker_id)),
        application_name=f"testing.{worker_id}",
    )
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


def app_sessions(connection: AsyncConnection) -> AsyncSessionMaker:
    """Sessions for the app's requests, as savepoints inside the test's transaction."""
    return create_async_sessionmaker(
        connection, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    async with app_sessions(connection)() as session:
        yield session


type SaveFixture = Callable[[Model], Coroutine[None, None, None]]


@pytest.fixture
def save_fixture(session: AsyncSession) -> SaveFixture:
    async def _save_fixture(model: Model) -> None:
        session.add(model)
        await session.flush()

    return _save_fixture
