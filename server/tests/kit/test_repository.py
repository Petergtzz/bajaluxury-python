from sqlalchemy import Select, func, select

from baja.kit.db.postgres import AsyncSession
from baja.kit.repository import RepositoryBase
from tests.widget import Widget


class WidgetRepository(RepositoryBase[Widget]):
    model = Widget


def named(name: str) -> Select[Widget]:
    return select(Widget).where(Widget.name == name)


async def count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Widget)) or 0


async def test_create_once_creates_a_missing_row(session: AsyncSession) -> None:
    widget, created = await WidgetRepository(session).create_once(
        Widget(name="a"), named("a")
    )

    assert (widget.name, created, await count(session)) == ("a", True, 1)


async def test_create_once_returns_the_existing_row(session: AsyncSession) -> None:
    repository = WidgetRepository(session)
    first, _ = await repository.create_once(Widget(name="a"), named("a"))

    second, created = await repository.create_once(Widget(name="a"), named("a"))

    assert (second.id, created, await count(session)) == (first.id, False, 1)


class RacedWidgetRepository(WidgetRepository):
    """Another request creates the row just after this one looked for it."""

    raced = False

    async def get_one_or_none(self, statement: Select[Widget]) -> Widget | None:
        if not self.raced:
            self.raced = True
            async with self.session.begin_nested():
                self.session.add(Widget(name="a"))
            return None
        return await super().get_one_or_none(statement)


async def test_create_once_returns_the_row_a_racing_request_created(
    session: AsyncSession,
) -> None:
    widget, created = await RacedWidgetRepository(session).create_once(
        Widget(name="a"), named("a")
    )

    assert (widget.name, created, await count(session)) == ("a", False, 1)
