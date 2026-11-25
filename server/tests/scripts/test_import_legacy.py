import dataclasses
import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select

import baja.company.service
from baja.kit.db.postgres import AsyncSession
from baja.models import (
    Checklist,
    ChecklistItem,
    ChecklistTemplateItem,
    Company,
    GuestExpense,
    PaymentMethod,
    Property,
    PropertyMember,
    RecurringCharge,
    Role,
    Transaction,
    User,
)
from scripts.import_legacy import (
    RECURRING_CHARGES,
    BalanceCheck,
    Legacy,
    LegacyChecklist,
    LegacyChecklistItem,
    LegacyDataInvalid,
    LegacyGuestExpense,
    LegacyHouse,
    LegacyRecurringCharge,
    LegacyTemplateItem,
    LegacyTransaction,
    LegacyUser,
    import_legacy,
)
from tests.fixtures import (
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

CAMPO = LegacyHouse(house_id=1, address=" Campo 9 ", account_type="app", is_active=True)
SOLEIL = LegacyHouse(house_id=40, address="Soleil", account_type="bank", is_active=True)
OLD = LegacyHouse(
    house_id=22, address="Soleil (old)", account_type="app", is_active=False
)


def transaction(id: int, house_id: int = 1, **changes: object) -> LegacyTransaction:
    values: dict[str, object] = {
        "id": id,
        "house_id": house_id,
        "type": "expense",
        "amount": Decimal("100.00"),
        "payment_method": "cash",
        "category": "utilities",
        "concept": "cfe",
        "date": dt.date(2026, 7, 1),
        "description": None,
        "created_at": dt.datetime(2026, 7, 1, 18, 30),
    }
    return LegacyTransaction(**(values | changes))  # type: ignore[arg-type]


LEGACY = Legacy(
    houses=[CAMPO, SOLEIL, OLD],
    transactions=[
        transaction(1, type="income", amount=Decimal("1000.00"), payment_method="WIRE"),
        transaction(2, amount=Decimal("250.50")),
        transaction(3, payment_method="credit card"),
        transaction(4, payment_method=""),
        transaction(5, 40, payment_method="debit card", amount=Decimal("70.00")),
        transaction(6, 40, payment_method="cash"),
        transaction(7, 22, source="reminders", external_id="R-7"),
    ],
    balances={1: Decimal("749.50"), 40: Decimal("-70.00"), 22: Decimal("55.00")},
)


async def transactions(session: AsyncSession) -> list[Transaction]:
    result = await session.execute(
        select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.external_id)
    )
    return list(result.scalars())


async def test_copies_properties_with_their_balance_rule(
    session: AsyncSession,
) -> None:
    await import_legacy(session, LEGACY)

    properties = (
        await session.execute(select(Property).order_by(Property.name))
    ).scalars()
    assert [(p.name, p.is_archived, p.balance_methods) for p in properties] == [
        ("Campo 9", False, [PaymentMethod.cash]),
        ("Soleil", False, [PaymentMethod.debit_card, PaymentMethod.withdrawal]),
        ("Soleil (old)", True, [PaymentMethod.cash]),
    ]


async def test_copies_transactions_normalized(session: AsyncSession) -> None:
    await import_legacy(session, LEGACY)

    copied = {t.external_id: t for t in await transactions(session)}
    assert sorted(copied) == ["1", "2", "3", "4", "5", "6", "R-7"]
    assert (copied["1"].source, copied["1"].payment_method) == (
        "legacy",
        PaymentMethod.wire,
    )
    assert copied["4"].payment_method is None
    assert copied["R-7"].source == "reminders"
    assert copied["2"].amount == Decimal("250.50")
    assert copied["2"].created_at == dt.datetime(2026, 7, 1, 18, 30, tzinfo=dt.UTC)
    assert [copied[k].affects_balance for k in ("1", "2", "3", "4", "5", "6")] == [
        True,
        True,
        False,
        False,
        True,
        False,
    ]


async def test_compares_balances_with_the_old_table(session: AsyncSession) -> None:
    checks = (await import_legacy(session, LEGACY)).balances

    assert checks == [
        BalanceCheck("Campo 9", Decimal("749.50"), Decimal("749.50")),
        BalanceCheck("Soleil", Decimal("-70.00"), Decimal("-70.00")),
        BalanceCheck(
            "Soleil (old)", Decimal("55.00"), Decimal("-100.00"), is_archived=True
        ),
    ]


async def test_running_again_follows_the_old_database(session: AsyncSession) -> None:
    await import_legacy(session, LEGACY)
    edited = dataclasses.replace(LEGACY.transactions[1], amount=Decimal("300.00"))
    again = dataclasses.replace(
        LEGACY,
        transactions=[
            LEGACY.transactions[0],
            edited,
            *LEGACY.transactions[3:],
            transaction(8, concept="new since"),
        ],
    )

    await import_legacy(session, again)

    copied = {t.external_id: t for t in await transactions(session)}
    assert sorted(copied) == ["1", "2", "4", "5", "6", "8", "R-7"]
    assert copied["2"].amount == Decimal("300.00")


async def test_leaves_the_apps_own_entries_alone(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    own_id = (await create_transaction(save_fixture, campo, source="web")).id

    await import_legacy(session, LEGACY)

    assert own_id in {t.id for t in await transactions(session)}


async def test_refuses_data_it_cannot_map_and_says_where(
    session: AsyncSession,
) -> None:
    broken = dataclasses.replace(
        LEGACY,
        transactions=[
            transaction(1, payment_method="bitcoin"),
            transaction(2, amount=Decimal(0)),
            transaction(3, house_id=99),
        ],
    )

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(session, broken)

    assert error.value.problems == [
        "transaction 1: unknown payment method 'bitcoin'",
        "transaction 2: amount 0 is not positive",
        "transaction 3: unknown house 99",
    ]


def guest_expense(id: int, house_id: int = 1, **changes: object) -> LegacyGuestExpense:
    values: dict[str, object] = {
        "id": id,
        "house_id": house_id,
        "amount": Decimal("456.50"),
        "category": "transport",
        "concept": "airport pickup",
        "date": dt.date(2026, 7, 2),
        "description": "arrival",
        "created_at": None,
    }
    return LegacyGuestExpense(**(values | changes))  # type: ignore[arg-type]


async def test_copies_guest_expenses_apart_from_the_ledger(
    session: AsyncSession,
) -> None:
    legacy = dataclasses.replace(
        LEGACY,
        guest_expenses=[
            guest_expense(1),
            guest_expense(2, source="shortcut", external_id="S-2"),
        ],
    )

    checks = (await import_legacy(session, legacy)).balances
    again = (
        await import_legacy(
            session,
            dataclasses.replace(legacy, guest_expenses=legacy.guest_expenses[1:]),
        )
    ).balances

    copied = (
        await session.execute(
            select(GuestExpense).where(GuestExpense.deleted_at.is_(None))
        )
    ).scalars()
    assert [(g.source, g.external_id, g.amount) for g in copied] == [
        ("shortcut", "S-2", Decimal("456.50"))
    ]
    assert checks == again
    assert checks[0].new == Decimal("749.50")


async def test_lists_problems_in_both_tables_together(session: AsyncSession) -> None:
    broken = dataclasses.replace(
        LEGACY,
        transactions=[transaction(1, type="refund")],
        guest_expenses=[guest_expense(9, category=None)],
    )

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(session, broken)

    assert error.value.problems == [
        "transaction 1: unknown type 'refund'",
        "guest expense 9: has no category",
    ]


def user(
    user_id: int, role: str, house_id: int | None = None, **changes: object
) -> LegacyUser:
    values: dict[str, object] = {
        "user_id": user_id,
        "email": f"user{user_id}@example.com",
        "name": f"User {user_id}",
        "house_id": house_id,
        "roles": [role],
    }
    return LegacyUser(**(values | changes))  # type: ignore[arg-type]


USERS = [
    user(1, "admin"),
    user(67, "editor"),
    user(3, "viewer", house_id=1, send_report=True),
    user(51, "viewer", house_id=40, name=None),
]


async def people(session: AsyncSession) -> dict[str, tuple[Role, str | None, set[str]]]:
    users = (
        await session.execute(select(User).where(User.deleted_at.is_(None)))
    ).scalars()
    members = await session.execute(
        select(PropertyMember.user_id, Property.name)
        .join(Property, Property.id == PropertyMember.property_id)
        .where(PropertyMember.deleted_at.is_(None))
    )
    assigned: dict[object, set[str]] = {}
    for user_id, name in members:
        assigned.setdefault(user_id, set()).add(name)
    return {u.email: (u.role, u.name, assigned.get(u.id, set())) for u in users}


async def test_copies_users_with_their_role_and_villa(session: AsyncSession) -> None:
    await import_legacy(session, dataclasses.replace(LEGACY, users=USERS))

    assert await people(session) == {
        "user1@example.com": (Role.owner, "User 1", set()),
        "user67@example.com": (Role.manager, "User 67", set()),
        "user3@example.com": (Role.homeowner, "User 3", {"Campo 9"}),
        "user51@example.com": (Role.homeowner, None, {"Soleil"}),
    }


async def test_running_again_follows_role_and_villa_changes(
    session: AsyncSession,
) -> None:
    await import_legacy(session, dataclasses.replace(LEGACY, users=USERS))
    moved = [
        *USERS[:2],
        dataclasses.replace(USERS[2], house_id=40, email="USER3@example.com "),
        dataclasses.replace(USERS[3], roles=["editor"]),
    ]

    await import_legacy(session, dataclasses.replace(LEGACY, users=moved))

    found = await people(session)
    assert len(found) == 4
    assert found["user3@example.com"] == (Role.homeowner, "User 3", {"Soleil"})
    assert found["user51@example.com"] == (Role.manager, None, set())


async def test_matches_existing_users_and_lists_the_others(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    lore = await create_user(
        save_fixture, Role.homeowner, email="User3@Example.com", name="Lore"
    )
    await assign_properties(save_fixture, lore, campo)
    await create_user(save_fixture, Role.owner, email="new@example.com")

    report = await import_legacy(session, dataclasses.replace(LEGACY, users=USERS))

    found = await people(session)
    assert found["User3@Example.com"] == (Role.homeowner, "User 3", {"Campo 9"})
    assert "new@example.com" in found
    assert report.users_only_here == ["new@example.com"]


async def test_records_who_entered_each_row(session: AsyncSession) -> None:
    legacy = dataclasses.replace(
        LEGACY,
        users=USERS,
        transactions=[transaction(1, entered_by=67), transaction(2)],
    )

    await import_legacy(session, legacy)

    manager = (
        await session.execute(select(User).where(User.email == "user67@example.com"))
    ).scalar_one()
    copied = {t.external_id: t.entered_by_id for t in await transactions(session)}
    assert copied == {"1": manager.id, "2": None}


async def test_refuses_users_it_cannot_map(session: AsyncSession) -> None:
    broken = dataclasses.replace(
        LEGACY,
        users=[
            user(1, "admin", email=" "),
            user(2, "superuser"),
            user(3, "viewer", house_id=99),
            user(4, "viewer", email="USER5@example.com"),
            user(5, "viewer"),
            user(6, "viewer", roles=[]),
        ],
    )

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(session, broken)

    assert error.value.problems == [
        "user 1: has no email",
        "user 2: roles ['superuser'] are not one of admin, editor, viewer",
        "user 3: unknown house 99",
        "user 5: same email as user 4",
        "user 6: roles [] are not one of admin, editor, viewer",
    ]


CHARGES = [
    LegacyRecurringCharge(
        1,
        Decimal(8500),
        PaymentMethod.cash,
        "staff",
        "property management",
        "monthly property management fee",
        10,
    ),
    LegacyRecurringCharge(
        40,
        Decimal(1305),
        PaymentMethod.credit_card,
        "utilities",
        "starlink",
        "monthly fee",
        15,
    ),
]


async def test_copies_recurring_charges_starting_after_the_import(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = dt.datetime(2026, 11, 25, 18, tzinfo=dt.UTC)
    monkeypatch.setattr(baja.company.service, "utc_now", lambda: now)
    await import_legacy(session, dataclasses.replace(LEGACY, recurring_charges=CHARGES))
    now = dt.datetime(2026, 12, 3, 18, tzinfo=dt.UTC)
    raised = dataclasses.replace(CHARGES[0], amount=Decimal(9000))

    await import_legacy(
        session, dataclasses.replace(LEGACY, recurring_charges=[raised, CHARGES[1]])
    )

    charges = (
        await session.execute(
            select(RecurringCharge, Property.name)
            .join(Property, Property.id == RecurringCharge.property_id)
            .order_by(Property.name)
        )
    ).all()
    assert [
        (name, c.amount, c.concept, c.day_of_month, c.charged_through)
        for c, name in charges
    ] == [
        (
            "Campo 9",
            Decimal("9000.00"),
            "property management",
            10,
            dt.date(2026, 12, 3),
        ),
        ("Soleil", Decimal("1305.00"), "starlink", 15, dt.date(2026, 12, 3)),
    ]


async def test_sets_up_the_company_laravel_hard_coded(session: AsyncSession) -> None:
    await import_legacy(session, LEGACY)
    await import_legacy(session, LEGACY)

    [company] = (await session.execute(select(Company))).scalars()
    assert (company.timezone, company.currency, company.usd_exchange_rate) == (
        "America/Mazatlan",
        "MXN",
        Decimal("17.0000"),
    )


async def test_refuses_charges_for_unknown_houses(session: AsyncSession) -> None:
    unknown = dataclasses.replace(CHARGES[0], house_id=99)

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(
            session, dataclasses.replace(LEGACY, recurring_charges=[unknown])
        )

    assert error.value.problems == [
        "recurring charge 'property management': unknown house 99"
    ]


def test_the_charge_table_has_every_laravel_command_charge() -> None:
    assert len(RECURRING_CHARGES) == 60
    assert {c.day_of_month for c in RECURRING_CHARGES} == {10, 15, 31}
    assert all(c.amount > 0 for c in RECURRING_CHARGES)


async def test_copies_who_gets_the_monthly_report(session: AsyncSession) -> None:
    await import_legacy(session, dataclasses.replace(LEGACY, users=USERS))

    users = (await session.execute(select(User).order_by(User.email))).scalars()
    assert [u.email for u in users if u.receives_monthly_report] == [
        "user3@example.com"
    ]


CREATED = dt.datetime(2026, 6, 1, 15, 30)
CHECKLISTS = dataclasses.replace(
    LEGACY,
    users=USERS,
    template_items=[
        LegacyTemplateItem(1, "check_in", "Keys are in the lockbox", 1),
        LegacyTemplateItem(2, "weekly", "Run every tap", 1),
    ],
    checklists=[
        LegacyChecklist(
            10, 1, 67, "check_in", "completed", CREATED, ["a@example.com"], CREATED
        ),
        LegacyChecklist(11, 40, 999, "weekly", "in_progress", None, None, CREATED),
    ],
    checklist_items=[
        LegacyChecklistItem(
            100, 10, "Keys are in the lockbox", 1, True, "two", CREATED, CREATED
        ),
        LegacyChecklistItem(101, 11, "Run every tap", 1, False, None, None, CREATED),
    ],
)


async def live[M: (Checklist, ChecklistItem, ChecklistTemplateItem)](
    session: AsyncSession, model: type[M]
) -> list[M]:
    result = await session.execute(
        select(model).where(model.deleted_at.is_(None)).order_by(model.created_at)
    )
    return list(result.scalars())


async def test_copies_checklists_their_items_and_templates(
    session: AsyncSession,
) -> None:
    await import_legacy(session, CHECKLISTS)

    templates = await live(session, ChecklistTemplateItem)
    checklists = await live(session, Checklist)
    items = await live(session, ChecklistItem)
    assert sorted(t.description for t in templates) == [
        "Keys are in the lockbox",
        "Run every tap",
    ]
    done, open_ = sorted(checklists, key=lambda c: c.type)
    manager = (
        await session.execute(select(User).where(User.email == "user67@example.com"))
    ).scalar_one()
    assert (done.completed_at, done.emailed_to, done.created_by_id) == (
        CREATED.replace(tzinfo=dt.UTC),
        ["a@example.com"],
        manager.id,
    )
    assert (open_.completed_at, open_.emailed_to, open_.created_by_id) == (
        None,
        [],
        None,
    )
    assert {(i.checklist_id, i.is_checked, i.note) for i in items} == {
        (done.id, True, "two"),
        (open_.id, False, None),
    }


async def test_running_again_follows_and_keeps_the_apps_own(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    await import_legacy(session, CHECKLISTS)
    own = ChecklistTemplateItem(type="weekly", description="Check the roof", position=2)
    await save_fixture(own)
    own_id = own.id

    await import_legacy(
        session,
        dataclasses.replace(
            CHECKLISTS,
            template_items=[
                dataclasses.replace(CHECKLISTS.template_items[0], description="Keys!")
            ],
            checklists=CHECKLISTS.checklists[:1],
            checklist_items=CHECKLISTS.checklist_items[:1],
        ),
    )

    templates = await live(session, ChecklistTemplateItem)
    assert sorted((t.description, t.id == own_id) for t in templates) == [
        ("Check the roof", True),
        ("Keys!", False),
    ]
    assert len(await live(session, Checklist)) == 1
    assert len(await live(session, ChecklistItem)) == 1


async def test_refuses_checklists_it_cannot_place(session: AsyncSession) -> None:
    broken = dataclasses.replace(
        CHECKLISTS,
        template_items=[LegacyTemplateItem(1, "monthly", "x", 1)],
        checklists=[dataclasses.replace(CHECKLISTS.checklists[0], house_id=99)],
        checklist_items=[
            dataclasses.replace(CHECKLISTS.checklist_items[0], checklist_id=7)
        ],
    )

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(session, broken)

    assert error.value.problems == [
        "checklist template item 1: unknown type 'monthly'",
        "checklist 10: unknown house 99",
        "checklist item 100: unknown checklist 7",
    ]
