from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


def start_of_day(d: date) -> datetime:
    """Medianoche al inicio del día en zona horaria argentina."""
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=TZ_AR)


def end_of_day(d: date) -> datetime:
    """Último microsegundo del día en zona horaria argentina."""
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=TZ_AR)
