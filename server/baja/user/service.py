from collections.abc import Sequence
from uuid import UUID

from baja.exceptions import BajaError, Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Role, User
from baja.property.repository import PropertyRepository

from .repository import UserRepository
from .schemas import ManagedUserCreate, ManagedUserSchema, ManagedUserUpdate


class EmailTaken(Conflict):
    def __init__(self) -> None:
        super().__init__("Another user already has this email.")


class InvalidAssignment(BajaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class CannotChangeYourself(BajaError):
    def __init__(self, action: str) -> None:
        super().__init__(f"You can't {action} yourself. Ask another owner.", 409)


class UserService:
    async def list(self, session: AsyncReadSession) -> list[ManagedUserSchema]:
        repository = UserRepository.from_session(session)
        users = await repository.list_all()
        assigned = await repository.get_property_ids([user.id for user in users])
        return [self._schema(user, assigned[user.id]) for user in users]

    async def get(self, session: AsyncReadSession, user_id: UUID) -> User:
        user = await UserRepository.from_session(session).get_by_id(user_id)
        if user is None:
            raise ResourceNotFound()
        return user

    async def get_schema(
        self, session: AsyncReadSession, user: User
    ) -> ManagedUserSchema:
        assigned = await UserRepository.from_session(session).get_property_ids(
            [user.id]
        )
        return self._schema(user, assigned[user.id])

    async def create(
        self, session: AsyncSession, user_create: ManagedUserCreate
    ) -> User:
        repository = UserRepository.from_session(session)
        if await repository.get_by_email(user_create.email) is not None:
            raise EmailTaken()
        await self._check_assignment(
            session, user_create.role, user_create.property_ids
        )
        user = await repository.create(
            User(
                email=user_create.email,
                name=user_create.name or None,
                role=user_create.role,
                receives_monthly_report=user_create.receives_monthly_report,
            )
        )
        await repository.set_property_ids(user, user_create.property_ids)
        return user

    async def update(
        self,
        session: AsyncSession,
        acting: User,
        user: User,
        user_update: ManagedUserUpdate,
    ) -> User:
        repository = UserRepository.from_session(session)
        fields = user_update.model_fields_set
        role = user_update.role if user_update.role is not None else user.role
        if role != user.role and user.id == acting.id:
            raise CannotChangeYourself("change the role of")
        if (
            user_update.email is not None
            and user_update.email.lower() != user.email.lower()
        ):
            if await repository.get_by_email(user_update.email) is not None:
                raise EmailTaken()
            user.email = user_update.email
            user.email_verified = False
        if "name" in fields:
            user.name = user_update.name or None
        if user_update.receives_monthly_report is not None:
            user.receives_monthly_report = user_update.receives_monthly_report
        property_ids = user_update.property_ids
        if role != Role.homeowner:
            # Owners and managers see everything: assignments would only mislead.
            property_ids = property_ids or set()
        await self._check_assignment(session, role, property_ids or set())
        user.role = role
        if property_ids is not None:
            await repository.set_property_ids(user, property_ids)
        await session.flush()
        return user

    async def delete(self, session: AsyncSession, acting: User, user: User) -> None:
        """Their sessions stop working with them; their history stays."""
        if user.id == acting.id:
            raise CannotChangeYourself("delete")
        repository = UserRepository.from_session(session)
        await repository.set_property_ids(user, set())
        await repository.soft_delete(user)

    async def _check_assignment(
        self, session: AsyncReadSession, role: Role, property_ids: set[UUID]
    ) -> None:
        if not property_ids:
            return
        if role != Role.homeowner:
            raise InvalidAssignment(
                "Only homeowners are assigned properties: owners and managers "
                "see them all."
            )
        existing = await PropertyRepository.from_session(session).count_existing(
            property_ids
        )
        if existing != len(property_ids):
            raise InvalidAssignment("One of these properties doesn't exist.")

    def _schema(self, user: User, property_ids: Sequence[UUID]) -> ManagedUserSchema:
        return ManagedUserSchema(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            property_ids=sorted(property_ids),
            receives_monthly_report=user.receives_monthly_report,
        )


user = UserService()
