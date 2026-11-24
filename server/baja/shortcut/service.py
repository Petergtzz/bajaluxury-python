from baja.exceptions import BadRequest
from baja.guest_expense.schemas import GuestExpenseCreate
from baja.guest_expense.service import guest_expense as guest_expense_service
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.ledger.repository import TransactionRepository
from baja.ledger.schemas import TransactionCreate
from baja.ledger.service import ledger as ledger_service
from baja.models import Property, TransactionType, User
from baja.property.repository import PropertyRepository

from .schemas import ShortcutConfirmation, ShortcutEntry

# Keeps its rows apart from the web's under the (source, external_id) key.
SOURCE = "shortcut"


class ShortcutService:
    async def list_villas(self, session: AsyncReadSession, user: User) -> list[str]:
        properties = await PropertyRepository.from_session(session).list_visible(
            user, is_archived=False
        )
        return [property.name for property in properties]

    async def list_categories(
        self, session: AsyncReadSession, user: User, type: TransactionType
    ) -> list[str]:
        return await TransactionRepository.from_session(session).list_categories(
            user, type
        )

    async def record(
        self, session: AsyncSession, user: User, entry: ShortcutEntry
    ) -> ShortcutConfirmation:
        """
        Records the entry once for each villa. Every villa is checked before
        anything is recorded, and the request is one transaction: it saves
        for all of them or for none.
        """
        if not entry.addresses:
            raise BadRequest("No villa selected.")
        properties = [
            await self._get_villa(session, user, name) for name in entry.addresses
        ]
        inserted = 0
        for position, property in enumerate(properties, start=1):
            external_id = (
                entry.external_id
                if len(properties) == 1
                else f"{entry.external_id}-{position}"
            )
            if entry.is_guest:
                _, created = await guest_expense_service.record(
                    session,
                    user,
                    GuestExpenseCreate(
                        property_id=property.id,
                        amount=entry.amount,
                        category=entry.category,
                        concept=entry.concept,
                        date=entry.date,
                        description=entry.description or None,
                        external_id=external_id,
                    ),
                    source=SOURCE,
                )
            else:
                assert entry.method is not None  # the schema requires it
                _, created = await ledger_service.record(
                    session,
                    user,
                    TransactionCreate(
                        property_id=property.id,
                        type=entry.type,
                        amount=entry.amount,
                        payment_method=entry.method,
                        category=entry.category,
                        concept=entry.concept,
                        date=entry.date,
                        description=entry.description or None,
                        external_id=external_id,
                    ),
                    source=SOURCE,
                )
            inserted += created
        return confirmation(entry, [p.name for p in properties], inserted)

    async def _get_villa(
        self, session: AsyncReadSession, user: User, name: str
    ) -> Property:
        repository = PropertyRepository.from_session(session)
        property = await repository.get_by_name(name)
        if property is None or (
            await repository.get_visible(user, property.id) is None
        ):
            raise BadRequest(f"No villa named {name!r}.")
        return property


def confirmation(
    entry: ShortcutEntry, villas: list[str], inserted: int
) -> ShortcutConfirmation:
    """
    The title carries what gets misread, the amount and the villa; the body
    the rest. A resend must not look like a save.
    """
    amount = f"${entry.amount:,.2f}"
    if len(villas) == 1:
        title, villa_line = f"{amount} · {villas[0]}", None
    else:
        # Counted in the title, named below: a count can't tell the right villas.
        title = f"{amount} each · {len(villas)} villas"
        villa_line = " · ".join(villas)

    if entry.type == TransactionType.income and not entry.is_guest:
        facts = ["Deposit", f"{entry.date:%d %b}"]
    else:
        facts = [entry.concept.capitalize()]
        facts += ["Guest"] if entry.is_guest else [str(entry.method).title()]
        facts += [f"{entry.date:%d %b}"]
    summary = " · ".join(facts)
    if villa_line:
        summary = f"{villa_line}\n{summary}"

    if inserted == 0:
        title = f"Already saved · {amount}"
    elif inserted < len(villas):
        title = f"{inserted} of {len(villas)} saved · {amount}"
    return ShortcutConfirmation(inserted=inserted, title=title, summary=summary)


shortcut = ShortcutService()
