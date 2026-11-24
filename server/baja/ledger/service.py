import datetime as dt
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from baja.authz.filters import visible_properties
from baja.exceptions import Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.pagination import PaginationParams, paginate
from baja.kit.utils import generate_uuid
from baja.models import (
    PaymentMethod,
    Property,
    Transaction,
    TransactionType,
    User,
)
from baja.property.repository import PropertyRepository

from .repository import TransactionRepository
from .schemas import PropertyBalance, TransactionCreate, TransactionUpdate


class PropertyArchived(Conflict):
    def __init__(self) -> None:
        super().__init__("This property is archived and takes no new transactions.")


class TransactionDeleted(Conflict):
    def __init__(self) -> None:
        super().__init__("This entry was recorded and then deleted.")


def affects_balance(
    property: Property, type: TransactionType, payment_method: PaymentMethod | None
) -> bool:
    """
    Whether a transaction moves the owner's balance with us.

    Income always does. An expense only does when we paid it from the owner's
    money we hold, which the property's `balance_methods` name: the rest was
    paid from the owner's own cards and accounts.
    """
    if type == TransactionType.income:
        return True
    return payment_method in property.balance_methods


class LedgerService:
    async def list(
        self,
        session: AsyncReadSession,
        user: User,
        *,
        pagination: PaginationParams,
        property_id: UUID | None = None,
        type: TransactionType | None = None,
        payment_method: PaymentMethod | None = None,
        category: str | None = None,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> tuple[Sequence[Transaction], int]:
        statement = TransactionRepository.from_session(session).get_list_statement(
            user,
            property_id=property_id,
            type=type,
            payment_method=payment_method,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
        return await paginate(session, statement, pagination=pagination)

    async def get(
        self, session: AsyncReadSession, user: User, transaction_id: UUID
    ) -> Transaction:
        transaction = await TransactionRepository.from_session(session).get_visible(
            user, transaction_id
        )
        if transaction is None:
            raise ResourceNotFound()
        return transaction

    async def record(
        self,
        session: AsyncSession,
        user: User,
        transaction_create: TransactionCreate,
        *,
        source: str,
    ) -> Transaction:
        """
        Records a transaction once per `external_id` within its source.

        A repeat returns the transaction already recorded, so a client that
        lost the response can safely send the same entry again.
        """
        repository = TransactionRepository.from_session(session)
        external_id = transaction_create.external_id
        if external_id is not None:
            existing = await repository.get_by_external_id(source, external_id)
            if existing is not None:
                return self._replayed(existing)

        property = await self._get_open_property(
            session, user, transaction_create.property_id
        )
        values = transaction_create.model_dump(exclude={"external_id"})
        transaction = Transaction(
            **values,
            source=source,
            external_id=external_id or str(generate_uuid()),
            affects_balance=affects_balance(
                property, transaction_create.type, transaction_create.payment_method
            ),
            entered_by_id=user.id,
        )
        try:
            async with session.begin_nested():
                await repository.create(transaction)
        except IntegrityError:
            # The same entry, sent twice at once: the other request recorded it.
            existing = await repository.get_by_external_id(source, str(external_id))
            if existing is None:
                raise
            return self._replayed(existing)
        return transaction

    async def update(
        self,
        session: AsyncSession,
        user: User,
        transaction: Transaction,
        transaction_update: TransactionUpdate,
    ) -> Transaction:
        changes = {
            key: value
            for key, value in transaction_update.model_dump(exclude_unset=True).items()
            if value is not None or key == "description"
        }
        if {"property_id", "type", "payment_method"} & changes.keys():
            property_id = changes.get("property_id", transaction.property_id)
            if property_id == transaction.property_id:
                property = await self._get_property(session, user, property_id)
            else:
                property = await self._get_open_property(session, user, property_id)
            changes["affects_balance"] = affects_balance(
                property,
                changes.get("type", transaction.type),
                changes.get("payment_method", transaction.payment_method),
            )
        return await TransactionRepository.from_session(session).update(
            transaction, changes
        )

    async def delete(self, session: AsyncSession, transaction: Transaction) -> None:
        await TransactionRepository.from_session(session).soft_delete(transaction)

    async def list_balances(
        self, session: AsyncReadSession, user: User, *, is_archived: bool | None
    ) -> Sequence[PropertyBalance]:
        return await TransactionRepository.from_session(session).list_balances(
            visible_properties(user, Property.id), is_archived=is_archived
        )

    def _replayed(self, transaction: Transaction) -> Transaction:
        if transaction.deleted_at is not None:
            raise TransactionDeleted()
        return transaction

    async def _get_property(
        self, session: AsyncReadSession, user: User, property_id: UUID
    ) -> Property:
        property = await PropertyRepository.from_session(session).get_visible(
            user, property_id
        )
        if property is None:
            raise ResourceNotFound("Property not found.")
        return property

    async def _get_open_property(
        self, session: AsyncReadSession, user: User, property_id: UUID
    ) -> Property:
        property = await self._get_property(session, user, property_id)
        if property.is_archived:
            raise PropertyArchived()
        return property


ledger = LedgerService()
