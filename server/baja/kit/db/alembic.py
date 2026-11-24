from typing import Any, Literal

from alembic.autogenerate.api import AutogenContext

from baja.kit.extensions.sqlalchemy import StringEnum


def render_item(
    type_: str, obj: Any, autogen_context: AutogenContext
) -> str | Literal[False]:
    """Writes a StringEnum into migrations as the plain string column it is."""
    if type_ == "type" and isinstance(obj, StringEnum):
        return f"sa.String(length={obj.length})"
    return False
