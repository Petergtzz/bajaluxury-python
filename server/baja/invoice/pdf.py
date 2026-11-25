from decimal import ROUND_HALF_UP, Decimal

from baja.kit.paper import (
    BODY,
    BOLD,
    CAPTION,
    FIGURE,
    INK,
    MEDIUM,
    MUTED,
    REGULAR,
    Letterhead,
    Paper,
    money,
    print_twice,
    shade,
    table_options,
)
from baja.models import Invoice

CENT = Decimal("0.01")


def render_invoice_pdf(invoice: Invoice, *, company: str, property_name: str) -> bytes:
    letterhead = Letterhead(
        company=company,
        kind="Invoice",
        title=invoice.number,
        subtitle=property_name,
        generated=invoice.issued_on,
        date_label="Issued",
    )

    def lay_out(page_total: int | None) -> Paper:
        pdf = Paper(letterhead, page_total=page_total)
        pdf.add_page()
        pdf.head()
        _parties(pdf, invoice, property_name)
        _lines(pdf, invoice)
        _totals(pdf, invoice)
        _remarks(pdf, invoice)
        return pdf

    return print_twice(lay_out)


def _usd(invoice: Invoice, amount: Decimal) -> Decimal:
    return (amount / invoice.exchange_rate).quantize(CENT, ROUND_HALF_UP)


def _parties(pdf: Paper, invoice: Invoice, property_name: str) -> None:
    """Who pays, for what, and by when."""
    columns = (
        ("Bill to", [invoice.recipient_name, invoice.email]),
        ("Property", [property_name]),
        (
            "Dates",
            # The due date first, and bold: it is what the guest acts on.
            [
                f"Due {invoice.due_on:%b %-d, %Y}",
                f"Issued {invoice.issued_on:%b %-d, %Y}",
            ],
        ),
    )
    width = pdf.content_width / len(columns)
    top = pdf.get_y()
    bottom = top
    for index, (label, lines) in enumerate(columns):
        x = pdf.l_margin + index * width
        pdf.set_xy(x, top)
        pdf.style(CAPTION, BOLD, MUTED)
        pdf.cell(width - 12, CAPTION + 4, label)
        pdf.set_xy(x, top + CAPTION + 6)
        for number, line in enumerate(lines):
            pdf.style(BODY, BOLD if number == 0 else REGULAR)
            pdf.set_x(x)
            pdf.multi_cell(width - 12, BODY + 4, line)
        bottom = max(bottom, pdf.get_y())
    pdf.set_y(bottom + 18)


def _lines(pdf: Paper, invoice: Invoice) -> None:
    figures = (44.0, 84.0, 84.0, 74.0)
    with pdf.table(
        col_widths=(pdf.content_width - sum(figures), *figures),
        text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
        **table_options(),
    ) as table:
        pdf.style(BODY)
        table.row(["Item", "Qty", "Unit price", "Amount (MXN)", "USD"])
        for index, line in enumerate(invoice.lines):
            row = table.row(style=shade(index))
            row.cell(line.description)
            row.cell(f"{line.quantity.normalize():f}")
            row.cell(money(line.unit_price))
            row.cell(money(line.amount))
            row.cell(money(_usd(invoice, line.amount)), style=shade(index, color=MUTED))


def _totals(pdf: Paper, invoice: Invoice) -> None:
    """Subtotal, VAT and total, in both currencies, at the right."""
    rows = (
        ("Subtotal", invoice.subtotal, False),
        (f"VAT ({(invoice.tax_rate * 100).normalize():f}%)", invoice.tax, False),
        ("Total", invoice.total, True),
    )
    label_width, figure_width = 110.0, 84.0
    x = pdf.l_margin + pdf.content_width - label_width - 2 * figure_width
    pdf.ln(10)
    pdf.set_x(x + label_width)
    pdf.style(CAPTION, BOLD, MUTED)
    pdf.cell(figure_width, CAPTION + 4, "MXN", align="R")
    pdf.cell(figure_width, CAPTION + 4, "USD", align="R")
    pdf.ln(CAPTION + 6)
    for label, amount, last in rows:
        if last:
            pdf.set_draw_color(*MUTED)
            pdf.line(x, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
            pdf.ln(6)
        size = FIGURE if last else BODY
        pdf.set_x(x)
        pdf.style(size, BOLD if last else REGULAR, INK if last else MUTED)
        pdf.cell(label_width, size + 6, label)
        pdf.style(size, BOLD if last else MEDIUM)
        pdf.cell(figure_width, size + 6, money(amount), align="R")
        pdf.style(size, BOLD if last else MEDIUM, MUTED)
        pdf.cell(figure_width, size + 6, money(_usd(invoice, amount)), align="R")
        pdf.ln(size + 6)
    pdf.style(CAPTION, color=MUTED)
    pdf.set_x(x)
    pdf.cell(
        label_width + 2 * figure_width,
        CAPTION + 6,
        f"At 1 USD = {invoice.exchange_rate.normalize():f} MXN",
        align="R",
    )
    pdf.ln(CAPTION + 18)


def _remarks(pdf: Paper, invoice: Invoice) -> None:
    for label, text in (
        ("Payment details", invoice.payment_details),
        ("Notes", invoice.notes),
    ):
        if not text:
            continue
        pdf.style(CAPTION, BOLD, MUTED)
        pdf.cell(0, CAPTION + 4, label)
        pdf.ln(CAPTION + 6)
        pdf.style(BODY)
        pdf.multi_cell(0, BODY + 5, text)
        pdf.ln(10)
