from enum import StrEnum
from typing import Any

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class StringEnum[E: StrEnum](TypeDecorator[E]):
    """A StrEnum stored as plain text; pair it with a CheckConstraint on the values."""

    impl = String
    cache_ok = True

    def __init__(self, enum: type[E], *, length: int, **kwargs: Any) -> None:
        super().__init__(length, **kwargs)
        self.enum = enum
        self.length = length

    def process_bind_param(self, value: E | str | None, dialect: Dialect) -> str | None:
        return None if value is None else self.enum(value).value

    def process_result_value(self, value: str | None, dialect: Dialect) -> E | None:
        return None if value is None else self.enum(value)


def enum_check(column: str, enum: type[StrEnum]) -> str:
    """The SQL for a CheckConstraint allowing exactly the enum's values."""
    return "{} IN ({})".format(
        column, ", ".join(f"'{member.value}'" for member in enum)
    )
