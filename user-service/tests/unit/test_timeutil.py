from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.timeutil import format_instant, parse_instant, utc_now


def test_utc_now_is_aware_and_millisecond_truncated():
    now = utc_now()
    assert now.tzinfo is not None and now.utcoffset() == timedelta(0)
    assert now.microsecond % 1000 == 0


def test_format_instant_uses_z_and_milliseconds():
    assert format_instant(datetime(2026, 10, 5, 9, 14, 3, 120000, tzinfo=UTC)) == "2026-10-05T09:14:03.120Z"
    assert format_instant(datetime(2026, 10, 5, 9, 14, 3, tzinfo=UTC)) == "2026-10-05T09:14:03.000Z"


def test_format_instant_converts_offsets_and_treats_naive_as_utc():
    plus_two = timezone(timedelta(hours=2))
    assert format_instant(datetime(2026, 10, 5, 11, 0, tzinfo=plus_two)) == "2026-10-05T09:00:00.000Z"
    assert format_instant(datetime(2026, 10, 5, 9, 0)) == "2026-10-05T09:00:00.000Z"


def test_parse_instant_accepts_z_and_naive():
    assert parse_instant("2026-10-05T09:14:03.120Z") == datetime(2026, 10, 5, 9, 14, 3, 120000, tzinfo=UTC)
    assert parse_instant("2026-10-05T09:14:03") == datetime(2026, 10, 5, 9, 14, 3, tzinfo=UTC)


def test_parse_instant_rejects_garbage():
    with pytest.raises(ValueError):
        parse_instant("yesterday")
