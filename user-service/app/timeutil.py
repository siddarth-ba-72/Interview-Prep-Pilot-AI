from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def utc_now() -> datetime:
    """Timezone-aware UTC now, truncated to milliseconds (BSON dates have millisecond precision)."""
    now = datetime.now(UTC)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def to_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC; convert aware ones to UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def parse_instant(text: str) -> datetime:
    """Parse an ISO-8601 instant (a trailing Z is accepted); naive values are taken as UTC. Raises ValueError."""
    return to_utc(datetime.fromisoformat(text))


def format_instant(value: datetime) -> str:
    """ISO-8601 UTC with millisecond precision and a Z suffix, e.g. 2026-10-05T09:14:03.120Z."""
    value = to_utc(value)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


UtcDateTime = Annotated[datetime, PlainSerializer(format_instant, return_type=str)]
