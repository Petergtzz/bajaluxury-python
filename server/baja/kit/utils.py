import uuid
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> uuid.UUID:
    """Time-ordered, so new rows land at the end of the primary key index."""
    return uuid.uuid7()
