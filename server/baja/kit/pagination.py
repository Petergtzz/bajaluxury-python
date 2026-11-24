import math
from collections.abc import Sequence
from typing import Annotated, Any, NamedTuple, Self

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, literal, select

from baja.kit.db.postgres import AsyncReadSession

MAX_LIMIT = 100


class PaginationParams(NamedTuple):
    page: int
    limit: int


async def paginate[M](
    session: AsyncReadSession,
    statement: Select[M],
    *,
    pagination: PaginationParams,
) -> tuple[Sequence[M], int]:
    """One page of the statement's rows, and how many rows there are in all."""
    page, limit = pagination
    count = await session.scalar(
        select(func.count()).select_from(
            statement.with_only_columns(literal(1)).order_by(None).subquery()
        )
    )
    result = await session.execute(statement.offset(limit * (page - 1)).limit(limit))
    return result.unique().scalars().all(), count or 0


async def get_pagination_params(
    page: int = Query(1, description="Page number, from 1.", gt=0),
    limit: int = Query(
        30, description=f"Size of a page. At most {MAX_LIMIT}.", gt=0, le=MAX_LIMIT
    ),
) -> PaginationParams:
    return PaginationParams(page, limit)


PaginationParamsQuery = Annotated[PaginationParams, Depends(get_pagination_params)]


class Pagination(BaseModel):
    total_count: int
    max_page: int


class ListResource[T: Any](BaseModel):
    items: list[T]
    pagination: Pagination

    @classmethod
    def from_paginated_results(
        cls, items: Sequence[Any], total_count: int, pagination: PaginationParams
    ) -> Self:
        return cls(
            items=list(items),
            pagination=Pagination(
                total_count=total_count,
                max_page=math.ceil(total_count / pagination.limit),
            ),
        )
