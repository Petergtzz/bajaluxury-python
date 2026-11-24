from baja.models import PaymentMethod, Property, PropertyMember, User
from tests.fixtures.database import SaveFixture


async def create_property(
    save_fixture: SaveFixture,
    *,
    name: str = "Campo 9",
    address: str | None = None,
    is_archived: bool = False,
    balance_methods: list[PaymentMethod] | None = None,
) -> Property:
    property = Property(
        name=name,
        address=address,
        is_archived=is_archived,
        balance_methods=balance_methods or [PaymentMethod.cash],
    )
    await save_fixture(property)
    return property


async def assign_properties(
    save_fixture: SaveFixture, user: User, *properties: Property
) -> None:
    for property in properties:
        await save_fixture(PropertyMember(user_id=user.id, property_id=property.id))
