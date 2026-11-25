import datetime as dt

from baja.kit.paper import (
    BODY,
    CAPTION,
    MUTED,
    Letterhead,
    Paper,
    money,
    period,
    print_twice,
    shade,
    table_options,
)

from .schemas import UtilitiesReport


def render_utilities_pdf(
    report: UtilitiesReport, *, company: str, generated: dt.date
) -> bytes:
    letterhead = Letterhead(
        company=company,
        kind="Utilities",
        title=report.property_name or "All properties",
        subtitle=period(report.start, report.end),
        generated=generated,
    )

    def lay_out(page_total: int | None) -> Paper:
        pdf = Paper(letterhead, orientation="landscape", page_total=page_total)
        pdf.add_page()
        pdf.head()
        _note(pdf, report)
        _table(pdf, report)
        return pdf

    return print_twice(lay_out)


def _note(pdf: Paper, report: UtilitiesReport) -> None:
    pdf.style(CAPTION, color=MUTED)
    note = f"Expenses by kind of bill, in {report.currency}."
    if report.exchange_rate is not None:
        note += f" Converted at 1 USD = {report.exchange_rate.normalize():f} MXN."
    pdf.cell(0, CAPTION + 2, note)
    pdf.ln(CAPTION + 10)


def _table(pdf: Paper, report: UtilitiesReport) -> None:
    # The total column is the widest figure: across all properties it runs
    # to eight digits.
    month_width = 60.0
    buckets = len(report.buckets)
    width = (pdf.content_width - month_width) / (buckets + 1.4)
    with pdf.table(
        col_widths=(month_width, *([width] * buckets), width * 1.4),
        text_align=("LEFT", *(["RIGHT"] * (buckets + 1))),
        **table_options(),
    ) as table:
        pdf.style(BODY)
        table.row(["Month", *(b.label for b in report.buckets), "Total"])
        for index, month in enumerate(report.months):
            year, number = (int(part) for part in month.month.split("-"))
            row = table.row(style=shade(index))
            row.cell(f"{dt.date(year, number, 1):%b %Y}")
            for bucket in report.buckets:
                cell = month.buckets[bucket.key]
                row.cell(money(cell.total) if cell.count else "")
            row.cell(money(month.total))
        total = table.row(style=shade(len(report.months), bold=True))
        total.cell("Total")
        for bucket in report.buckets:
            total.cell(money(report.totals[bucket.key].total))
        total.cell(money(report.grand_total))
