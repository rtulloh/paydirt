"""Tests for separating offense and defense effects in empirical chart data."""

from __future__ import annotations

from statistics import mean

import pytest

from paydirt.chart_generator import TeamSeasonStats
from paydirt.empirical_adjustment import (
    DefenseProfile,
    adjust_empirical_offense,
    calibrate_defense_stats,
    fit_additive_effects,
)
from paydirt.pfr_play_by_play import EmpiricalPlay


def _play(
    team: str,
    opponent: str,
    result: str,
    number: int,
    chart: str = "line_plunge",
) -> EmpiricalPlay:
    """Build one synthetic matched play without historical season data."""
    return EmpiricalPlay(
        team=team,
        unit="offense",
        chart=chart,
        result=result,
        game_id="synthetic",
        play_number=number,
        detail=f"synthetic result {result}",
        opponent=opponent,
    )


def _numeric_mean(plays: tuple[EmpiricalPlay, ...]) -> float:
    """Return the mean of numeric results in an adjusted synthetic sample."""
    return mean(int(play.result.rstrip("*†")) for play in plays)


def test_additive_model_recovers_balanced_offense_and_defense_effects() -> None:
    observations = (
        ("strong_offense", "weak_defense", 8.0),
        ("strong_offense", "strong_defense", 4.0),
        ("weak_offense", "weak_defense", 4.0),
        ("weak_offense", "strong_defense", 0.0),
    )

    model = fit_additive_effects(observations, shrinkage=0.0)

    assert model.baseline == pytest.approx(4.0)
    assert model.offense_effects == pytest.approx(
        {"strong_offense": 2.0, "weak_offense": -2.0}
    )
    assert model.defense_effects == pytest.approx(
        {"weak_defense": 2.0, "strong_defense": -2.0}
    )
    assert model.predict("strong_offense") == pytest.approx(6.0)
    assert model.predict("weak_offense") == pytest.approx(2.0)


def test_empirical_adjustment_translates_results_to_average_defense() -> None:
    plays = (
        _play("strong_offense", "weak_defense", "8", 1),
        _play("strong_offense", "strong_defense", "4", 2),
        _play("weak_offense", "weak_defense", "4", 3),
        _play("weak_offense", "strong_defense", "0", 4),
    )

    adjusted = adjust_empirical_offense(plays, shrinkage=0.0)

    assert _numeric_mean(adjusted.plays_by_team["strong_offense"]) == 6.0
    assert _numeric_mean(adjusted.plays_by_team["weak_offense"]) == 2.0
    assert adjusted.defense_profiles["weak_defense"].rushing_yards_per_attempt > 4.0
    assert adjusted.defense_profiles["strong_defense"].rushing_yards_per_attempt < 4.0


def test_defense_profile_replaces_schedule_biased_defense_rates() -> None:
    stats = TeamSeasonStats.from_dict(
        {
            "season": 2026,
            "team_name": "Foxes",
            "short_name": "FOX",
            "offense": {
                "rushing": {"attempts": 100, "yards": 400},
                "passing": {"attempts": 100, "completions": 60, "yards": 700},
            },
            "defense": {
                "rushing": {"attempts": 200, "yards": 1000},
                "passing": {
                    "attempts": 300,
                    "completions": 210,
                    "yards": 2400,
                    "interceptions": 3,
                    "sacks": 6,
                    "sack_yards": 42,
                },
            },
        }
    )
    profile = DefenseProfile(
        rushing_yards_per_attempt=3.5,
        passing_yards_per_attempt=6.4,
        completion_rate=0.55,
        interception_rate=0.04,
        sack_rate=0.08,
    )

    calibrated = calibrate_defense_stats(stats, profile)

    assert calibrated.defense.rushing.attempts == 200
    assert calibrated.defense.rushing.yards == 700
    assert calibrated.defense.passing.attempts == 300
    assert calibrated.defense.passing.yards == 1920
    assert calibrated.defense.passing.completions == 165
    assert calibrated.defense.passing.interceptions == 12
    assert calibrated.defense.passing.sacks == 26
    assert calibrated.defense.passing.sack_yards == 182


def test_run_yard_calibration_preserves_symbols_and_non_run_results() -> None:
    """Run calibration should scale yardage without losing result semantics."""
    from paydirt.empirical_adjustment import scale_empirical_run_yards

    plays = (
        _play("alpha", "beta", "8*", 1, chart="line_plunge"),
        _play("alpha", "beta", "F - 6", 2, chart="off_tackle"),
        _play("alpha", "beta", "TD", 3, chart="end_run"),
        _play("alpha", "beta", "12", 4, chart="short_pass"),
    )

    calibrated = scale_empirical_run_yards(plays, multiplier=0.75)

    assert [play.result for play in calibrated] == ["6*", "F - 4", "TD", "12"]
    assert [play.chart for play in calibrated] == [
        "line_plunge",
        "off_tackle",
        "end_run",
        "short_pass",
    ]
