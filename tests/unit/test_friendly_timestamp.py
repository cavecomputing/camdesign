from __future__ import annotations

from datetime import timedelta, timezone

from camdesign import friendly_timestamp


def test_formats_utc_timestamp_in_target_zone() -> None:
    result = friendly_timestamp("2026-08-13 20:53:44", tz=timezone(timedelta(hours=-4)))

    assert result == "13 Aug 2026, 4:53 PM"


def test_rolls_back_across_midnight_into_previous_day() -> None:
    result = friendly_timestamp("2026-01-01 01:15:00", tz=timezone(timedelta(hours=-5)))

    assert result == "31 Dec 2025, 8:15 PM"


def test_passes_through_values_it_cannot_parse() -> None:
    assert friendly_timestamp("sometime soon") == "sometime soon"
    assert friendly_timestamp(None) == ""
