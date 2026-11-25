import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from baja.kit.schemas import Money
from baja.models import Currency, PaymentMethod, TransactionType


class StatementEntry(BaseModel):
    id: UUID
    date: dt.date
    type: TransactionType
    category: str
    concept: str
    payment_method: PaymentMethod | None
    description: str | None
    amount: Money
    affects_balance: bool
    balance_after: Money = Field(description="The balance once this entry is counted.")


class CategoryTotal(BaseModel):
    category: str
    total: Money
    entries: list[StatementEntry] = Field(description="Largest first.")


class MethodTotal(BaseModel):
    payment_method: PaymentMethod | None
    total: Money


class Statement(BaseModel):
    """
    A property's ledger over a period: every report is a rendering of one.

    Amounts are in `currency`. Converted from the company's, each entry is
    converted and every total and balance is worked out from the converted
    entries, so the document always adds up.
    """

    property_id: UUID
    property_name: str
    start: dt.date
    end: dt.date
    currency: Currency
    exchange_rate: Decimal | None = Field(
        description="Company currency per US dollar, when converted; else null."
    )
    opening_balance: Money = Field(description="The balance before `start`.")
    closing_balance: Money = Field(description="The balance after `end`.")
    income_total: Money
    expense_total: Money = Field(description="Every expense, however it was paid.")
    balance_expense_total: Money = Field(
        description="The expenses paid from the owner's balance with us."
    )
    expenses_by_method: list[MethodTotal] = Field(description="Largest first.")
    expenses_by_category: list[CategoryTotal] = Field(description="Largest first.")
    entries: list[StatementEntry] = Field(description="In the order they happened.")
