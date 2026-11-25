import datetime as dt

import pytest

from baja.recurring.dates import due_dates, next_due

D = dt.date


@pytest.mark.parametrize(
    ("day", "after", "through", "expected"),
    [
        (10, D(2026, 11, 9), D(2026, 11, 10), [D(2026, 11, 10)]),
        (10, D(2026, 11, 10), D(2026, 11, 30), []),
        (
            15,
            D(2026, 10, 20),
            D(2027, 1, 15),
            [D(2026, 11, 15), D(2026, 12, 15), D(2027, 1, 15)],
        ),
        (31, D(2027, 1, 31), D(2027, 3, 31), [D(2027, 2, 28), D(2027, 3, 31)]),
        (30, D(2028, 1, 31), D(2028, 2, 29), [D(2028, 2, 29)]),
        (5, D(2026, 11, 30), D(2026, 11, 30), []),
    ],
)
def test_due_dates(
    day: int, after: dt.date, through: dt.date, expected: list[dt.date]
) -> None:
    assert due_dates(day, after, through) == expected


@pytest.mark.parametrize(
    ("day", "after", "expected"),
    [
        (15, D(2026, 11, 14), D(2026, 11, 15)),
        (15, D(2026, 11, 15), D(2026, 12, 15)),
        (31, D(2026, 12, 31), D(2027, 1, 31)),
        (31, D(2027, 1, 31), D(2027, 2, 28)),
    ],
)
def test_next_due(day: int, after: dt.date, expected: dt.date) -> None:
    assert next_due(day, after) == expected
