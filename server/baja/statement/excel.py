import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from baja.kit.paper import sentence
from baja.models import TransactionType

from .schemas import Statement

AMOUNT = "#,##0.00;[Red]-#,##0.00"
DATE = "mmm d, yyyy"
HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", start_color="27272A")
BOLD = Font(bold=True)
LINE = Border(bottom=Side(style="thin", color="E4E4E7"))
COLUMNS = (
    ("Date", 14),
    ("Description", 44),
    ("Concept", 26),
    ("Method", 14),
    ("Expense", 14),
    ("Income", 14),
    ("Balance", 16),
)


def render_statement_excel(statement: Statement, *, company: str) -> bytes:
    """
    The statement as a sheet to work with: real dates and numbers, so it sums
    and sorts, laid out like the PDF.
    """
    workbook = Workbook()
    sheet = workbook.active
    assert isinstance(sheet, Worksheet)
    sheet.title = "Statement"

    sheet.append([company])
    sheet["A1"].font = Font(bold=True, size=14)
    for label, value in (
        ("Property", statement.property_name),
        ("From", statement.start),
        ("To", statement.end),
        ("Currency", str(statement.currency)),
        ("Previous balance", statement.opening_balance),
        ("Ending balance", statement.closing_balance),
    ):
        sheet.append([label, value])
        sheet.cell(sheet.max_row, 1).font = BOLD
        sheet.cell(sheet.max_row, 2).alignment = Alignment(horizontal="left")
        sheet.cell(sheet.max_row, 2).number_format = (
            DATE if label in {"From", "To"} else AMOUNT
        )
    if statement.exchange_rate is not None:
        sheet.append(["Exchange rate", f"1 USD = {statement.exchange_rate} MXN"])
        sheet.cell(sheet.max_row, 1).font = BOLD
    sheet.append([])

    sheet.append([name for name, _ in COLUMNS])
    head = sheet.max_row
    for index, (_, width) in enumerate(COLUMNS, start=1):
        cell = sheet.cell(head, index)
        cell.font, cell.fill = HEAD, HEAD_FILL
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.freeze_panes = f"A{head + 1}"  # by name: `sheet.cell` would add a row

    for entry in statement.entries:
        is_expense = entry.type == TransactionType.expense
        sheet.append(
            [
                entry.date,
                sentence(entry.description),
                sentence(entry.concept),
                sentence(entry.payment_method),
                entry.amount if is_expense else None,
                None if is_expense else entry.amount,
                entry.balance_after,
            ]
        )
        _format_row(sheet, sheet.max_row)

    sheet.append(
        [
            "Total",
            None,
            None,
            None,
            statement.expense_total,
            statement.income_total,
            statement.closing_balance,
        ]
    )
    _format_row(sheet, sheet.max_row)
    for index in range(1, len(COLUMNS) + 1):
        sheet.cell(sheet.max_row, index).font = BOLD

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _format_row(sheet: Worksheet, row: int) -> None:
    sheet.cell(row, 1).number_format = DATE
    for column in (5, 6, 7):
        sheet.cell(row, column).number_format = AMOUNT
    for column in range(1, len(COLUMNS) + 1):
        sheet.cell(row, column).border = LINE
