"""
The page every document Baja sends is printed on: A4, one typeface, a few sizes.

Documents differ in what is on the page, not in how the page is set.
"""

from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

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


class Paper(FPDF):
    """An A4 page set in IBM Plex Sans, with nothing on it yet."""

    def __init__(self, title: str, *, orientation: str = "portrait") -> None:
        super().__init__(orientation=orientation, unit="pt", format="A4")
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN + FOOT)
        self.set_title(title)
        self.set_creator("Baja Luxury")
        self.set_lang("en")
        self.add_font("Plex", "", str(FONTS / "IBMPlexSans-Regular.ttf"))
        self.add_font("Plex", "B", str(FONTS / "IBMPlexSans-Bold.ttf"))
        self.add_font(MEDIUM[0], MEDIUM[1], str(FONTS / "IBMPlexSans-Medium.ttf"))

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
