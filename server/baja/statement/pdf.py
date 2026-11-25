import datetime as dt
from decimal import Decimal

from baja.kit.paper import (
    BODY,
    CAPTION,
    FIGURE,
    GREEN,
    INK,
    MEDIUM,
    MUTED,
    RED,
    SHADE,
    Letterhead,
    Paper,
    money,
    period,
    print_twice,
    sentence,
    shade,
    table_options,
)
from baja.models import TransactionType

from .schemas import Statement

# Date, Description, Concept, Method, Expense, Income, Balance: the description
# takes what the others leave.
COLUMNS = (68, 0, 88, 62, 62, 62, 68)


def render_statement_pdf(
    statement: Statement, *, company: str, generated: dt.date
) -> bytes:
    letterhead = Letterhead(
        company=company,
        kind="Statement",
        title=statement.property_name,
        subtitle=period(statement.start, statement.end),
        generated=generated,
    )

    def lay_out(page_total: int | None) -> Paper:
        pdf = Paper(letterhead, page_total=page_total)
        pdf.add_page()
        pdf.head()
        _summary(pdf, statement)
        _entries(pdf, statement)
        return pdf

    return print_twice(lay_out)


def _summary(pdf: Paper, statement: Statement) -> None:
    """The balance's story in four figures: where it started, what moved it."""
    figures = (
        ("Previous balance", statement.opening_balance, True),
        ("Income", statement.income_total, False),
        ("Paid from balance", -statement.balance_expense_total, False),
        ("Ending balance", statement.closing_balance, True),
    )
    width = pdf.content_width / len(figures)
    top = pdf.get_y()
    pdf.set_fill_color(*SHADE)
    pdf.rect(pdf.l_margin, top, pdf.content_width, 46, style="F")
    for index, (label, amount, signed) in enumerate(figures):
        x = pdf.l_margin + index * width + 12
        pdf.set_xy(x, top + 8)
        pdf.style(CAPTION, color=MUTED)
        pdf.cell(width - 12, CAPTION + 2, f"{label} ({statement.currency})")
        pdf.set_xy(x, top + 21)
        pdf.style(FIGURE, MEDIUM, _sign_color(amount) if signed else INK)
        pdf.cell(width - 12, FIGURE + 4, money(amount))
    pdf.set_y(top + 54)
    if statement.exchange_rate is not None:
        pdf.style(CAPTION, color=MUTED)
        pdf.cell(
            0,
            CAPTION + 2,
            f"Converted at 1 USD = {statement.exchange_rate.normalize():f} MXN.",
        )
        pdf.ln(CAPTION + 6)
    pdf.ln(6)


def _entries(pdf: Paper, statement: Statement) -> None:
    pdf.style(BODY)
    if not statement.entries:
        pdf.style(BODY, color=MUTED)
        pdf.cell(0, BODY + 4, "Nothing was recorded in this period.")
        return
    with pdf.table(
        col_widths=_widths(pdf.content_width),
        text_align=("LEFT", "LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
        **table_options(),
    ) as table:
        table.row(
            ["Date", "Description", "Concept", "Method", "Expense", "Income", "Balance"]
        )
        for index, entry in enumerate(statement.entries):
            row = table.row(style=shade(index))
            row.cell(f"{entry.date:%b %-d, %Y}")
            row.cell(sentence(entry.description))
            row.cell(sentence(entry.concept))
            row.cell(sentence(entry.payment_method))
            row.cell(
                money(entry.amount) if entry.type == TransactionType.expense else ""
            )
            row.cell(
                money(entry.amount) if entry.type == TransactionType.income else ""
            )
            # Only the rows that moved the balance carry its colour.
            row.cell(
                money(entry.balance_after),
                style=shade(
                    index,
                    color=(
                        _sign_color(entry.balance_after)
                        if entry.affects_balance
                        else MUTED
                    ),
                ),
            )
        last = len(statement.entries)
        row = table.row(style=shade(last, bold=True))
        row.cell("Total", colspan=4)
        row.cell(money(statement.expense_total))
        row.cell(money(statement.income_total))
        row.cell(
            money(statement.closing_balance),
            style=shade(last, color=_sign_color(statement.closing_balance), bold=True),
        )


def _widths(content_width: float) -> tuple[float, ...]:
    fixed = sum(COLUMNS)
    return tuple(width or content_width - fixed for width in COLUMNS)


def _sign_color(amount: Decimal) -> tuple[int, int, int]:
    return RED if amount < 0 else GREEN
