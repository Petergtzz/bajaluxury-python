from collections.abc import Iterable, Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from baja.authz.permission import Permission, has_permission
from baja.exceptions import BajaError
from baja.kit.db.postgres import AsyncReadSession
from baja.models import Property, PropertyMember, RecipientKind, User

from .schemas import RecipientSchema, RecipientUpdate


class RecipientsInvalid(BajaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


async def check_recipients(
    session: AsyncReadSession, property: Property, recipients: Sequence[RecipientUpdate]
) -> dict[UUID, RecipientKind]:
    """
    Who an email about a property goes to, as chosen: nobody twice, somebody
    on its To line, and only people who can see the property anyway.
    """
    chosen = {recipient.user_id: recipient.kind for recipient in recipients}
    if len(chosen) != len(recipients):
        raise RecipientsInvalid("Someone is on it twice.")
    if chosen and RecipientKind.to not in chosen.values():
        raise RecipientsInvalid("Address it to someone: at least one recipient is To.")
    users = (
        await session.execute(
            select(User).where(User.id.in_(chosen), User.deleted_at.is_(None))
        )
    ).scalars()
    members = set(
        (
            await session.execute(
                select(PropertyMember.user_id).where(
                    PropertyMember.property_id == property.id,
                    PropertyMember.deleted_at.is_(None),
                )
            )
        ).scalars()
    )
    allowed = {
        user.id
        for user in users
        if has_permission(user.role, Permission.properties_read_all)
        or user.id in members
    }
    if allowed != set(chosen):
        raise RecipientsInvalid(
            "Everyone who receives it must be able to see the property."
        )
    return chosen


class Recipient(Protocol):
    @property
    def user_id(self) -> UUID: ...
    @property
    def user(self) -> User: ...
    @property
    def kind(self) -> RecipientKind: ...


def to_schemas(recipients: Iterable[Recipient]) -> list[RecipientSchema]:
    """Those addressed first, then those copied, each by name."""
    return sorted(
        (
            RecipientSchema(
                user_id=r.user_id, email=r.user.email, name=r.user.name, kind=r.kind
            )
            for r in recipients
        ),
        key=lambda r: (r.kind != RecipientKind.to, (r.name or r.email).lower()),
    )
