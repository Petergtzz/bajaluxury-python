from typing import Any, ClassVar, Self

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

from baja.kit.db.models import RecordModel
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now


class RepositoryBase[M: RecordModel]:
    """Where a model's queries live. Rows that are soft deleted are never returned."""

    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncReadSession) -> None:
        self.session: _AsyncSession = session

    @classmethod
    def from_session(cls, session: AsyncReadSession | AsyncSession) -> Self:
        return cls(session)

    def get_base_statement(self) -> Select[M]:
        return select(self.model).where(self.model.deleted_at.is_(None))

    async def get_one_or_none(self, statement: Select[M]) -> M | None:
        result = await self.session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_all(self, statement: Select[M]) -> list[M]:
        result = await self.session.execute(statement)
        return list(result.unique().scalars().all())

    async def create(self, model: M, *, flush: bool = True) -> M:
        self.session.add(model)
        if flush:
            await self.session.flush()
        return model

    async def update(self, model: M, update_dict: dict[str, Any]) -> M:
        for key, value in update_dict.items():
            setattr(model, key, value)
        await self.session.flush()
        return model

    async def soft_delete(self, model: M) -> None:
        model.deleted_at = utc_now()
        await self.session.flush()
