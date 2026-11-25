import datetime as dt
from decimal import Decimal

from fpdf.enums import Align, TableBordersLayout
from fpdf.fonts import FontFace

from baja.kit.paper import (
    BODY,
    BOLD,
    CAPTION,
    FIGURE,
    GREEN,
    INK,
    LOGO,
    MEDIUM,
    MUTED,
    RED,
    SHADE,
    TITLE,
    Paper,
    money,
    sentence,
)
from baja.models import TransactionType

from .schemas import Statement

# Date, Description, Concept, Method, Expense, Income, Balance: the description
# takes what the others leave.
COLUMNS = (68, 0, 88, 62, 62, 62, 68)


class StatementPaper(Paper):
    def __init__(
        self,
        statement: Statement,
        *,
        company: str,
        generated: dt.date,
        pages: int | None,
    ) -> None:
        super().__init__(f"{statement.property_name} statement")
        self.statement = statement
        self.company = company
        self.generated = generated
        self.page_total = pages

    def footer(self) -> None:
        self.set_y(-self.b_margin + 8)
        self.style(CAPTION, color=MUTED)
        self.cell(
            0,
            CAPTION,
            f"{self.statement.property_name} · {_period(self.statement)}",
            align=Align.L,
        )
        self.set_x(self.l_margin)
        total = f" of {self.page_total}" if self.page_total else ""
        self.cell(0, CAPTION, f"Page {self.page_no()}{total}", align=Align.R)


def render_statement_pdf(
    statement: Statement, *, company: str, generated: dt.date
) -> bytes:
    # Laid out twice: the first time to learn how many pages "of N" is, as
    # fpdf2's page count alias is measured before it is filled in.
    pages = None
    for _ in range(2):
        pdf = StatementPaper(
            statement, company=company, generated=generated, pages=pages
        )
        pdf.add_page()
        _head(pdf)
        _summary(pdf)
        _entries(pdf)
        pages = pdf.pages_count
    return bytes(pdf.output())


def _head(pdf: StatementPaper) -> None:
    top = pdf.get_y()
    pdf.image(str(LOGO), x=pdf.l_margin, y=top - 4, h=48)
    pdf.set_xy(pdf.l_margin + 52, top)
    pdf.style(CAPTION, color=MUTED)
    pdf.cell(0, CAPTION + 2, f"{pdf.company} · Statement")
    pdf.set_xy(pdf.l_margin + 52, top + 12)
    pdf.style(TITLE, BOLD)
    pdf.cell(0, TITLE + 4, pdf.statement.property_name)
    pdf.set_xy(pdf.l_margin + 52, top + 33)
    pdf.style(BODY, color=MUTED)
    pdf.cell(0, BODY + 2, _period(pdf.statement))
    pdf.set_xy(pdf.l_margin, top)
    pdf.style(CAPTION, color=MUTED)
    pdf.cell(0, CAPTION + 2, f"Generated {pdf.generated:%b %-d, %Y}", align=Align.R)
    pdf.set_y(top + 64)


def _summary(pdf: StatementPaper) -> None:
    """The balance's story in four figures: where it started, what moved it."""
    statement = pdf.statement
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


def _entries(pdf: StatementPaper) -> None:
    statement = pdf.statement
    pdf.style(BODY)
    if not statement.entries:
        pdf.style(BODY, color=MUTED)
        pdf.cell(0, BODY + 4, "Nothing was recorded in this period.")
        return
    head = FontFace(family="Plex", emphasis="BOLD", size_pt=CAPTION, color=MUTED)
    with pdf.table(
        col_widths=_widths(pdf.content_width),
        text_align=("LEFT", "LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
        headings_style=head,
        borders_layout=TableBordersLayout.HORIZONTAL_LINES,
        line_height=BODY + 3,
        padding=(4, 3, 4, 3),
        repeat_headings=1,
        first_row_as_headings=True,
    ) as table:
        table.row(
            ["Date", "Description", "Concept", "Method", "Expense", "Income", "Balance"]
        )
        for entry in statement.entries:
            row = table.row()
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
                style=FontFace(
                    color=(
                        _sign_color(entry.balance_after)
                        if entry.affects_balance
                        else MUTED
                    )
                ),
            )
        total = FontFace(family="Plex", emphasis="BOLD", size_pt=BODY)
        row = table.row(style=total)
        row.cell("Total", colspan=4)
        row.cell(money(statement.expense_total))
        row.cell(money(statement.income_total))
        row.cell(
            money(statement.closing_balance),
            style=FontFace(
                family="Plex",
                emphasis="BOLD",
                color=_sign_color(statement.closing_balance),
            ),
        )


def _widths(content_width: float) -> tuple[float, ...]:
    fixed = sum(COLUMNS)
    return tuple(width or content_width - fixed for width in COLUMNS)


def _sign_color(amount: Decimal) -> tuple[int, int, int]:
    return RED if amount < 0 else GREEN


def _period(statement: Statement) -> str:
    return f"{statement.start:%b %-d, %Y} – {statement.end:%b %-d, %Y}"
