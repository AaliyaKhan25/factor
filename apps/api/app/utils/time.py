"""Time helpers."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC now.

    Every timestamp is stored as naive UTC so SQLite (tests) and Postgres behave the same.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
