"""
The page every document Baja sends is printed on: A4, one typeface, a few sizes.

Documents differ in what is on the page, not in how the page is set.
"""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from fpdf import FPDF
from fpdf.enums import Align, TableBordersLayout
from fpdf.fonts import FontFace

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
LOGO = HERE / "logo.png"

MARGIN = 40.0
FOOT = 24.0

INK = (24, 24, 27)
MUTED = (113, 113, 122)
RULE = (228, 228, 231)
SHADE = (244, 244, 245)
GREEN = (21, 128, 61)
RED = (185, 28, 28)

CAPTION = 8.0
"""What a thing is: column heads, labels over figures, the foot."""
BODY = 9.0
"""The rows."""
FIGURE = 13.0
"""The sums above the rows."""
TITLE = 17.0
"""What the document is about: the property."""

REGULAR = ("Plex", "")
MEDIUM = ("Plex Medium", "")
BOLD = ("Plex", "B")


@dataclass(frozen=True)
class Letterhead:
    """What heads a document's first page and foots every page."""

    company: str
    kind: str
    """What the document is: "Statement"."""
    title: str
    """What it is about: the property."""
    subtitle: str
    """Which part of it: the period."""
    generated: dt.date


class Paper(FPDF):
    """An A4 page set in IBM Plex Sans, with nothing on it yet."""

    def __init__(
        self,
        letterhead: Letterhead,
        *,
        orientation: Literal["portrait", "landscape"] = "portrait",
        page_total: int | None = None,
    ) -> None:
        super().__init__(orientation=orientation, unit="pt", format="A4")
        self.letterhead = letterhead
        self.page_total = page_total
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN + FOOT)
        self.set_title(f"{letterhead.title} {letterhead.kind.lower()}")
        self.set_creator("Baja Luxury")
        self.set_lang("en")
        self.add_font("Plex", "", str(FONTS / "IBMPlexSans-Regular.ttf"))
        self.add_font("Plex", "B", str(FONTS / "IBMPlexSans-Bold.ttf"))
        self.add_font(MEDIUM[0], MEDIUM[1], str(FONTS / "IBMPlexSans-Medium.ttf"))

    def head(self) -> None:
        """The logo, what the document is and what about, on the first page."""
        letterhead = self.letterhead
        top = self.get_y()
        self.image(str(LOGO), x=self.l_margin, y=top - 4, h=48)
        self.set_xy(self.l_margin + 52, top)
        self.style(CAPTION, color=MUTED)
        self.cell(0, CAPTION + 2, f"{letterhead.company} · {letterhead.kind}")
        self.set_xy(self.l_margin + 52, top + 12)
        self.style(TITLE, BOLD)
        self.cell(0, TITLE + 4, letterhead.title)
        self.set_xy(self.l_margin + 52, top + 33)
        self.style(BODY, color=MUTED)
        self.cell(0, BODY + 2, letterhead.subtitle)
        self.set_xy(self.l_margin, top)
        self.style(CAPTION, color=MUTED)
        self.cell(
            0,
            CAPTION + 2,
            f"Generated {letterhead.generated:%b %-d, %Y}",
            align=Align.R,
        )
        self.set_y(top + 64)

    def footer(self) -> None:
        self.set_y(-self.b_margin + 8)
        self.style(CAPTION, color=MUTED)
        self.cell(
            0,
            CAPTION,
            f"{self.letterhead.title} · {self.letterhead.subtitle}",
            align=Align.L,
        )
        self.set_x(self.l_margin)
        total = f" of {self.page_total}" if self.page_total else ""
        self.cell(0, CAPTION, f"Page {self.page_no()}{total}", align=Align.R)

    @property
    def content_width(self) -> float:
        return float(self.w - self.l_margin - self.r_margin)

    def style(
        self,
        size: float,
        weight: tuple[str, str] = REGULAR,
        color: tuple[int, int, int] = INK,
    ) -> None:
        self.set_font(weight[0], weight[1], size)
        self.set_text_color(*color)

    def rule(self, color: tuple[int, int, int] = RULE) -> None:
        self.set_draw_color(*color)
        self.set_line_width(0.75)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())


def money(amount: Decimal) -> str:
    """`-1,234.50`: the sign first, two decimals, thousands grouped."""
    return f"{amount:,.2f}"


def sentence(text: str | None) -> str:
    """Stored lowercase; shown with a capital, like a sentence."""
    return text[:1].upper() + text[1:] if text else ""


def period(start: dt.date, end: dt.date) -> str:
    return f"{start:%b %-d, %Y} – {end:%b %-d, %Y}"


def print_twice(lay_out: Callable[[int | None], Paper]) -> bytes:
    """
    The document, laid out twice: the first time to learn how many pages
    "of N" is, as fpdf2's page count alias is measured before it is filled in.
    """
    pages = lay_out(None).pages_count
    return bytes(lay_out(pages).output())


def table_options() -> dict[str, Any]:
    """
    How every table is set: heads in small bold grey, rows shaded in turn
    (see `shade`).

    Shading rather than rules: fpdf2 draws a rule per cell, and where two
    meet they leave a visible bump.
    """
    return {
        "headings_style": FontFace(
            family="Plex",
            emphasis="BOLD",
            size_pt=CAPTION,
            color=MUTED,
            fill_color=(255, 255, 255),
        ),
        "borders_layout": TableBordersLayout.NONE,
        "line_height": BODY + 3,
        "padding": (5, 4, 5, 4),
        "repeat_headings": 1,
    }


def shade(
    row: int,
    *,
    color: tuple[int, int, int] | None = None,
    bold: bool = False,
) -> FontFace:
    """
    The face for a cell in body row `row`: every other row shaded.

    Given per row and per styled cell, as fpdf2's own row shading loses step
    when one cell has a style of its own.
    """
    return FontFace(
        family="Plex",
        emphasis="BOLD" if bold else None,
        color=color,
        # White, not None: fpdf2 keeps the last fill for a cell without one.
        fill_color=SHADE if row % 2 else (255, 255, 255),
    )
