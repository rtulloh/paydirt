"""AUD-032: clock traces use the same truncation as the game clock."""

import pytest

from paydirt.game_state import ClockTrace
from paydirt.utils import format_time


def trace(start: float, end: float, *, end_quarter: int = 3) -> ClockTrace:
    return ClockTrace(
        start_quarter=3,
        start_seconds=start,
        end_quarter=end_quarter,
        end_seconds=end,
        requested_seconds=start - end,
        charged_seconds=start - end,
        period_ended=False,
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (403.829, "6:43"),
        (852.786, "14:12"),
        (779.624, "12:59"),
        (364.050, "6:04"),
    ],
)
def test_trace_endpoints_use_truncated_clock_seconds(seconds: float, expected: str) -> None:
    description = trace(907.0, seconds).description
    assert f"Q3 {expected} ({seconds:.3f}s)" in description
    assert format_time(seconds / 60) == expected


def test_period_boundary_end_renders_fifteen_minutes_not_fourteen_sixty() -> None:
    description = trace(905.0, 900.0, end_quarter=4).description
    assert "Q4 15:00 (900.000s)" in description
    assert "14:60" not in description


def test_rounding_is_not_used_for_either_endpoint() -> None:
    description = trace(403.829, 779.624).description
    assert "Q3 6:44" not in description
    assert "Q3 13:00" not in description
