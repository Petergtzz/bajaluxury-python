from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

environment = Environment(
    loader=PackageLoader("baja.email", "templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def render_email(template: str, **context: Any) -> tuple[str, str]:
    """The HTML and plain text bodies of one email."""
    html = environment.get_template(f"{template}.html").render(**context)
    text = environment.get_template(f"{template}.txt").render(**context)
    return html, text
