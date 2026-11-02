"""Tests for reproducible chart-generator engine tuning."""

from __future__ import annotations

import pytest

from paydirt.chart_tuning import (
    CalibrationProfile,
    MetricTarget,
    TuningBounds,
    assess_calibration_report,
    propose_next_profile,
    recommended_sample_plan,
)


def _report(*, team_games: int = 1024, completion_rate: float = 0.62) -> dict:
    """Return a compact engine-calibration report for two synthetic teams."""
    return {
        "league": {
            "completion_rate": completion_rate,
            "interception_rate": 0.025,
            "sack_rate": 0.065,
            "yards_per_pass_attempt": 7.1,
            "rushing_yards_per_attempt": 4.2,
            "points_per_team_game": 22.5,
        },
        "teams": {
            "AAA": {"team_games": team_games},
            "BBB": {"team_games": team_games},
        },
    }


def _targets() -> dict[str, MetricTarget]:
    """Return ordered targets matching the documented calibration sequence."""
    return {
        "completion_rate": MetricTarget(value=0.65, tolerance=0.01),
        "interception_rate": MetricTarget(value=0.025, tolerance=0.005),
        "sack_rate": MetricTarget(value=0.065, tolerance=0.005),
        "yards_per_pass_attempt": MetricTarget(value=7.1, tolerance=0.2),
        "rushing_yards_per_attempt": MetricTarget(value=4.2, tolerance=0.15),
        "points_per_team_game": MetricTarget(value=22.5, tolerance=0.75),
    }


def test_profile_loads_supported_generator_controls_and_rejects_unknown_keys() -> None:
    profile = CalibrationProfile.from_mapping(
        {
            "run_yard_multiplier": 1.04,
            "pass_completion_adjustment": 0.02,
            "pass_interception_adjustment": -0.003,
            "pass_pressure_adjustment": 0.004,
            "pass_yard_multiplier": 1.08,
        }
    )

    assert profile.to_dict() == {
        "run_yard_multiplier": 1.04,
        "pass_completion_adjustment": 0.02,
        "pass_interception_adjustment": -0.003,
        "pass_pressure_adjustment": 0.004,
        "pass_yard_multiplier": 1.08,
    }
    with pytest.raises(ValueError, match="Unknown calibration profile field"):
        CalibrationProfile.from_mapping({"mystery_control": 1.0})


def test_assessment_requires_enough_games_for_every_team() -> None:
    with pytest.raises(ValueError, match="AAA.*999.*1000"):
        assess_calibration_report(
            _report(team_games=999),
            _targets(),
            minimum_team_games=1000,
        )


def test_assessment_normalizes_errors_by_tolerance() -> None:
    assessment = assess_calibration_report(
        _report(completion_rate=0.62),
        _targets(),
        minimum_team_games=1000,
    )

    assert assessment.within_tolerance is False
    assert assessment.metrics["completion_rate"].difference == pytest.approx(-0.03)
    assert assessment.metrics["completion_rate"].normalized_error == pytest.approx(-3.0)
    assert assessment.loss == pytest.approx(9.0)


def test_coordinate_descent_changes_only_first_out_of_tolerance_control() -> None:
    assessment = assess_calibration_report(
        _report(completion_rate=0.62),
        _targets(),
        minimum_team_games=1000,
    )
    bounds = {
        "pass_completion_adjustment": TuningBounds(-0.08, 0.08, 0.005),
        "pass_interception_adjustment": TuningBounds(-0.03, 0.03, 0.001),
    }

    proposal = propose_next_profile(CalibrationProfile(), assessment, bounds)

    assert proposal is not None
    assert proposal.metric == "completion_rate"
    assert proposal.parameter == "pass_completion_adjustment"
    assert proposal.previous_value == 0.0
    assert proposal.next_value == pytest.approx(0.005)
    assert proposal.profile.pass_completion_adjustment == pytest.approx(0.005)
    assert proposal.profile.pass_interception_adjustment == 0.0


def test_coordinate_descent_stops_when_metric_is_at_parameter_bound() -> None:
    assessment = assess_calibration_report(
        _report(completion_rate=0.62),
        _targets(),
        minimum_team_games=1000,
    )
    bounds = {
        "pass_completion_adjustment": TuningBounds(-0.08, 0.0, 0.005),
    }

    assert propose_next_profile(CalibrationProfile(), assessment, bounds) is None


@pytest.mark.parametrize(
    ("games_per_season", "training_team_games", "validation_team_games"),
    [(16, 1024, 4096), (17, 1088, 4352)],
)
def test_recommended_sample_plan_uses_64_training_and_256_validation_seasons(
    games_per_season: int,
    training_team_games: int,
    validation_team_games: int,
) -> None:
    plan = recommended_sample_plan(games_per_season)

    assert plan.pilot_seasons == 16
    assert plan.training_seasons == 64
    assert plan.validation_seasons == 256
    assert plan.training_team_games == training_team_games
    assert plan.validation_team_games == validation_team_games
