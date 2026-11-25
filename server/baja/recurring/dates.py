import datetime as dt
from calendar import monthrange


def due_on(day_of_month: int, year: int, month: int) -> dt.date:
    """The charge's day in that month, or its last day if the month is shorter."""
    return dt.date(year, month, min(day_of_month, monthrange(year, month)[1]))


def due_dates(day_of_month: int, after: dt.date, through: dt.date) -> list[dt.date]:
    """Every day the charge falls due after `after`, up to and including `through`."""
    dates = []
    year, month = after.year, after.month
    while (year, month) <= (through.year, through.month):
        due = due_on(day_of_month, year, month)
        if after < due <= through:
            dates.append(due)
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    return dates


def next_due(day_of_month: int, after: dt.date) -> dt.date:
    this_month = due_on(day_of_month, after.year, after.month)
    if this_month > after:
        return this_month
    year, month = (
        (after.year, after.month + 1) if after.month < 12 else (after.year + 1, 1)
    )
    return due_on(day_of_month, year, month)
