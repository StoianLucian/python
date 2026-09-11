from datetime import date, timedelta


def iter_days(start: date, end: date):
    """Yield each date in the inclusive range [start, end]."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
