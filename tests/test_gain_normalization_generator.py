"""Synthetic generator integration for the fixed gain transformation."""
from collections import Counter
from pathlib import Path

import pytest

from paydirt.chart_generator import TeamSeasonStats, generate_team_charts
from paydirt.gain_normalization import transform_offense_gains
from paydirt.play_resolver import chart_roll_weights


def synthetic_stats() -> TeamSeasonStats:
    return TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Synthetic", "short_name": "SYN",
        "offense": {
            "rushing": {"attempts": 400, "yards": 1800, "fumbles": 8, "fumbles_lost": 3},
            "passing": {"attempts": 500, "completions": 320, "yards": 3600,
                        "interceptions": 12, "sacks": 30, "sack_yards": 180,
                        "fumbles": 5, "fumbles_lost": 2},
        },
        "defense": {"rushing": {"attempts": 400, "yards": 1600},
                    "passing": {"attempts": 500, "completions": 300, "yards": 3400}},
    })


def weighted(column: dict[int, str]) -> Counter:
    counts = Counter()
    for row, token in column.items():
        counts[token] += chart_roll_weights()[row]
    return counts


def test_default_generation_remains_deterministic(tmp_path: Path) -> None:
    first = generate_team_charts(synthetic_stats(), tmp_path / "first")
    second = generate_team_charts(synthetic_stats(), tmp_path / "second")
    assert first == second
    for path in (tmp_path / "first").iterdir():
        assert path.read_bytes() == (tmp_path / "second" / path.name).read_bytes()


@pytest.mark.parametrize("passing,rushing", [(1.1, .9), (.8, 1.25), (1.0, 1.0)])
def test_generator_applies_gains_once_before_final_layout(
    tmp_path: Path, passing: float, rushing: float,
) -> None:
    original = generate_team_charts(synthetic_stats(), tmp_path / "original")
    expected, _ = transform_offense_gains(
        original.offense, passing_multiplier=passing, rushing_multiplier=rushing)
    generated = generate_team_charts(
        synthetic_stats(), tmp_path / "normalized",
        gain_multipliers=(passing, rushing))
    assert {name: weighted(column) for name, column in generated.offense.items()} == {
        name: weighted(column) for name, column in expected.items()}
    assert generated.defense == original.defense
    assert generated.special_teams == original.special_teams
    assert generated.gain_normalization["protected_mass_preserved"] is True
    assert generated.primary_layout["invariants_passed"] is True
    for filename in ("defense.csv", "special.csv", "team.yaml"):
        assert (tmp_path / "original" / filename).read_bytes() == (
            tmp_path / "normalized" / filename).read_bytes()
    assert (tmp_path / "original/offense.csv").read_text().splitlines()[-2:] == (
        tmp_path / "normalized/offense.csv").read_text().splitlines()[-2:]


@pytest.mark.parametrize("multipliers", [(True, 1.0), (1.0, 1.251), (.79, 1.0)])
def test_generator_rejects_invalid_gain_factors(tmp_path: Path, multipliers: tuple) -> None:
    with pytest.raises(ValueError, match="Gain multiplier"):
        generate_team_charts(synthetic_stats(), tmp_path, gain_multipliers=multipliers)
