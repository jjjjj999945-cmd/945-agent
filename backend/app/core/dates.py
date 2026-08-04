import os
from datetime import date


def app_date() -> str:
    """Return the current product date, with an explicit test override."""
    return os.getenv("945_REFERENCE_DATE", date.today().isoformat())
