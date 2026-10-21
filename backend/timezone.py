from datetime import date, datetime
from datetime import timedelta, timezone

# Colombia stays at UTC-5 year-round; this fixed offset also works on Windows
# installations that do not have an IANA timezone database installed.
BOGOTA_TIMEZONE = timezone(timedelta(hours=-5), name='America/Bogota')


def bogota_now() -> datetime:
    """Return the current Bogotá wall time as a naive datetime for MySQL DATETIME."""
    return datetime.now(BOGOTA_TIMEZONE).replace(tzinfo=None)


def bogota_today() -> date:
    """Return today's date in the application's business timezone."""
    return datetime.now(BOGOTA_TIMEZONE).date()
