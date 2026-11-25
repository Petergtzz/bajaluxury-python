import datetime as dt
import logging
from uuid import UUID

from baja.company.service import today as company_today
from baja.exceptions import ResourceNotFound
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.ledger.schemas import TransactionCreate
from baja.ledger.service import ledger as ledger_service
from baja.models import RecurringCharge, TransactionType, User
from baja.property.service import property as property_service

from .dates import due_dates
from .repository import RecurringChargeRepository
from .schemas import RecurringChargeCreate, RecurringChargeUpdate

log = logging.getLogger("baja.recurring")

# The ledger rows it records. Their id is the charge and the month, so a month
# is charged once even if the cursor were lost.
SOURCE = "recurring"


class RecurringChargeService:
    async def list(
        self, session: AsyncReadSession, user: User, *, property_id: UUID | None
    ) -> list[RecurringCharge]:
        return await RecurringChargeRepository.from_session(session).list_visible(
            user, property_id=property_id
        )

    async def get(
        self, session: AsyncReadSession, user: User, recurring_charge_id: UUID
    ) -> RecurringCharge:
        charge = await RecurringChargeRepository.from_session(session).get_visible(
            user, recurring_charge_id
        )
        if charge is None:
            raise ResourceNotFound()
        return charge

    async def create(
        self, session: AsyncSession, user: User, charge_create: RecurringChargeCreate
    ) -> RecurringCharge:
        property = await property_service.get_open(
            session, user, charge_create.property_id
        )
        starts_on = charge_create.starts_on or await company_today(session)
        return await RecurringChargeRepository.from_session(session).create(
            RecurringCharge(
                **charge_create.model_dump(exclude={"starts_on"}),
                property=property,
                charged_through=starts_on - dt.timedelta(days=1),
            )
        )

    async def update(
        self,
        session: AsyncSession,
        charge: RecurringCharge,
        charge_update: RecurringChargeUpdate,
    ) -> RecurringCharge:
        changes = {
            key: value
            for key, value in charge_update.model_dump(exclude_unset=True).items()
            if value is not None or key == "description"
        }
        return await RecurringChargeRepository.from_session(session).update(
            charge, changes
        )

    async def delete(self, session: AsyncSession, charge: RecurringCharge) -> None:
        await RecurringChargeRepository.from_session(session).soft_delete(charge)

    async def charge_due(self, session: AsyncSession) -> int:
        """
        Records every charge that fell due since the last run, up to today.

        Safe to run any number of times, and at once: each charge's cursor
        only moves forward, and concurrent runs wait for each other. An
        archived property's charges move on without charging.
        """
        today = await company_today(session)
        charged = 0
        for charge in await RecurringChargeRepository.from_session(session).list_all():
            if charge.charged_through >= today:
                continue
            if not charge.property.is_archived:
                for due in due_dates(
                    charge.day_of_month, charge.charged_through, today
                ):
                    _, created = await ledger_service.record_for(
                        session,
                        charge.property,
                        TransactionCreate(
                            property_id=charge.property_id,
                            type=TransactionType.expense,
                            amount=charge.amount,
                            payment_method=charge.payment_method,
                            category=charge.category,
                            concept=charge.concept,
                            date=due,
                            description=charge.description,
                            external_id=f"{charge.id}:{due:%Y-%m}",
                        ),
                        source=SOURCE,
                        entered_by=None,
                    )
                    charged += created
            charge.charged_through = today
        await session.flush()
        log.info("Recorded %d recurring charge(s) through %s", charged, today)
        return charged


recurring_charge = RecurringChargeService()
