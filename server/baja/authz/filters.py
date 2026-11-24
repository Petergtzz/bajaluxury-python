from uuid import UUID

from sqlalchemy import ColumnElement, select, true
from sqlalchemy.orm import InstrumentedAttribute

from baja.models import PropertyMember, User

from .permission import Permission, has_permission


def visible_properties(
    user: User, property_id: InstrumentedAttribute[UUID]
) -> ColumnElement[bool]:
    """
    The rows a user may see, by the property they belong to.

    Every query over property-owned rows applies it: a homeowner who asks for a
    property that isn't theirs gets the same 404 as one that doesn't exist.
    """
    if has_permission(user.role, Permission.properties_read_all):
        return true()
    return property_id.in_(
        select(PropertyMember.property_id).where(
            PropertyMember.user_id == user.id, PropertyMember.deleted_at.is_(None)
        )
    )
