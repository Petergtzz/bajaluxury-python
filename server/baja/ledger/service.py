from collections.abc import Sequence
from uuid import UUID

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
from baja.property.service import property as property_service

from .repository import TransactionRepository
from .schemas import (
    PropertyBalance,
    TransactionCreate,
    TransactionFilters,
    TransactionSummary,
    TransactionUpdate,
)


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
        filters: TransactionFilters,
        *,
        pagination: PaginationParams,
    ) -> tuple[Sequence[Transaction], int]:
        statement = TransactionRepository.from_session(session).get_list_statement(
            user, filters
        )
        return await paginate(session, statement, pagination=pagination)

    async def summarize(
        self, session: AsyncReadSession, user: User, filters: TransactionFilters
    ) -> TransactionSummary:
        """What `list` would list, added up across its pages."""
        repository = TransactionRepository.from_session(session)
        return await repository.summarize(repository.get_list_statement(user, filters))

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
    ) -> tuple[Transaction, bool]:
        """
        Records a transaction once per `external_id` within its source.

        A repeat returns the transaction already recorded, so a client that
        lost the response can safely send the same entry again. Says whether
        it recorded a new one.
        """
        property = await property_service.get_open(
            session, user, transaction_create.property_id
        )
        return await self.record_for(
            session, property, transaction_create, source=source, entered_by=user
        )

    async def record_for(
        self,
        session: AsyncSession,
        property: Property,
        transaction_create: TransactionCreate,
        *,
        source: str,
        entered_by: User | None,
    ) -> tuple[Transaction, bool]:
        """`record`, for a property the caller already checked, by anyone or nobody."""
        repository = TransactionRepository.from_session(session)
        external_id = transaction_create.external_id or str(generate_uuid())
        transaction, created = await repository.create_once(
            Transaction(
                **transaction_create.model_dump(exclude={"external_id", "property_id"}),
                property_id=property.id,
                source=source,
                external_id=external_id,
                affects_balance=affects_balance(
                    property,
                    transaction_create.type,
                    transaction_create.payment_method,
                ),
                entered_by_id=entered_by.id if entered_by else None,
            ),
            repository.get_by_external_id_statement(source, external_id),
        )
        return self._replayed(transaction), created

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
                property = await property_service.get(session, user, property_id)
            else:
                property = await property_service.get_open(session, user, property_id)
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


ledger = LedgerService()
