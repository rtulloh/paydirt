"""A diagnostic can hold measured range pairs while source counts are repaired."""

from pathlib import Path

import pytest

from paydirt.chart_generator import generate_team_charts
from paydirt.chart_loader import load_team_chart
from tests.test_chart_generator import _synthetic_stats


@pytest.mark.parametrize("ranges", [((10, 35), (36, 39)), ((0, 0), (10, 39)), ((10, 39), (0, 0))])
def test_explicit_diagnostic_ranges_change_only_peripheral_ranges(tmp_path: Path, ranges: tuple) -> None:
    stats = _synthetic_stats()
    baseline = generate_team_charts(stats, tmp_path / "baseline", seed=8306)
    diagnostic = generate_team_charts(stats, tmp_path / "diagnostic", seed=8306,
                                      fumble_range_override=ranges)
    loaded = load_team_chart(tmp_path / "diagnostic")
    assert loaded.peripheral.fumble_recovered_range == ranges[0]
    assert loaded.peripheral.fumble_lost_range == ranges[1]
    assert diagnostic.offense == baseline.offense
    assert diagnostic.defense == baseline.defense
    assert diagnostic.special_teams == baseline.special_teams
    assert diagnostic.primary_layout == baseline.primary_layout


@pytest.mark.parametrize("ranges", [
    ((10, 30), (30, 39)), ((10, 28), (30, 39)), ((11, 29), (30, 39)),
    ((10, 40), (0, 0)), ((False, False), (10, 39)), ((10, 30),),
    [[10, 30], [31, 39]], ((10, 30), ("31", 39)),
])
def test_invalid_diagnostic_ranges_fail_before_chart_write(tmp_path: Path, ranges: tuple) -> None:
    with pytest.raises(ValueError):
        generate_team_charts(_synthetic_stats(), tmp_path / "invalid",
                             fumble_range_override=ranges)
    assert not list((tmp_path / "invalid").glob("*.csv"))
