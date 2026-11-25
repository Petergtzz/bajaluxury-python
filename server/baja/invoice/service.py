from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from baja.company.service import get_company
from baja.exceptions import BajaError, Conflict, ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Invoice, InvoiceLine, User
from baja.property.service import property as property_service
from baja.worker import enqueue_job

from .repository import InvoiceRepository
from .schemas import InvoiceCreate

SEND = "invoice.send"
CENT = Decimal("0.01")


class InvoiceLinesInvalid(BajaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 422)


class GuestExpenseInvoiced(Conflict):
    def __init__(self, number: str) -> None:
        super().__init__(f"A guest expense on it is already billed by {number}.")


class InvoiceService:
    async def list(
        self, session: AsyncReadSession, user: User, *, property_id: UUID | None
    ) -> list[Invoice]:
        return await InvoiceRepository.from_session(session).list_visible(
            user, property_id=property_id
        )

    async def get(
        self, session: AsyncReadSession, user: User, invoice_id: UUID
    ) -> Invoice:
        invoice = await InvoiceRepository.from_session(session).get_visible(
            user, invoice_id
        )
        if invoice is None:
            raise ResourceNotFound()
        return invoice

    async def issue(
        self, session: AsyncSession, user: User, invoice_create: InvoiceCreate
    ) -> Invoice:
        """Numbers it, keeps it, and emails it once the request commits."""
        property = await property_service.get_open(
            session, user, invoice_create.property_id
        )
        repository = InvoiceRepository.from_session(session)
        await self._check_guest_expenses(repository, invoice_create)

        amounts = [
            (line.quantity * line.unit_price).quantize(CENT, ROUND_HALF_UP)
            for line in invoice_create.lines
        ]
        subtotal = sum(amounts, Decimal(0))
        tax = (subtotal * invoice_create.tax_rate).quantize(CENT, ROUND_HALF_UP)
        year = invoice_create.issued_on.year
        invoice = await repository.create(
            Invoice(
                **invoice_create.model_dump(
                    exclude={"lines", "exchange_rate", "property_id"}
                ),
                property_id=property.id,
                year=year,
                sequence=await repository.next_sequence(year),
                exchange_rate=invoice_create.exchange_rate
                or (await get_company(session)).usd_exchange_rate,
                subtotal=subtotal,
                tax=tax,
                total=subtotal + tax,
                created_by_id=user.id,
            )
        )
        for position, (line, amount) in enumerate(
            zip(invoice_create.lines, amounts, strict=True), start=1
        ):
            session.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    position=position,
                    amount=amount,
                    **line.model_dump(),
                )
            )
        await session.flush()
        enqueue_job(SEND, str(invoice.id))
        reloaded = await repository.get_visible(user, invoice.id, fresh=True)
        assert reloaded is not None
        return reloaded

    async def delete(self, session: AsyncSession, invoice: Invoice) -> None:
        """Its number stays used, and its guest expenses can be billed again."""
        await InvoiceRepository.from_session(session).soft_delete(invoice)

    async def _check_guest_expenses(
        self, repository: InvoiceRepository, invoice_create: InvoiceCreate
    ) -> None:
        ids = [
            line.guest_expense_id
            for line in invoice_create.lines
            if line.guest_expense_id is not None
        ]
        if len(ids) != len(set(ids)):
            raise InvoiceLinesInvalid("A guest expense is on two lines.")
        guest_expenses = await repository.get_guest_expenses(ids)
        for id in ids:
            guest_expense = guest_expenses.get(id)
            if guest_expense is None or (
                guest_expense.property_id != invoice_create.property_id
            ):
                raise InvoiceLinesInvalid(
                    "A guest expense on it isn't one of this property's."
                )
            billed_by = guest_expense.invoice_id  # type: ignore[attr-defined]
            if billed_by is not None:
                other = await repository.get_one_or_none(
                    repository.get_base_statement().where(Invoice.id == billed_by)
                )
                raise GuestExpenseInvoiced(other.number if other else "another invoice")


invoice = InvoiceService()
