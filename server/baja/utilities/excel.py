import datetime as dt
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from .schemas import UtilitiesReport

AMOUNT = "#,##0.00"
BOLD = Font(bold=True)


def render_utilities_excel(report: UtilitiesReport, *, company: str) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert isinstance(sheet, Worksheet)
    sheet.title = "Utilities"
    sheet.append([company])
    sheet["A1"].font = Font(bold=True, size=14)
    for label, value in (
        ("Property", report.property_name or "All properties"),
        ("From", report.start),
        ("To", report.end),
        ("Currency", str(report.currency)),
    ):
        sheet.append([label, value])
        sheet.cell(sheet.max_row, 1).font = BOLD
        if isinstance(value, dt.date):
            sheet.cell(sheet.max_row, 2).number_format = "mmm d, yyyy"
    if report.exchange_rate is not None:
        sheet.append(["Exchange rate", f"1 USD = {report.exchange_rate} MXN"])
    sheet.append([])

    sheet.append(["Month", *(b.label for b in report.buckets), "Total"])
    head = sheet.max_row
    for column in range(1, len(report.buckets) + 3):
        cell = sheet.cell(head, column)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", start_color="27272A")
        sheet.column_dimensions[cell.column_letter].width = 15
    for month in report.months:
        year, number = (int(part) for part in month.month.split("-"))
        sheet.append(
            [
                dt.date(year, number, 1),
                *(month.buckets[b.key].total for b in report.buckets),
                month.total,
            ]
        )
        sheet.cell(sheet.max_row, 1).number_format = "mmm yyyy"
        _amounts(sheet, len(report.buckets))
    sheet.append(
        [
            "Total",
            *(report.totals[b.key].total for b in report.buckets),
            report.grand_total,
        ]
    )
    _amounts(sheet, len(report.buckets))
    for column in range(1, len(report.buckets) + 3):
        sheet.cell(sheet.max_row, column).font = BOLD

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _amounts(sheet: Worksheet, buckets: int) -> None:
    for column in range(2, buckets + 3):
        sheet.cell(sheet.max_row, column).number_format = AMOUNT
