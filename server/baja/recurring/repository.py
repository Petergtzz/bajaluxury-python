from uuid import UUID

from sqlalchemy import Select, func
from sqlalchemy.orm import contains_eager

from baja.authz.filters import visible_properties
from baja.kit.repository import RepositoryBase
from baja.models import Property, RecurringCharge, User


class RecurringChargeRepository(RepositoryBase[RecurringCharge]):
    model = RecurringCharge

    def get_with_property_statement(self) -> Select[RecurringCharge]:
        return (
            self.get_base_statement()
            .join(RecurringCharge.property)
            .where(Property.deleted_at.is_(None))
            .options(contains_eager(RecurringCharge.property))
        )

    async def list_visible(
        self, user: User, *, property_id: UUID | None = None
    ) -> list[RecurringCharge]:
        statement = (
            self.get_with_property_statement()
            .where(visible_properties(user, RecurringCharge.property_id))
            .order_by(
                func.lower(Property.name),
                RecurringCharge.day_of_month,
                RecurringCharge.concept,
            )
        )
        if property_id is not None:
            statement = statement.where(RecurringCharge.property_id == property_id)
        return await self.get_all(statement)

    async def get_visible(
        self, user: User, recurring_charge_id: UUID
    ) -> RecurringCharge | None:
        return await self.get_one_or_none(
            self.get_with_property_statement().where(
                RecurringCharge.id == recurring_charge_id,
                visible_properties(user, RecurringCharge.property_id),
            )
        )

    async def list_all(self) -> list[RecurringCharge]:
        """Every charge, locked: two runs at once take turns instead of both charging."""
        return await self.get_all(
            self.get_with_property_statement()
            .order_by(RecurringCharge.id)
            .with_for_update(of=RecurringCharge)
        )
