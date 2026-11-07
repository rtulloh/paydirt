"""Source, sampling and generation preserve the retained-fumble incomplete subtype."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from paydirt.chart_generator import (
    _ROLL_WEIGHTS,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    _calibrate_empirical_pass_events,
    supported_generated_cell,
)
from paydirt.empirical_adjustment import _category, _passing_attempt_yards, _result_yards
from paydirt.fumble_source import FumbleGainFacts, project_fumble_gain
from paydirt.nflverse_play_by_play import classify_nflverse_rows
from paydirt.pfr_play_by_play import FumbleEvent, calibrate_stats_from_pbp
from tests.test_empirical_adjustment import _play
from tests.test_fumble_source_projection import PROXY, fact_values, nfl_row


def incomplete_row(**changes: object) -> dict:
    return nfl_row(**{
        "play_type": "pass", "pass_attempt": "1", "rush_attempt": "0",
        "incomplete_pass": "1", "complete_pass": "0", "yards_gained": "0",
        "fumbled_1_player_id": "synthetic-player",
        "fumble_recovery_1_team": "FOX",
        "desc": "Pat Quarterback FUMBLES, recovered by FOX-Pat Quarterback. "
                "Pat Quarterback pass incomplete short right.",
        **changes,
    })


def test_joint_projection_carries_no_invented_initial_gain() -> None:
    facts = FumbleGainFacts(**fact_values(
        credited_kind="incomplete", credited_yards=0,
        loose_ball_yards=None, retained_incompletion=True,
    ))
    projected = project_fumble_gain(facts, policy=PROXY)
    assert projected.chart_result == "F INC"
    assert projected.modeled_initial_yards is None
    assert projected.modeled_gain_basis == "retained_incompletion"
    assert projected.to_dict()["source_facts"]["physical_initial_yards"] is None


@pytest.mark.parametrize("changes", [
    {"lost": True}, {"credited_yards": 1}, {"credited_kind": "receiving"},
    {"physical_initial_yards": 0},
])
def test_joint_projection_rejects_conflicting_credit_or_physical_claim(changes: dict) -> None:
    facts = FumbleGainFacts(**fact_values(**{
        "credited_kind": "incomplete", "credited_yards": 0,
        "retained_incompletion": True, **changes,
    }))
    with pytest.raises(ValueError):
        project_fumble_gain(facts, policy=PROXY)


@pytest.mark.parametrize("recovery_player", ["synthetic-player", "synthetic-teammate"])
def test_source_joint_event_projects_once_and_preserves_ledger(recovery_player: str) -> None:
    result = classify_nflverse_rows([
        incomplete_row(fumble_recovery_1_player_id=recovery_player),
    ], fumble_gain_policy=PROXY)
    assert not result.unsupported_fields
    assert [(p.chart, p.result) for p in result.plays] == [("short_pass", "F INC")]
    assert len(result.fumbles) == len(result.fumble_gain_projections) == 1
    assert result.fumbles[0].retained_incompletion is True
    assert result.fumbles[0].lost is False
    assert result.fumble_gain_projections[0].modeled_initial_yards is None


@pytest.mark.parametrize("changes", [
    {"fumble_lost": "1"}, {"fumble_lost": ""},
    {"fumble_recovery_1_team": "OWL"}, {"fumble_recovery_1_team": ""},
    {"fumbled_1_player_id": ""}, {"complete_pass": "1"}, {"sack": "1"},
    {"rush_attempt": "1"}, {"interception": "1"}, {"yards_gained": "-3"},
    {"desc": "Pat Quarterback pass incomplete. A later carrier FUMBLES."},
])
def test_source_joint_event_requires_supported_joint_scope(changes: dict) -> None:
    result = classify_nflverse_rows([incomplete_row(**changes)], fumble_gain_policy=PROXY)
    assert not any(p.result == "F INC" for p in result.plays)
    assert result.unsupported_fields


def test_deterministic_retention_is_excluded_from_recovery_calibration() -> None:
    stats = TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Foxes", "short_name": "FOX",
        "offense": {"passing": {"attempts": 10, "fumbles": 9, "fumbles_lost": 8}},
    })
    ordinary = FumbleEvent("FOX", "passing", True, "synthetic", 1)
    joint = replace(ordinary, lost=False, play_number=2, retained_incompletion=True)
    result = calibrate_stats_from_pbp(stats, "FOX", (), (ordinary, joint))
    assert result.offense.passing.fumbles == 1
    assert result.offense.passing.fumbles_lost == 1
    assert result.offense.passing.retained_fumble_incompletions == 1
    only_joint = calibrate_stats_from_pbp(stats, "FOX", (), (joint,))
    assert only_joint.offense.passing.fumbles == only_joint.offense.passing.fumbles_lost == 0


@pytest.mark.parametrize("column", [
    "screen", "short_pass", "medium_pass", "long_pass", "te_short_long",
])
def test_generator_accepts_joint_token_in_primary_pass_only(column: str) -> None:
    assert supported_generated_cell("offense", column, "F INC")


@pytest.mark.parametrize("unit,column", [
    ("offense", "line_plunge"), ("offense", "draw"), ("offense", "breakaway"),
    ("offense", "qb_time"), ("special_teams", "interception_return"),
])
def test_generator_rejects_joint_token_outside_primary_pass(unit: str, column: str) -> None:
    assert not supported_generated_cell(unit, column, "F INC")


def test_opponent_adjustment_counts_one_zero_yard_attempt_without_initial_gain() -> None:
    play = _play("FOX", "OWL", "F INC", 1, "short_pass")
    assert _category(play.result) == "retained_incompletion"
    assert _passing_attempt_yards(play) == 0
    assert _result_yards(play) is None


def test_pass_calibration_preserves_joint_subtype_within_incomplete_population() -> None:
    baseline = {roll: "BLACK" if roll % 2 else "8" for roll in _ROLL_WEIGHTS}
    outcomes = ("F INC",) * 3 + ("BLACK",) * 37 + ("8",) * 60
    calibrated = _calibrate_empirical_pass_events(
        outcomes, baseline, EmpiricalPassCalibration(),
    )
    counts = Counter(calibrated)
    target_incompletes = round(sum(
        weight for roll, weight in _ROLL_WEIGHTS.items() if baseline[roll] == "BLACK"
    ) / 216 * len(outcomes))
    assert counts["F INC"] == 3
    assert counts["F INC"] + counts["BLACK"] == target_incompletes
    assert len(calibrated) == len(outcomes)


def test_pass_calibration_rejects_incomplete_target_that_cannot_contain_joint_mass() -> None:
    baseline = {roll: "8" for roll in _ROLL_WEIGHTS}
    with pytest.raises(ValueError, match="retained.*incomplet"):
        _calibrate_empirical_pass_events(
            ("F INC", "8"), baseline, EmpiricalPassCalibration(),
        )


@pytest.mark.parametrize("policy", ["credited_fumble_proxy_v1", "source_reported_gain_proxy_v1"])
def test_bound_pfr_split_rows_emit_one_joint_attempt(tmp_path, policy: str) -> None:
    from paydirt.pfr_event_reconciliation import load_event_reconciliations
    from paydirt.pfr_play_by_play import classify_pfr_game
    from tests.test_pfr_event_reconciliation import _prepass_game, _prepass_sidecar

    game = _prepass_game()
    path, record = _prepass_sidecar(tmp_path, game)
    loaded = load_event_reconciliations(path)
    facts = loaded.for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=policy)
    loaded.assert_all_applied()
    assert not result.unsupported_fields
    assert [(p.play_number, p.result) for p in result.plays] == [(8, "F INC")]
    assert len(result.fumbles) == len(result.fumble_gain_projections) == 1
    assert result.fumbles[0].retained_incompletion
    assert result.fumble_gain_projections[0].source_facts.raw_event_sha256 == record["raw_play_sha256"]
    assert not result.diagnostics.get("unmodeled_prepass_fumbles", 0)


@pytest.mark.parametrize("calibrate", [False, True])
def test_generated_csv_preserves_joint_mass_without_qt_or_recovery_double_allocation(tmp_path, calibrate: bool) -> None:
    from paydirt.chart_generator import EmpiricalChartData, generate_team_charts
    from paydirt.chart_loader import load_team_chart
    from tests.test_chart_generator import _synthetic_stats

    results = ("F INC",) * 5 + ("BLACK",) * 35 + ("8",) * 60
    samples = EmpiricalChartData.from_rows(
        {"unit": "offense", "chart": "short_pass", "result": result} for result in results
    )
    generated = generate_team_charts(
        _synthetic_stats(), tmp_path / "Foxes", empirical=samples,
        calibrate_empirical_pass_events=calibrate,
    )
    loaded = load_team_chart(tmp_path / "Foxes")
    assert loaded.offense.short_pass == generated.offense["short_pass"]
    joint_mass = sum(weight for roll, weight in _ROLL_WEIGHTS.items()
                     if loaded.offense.short_pass[roll] == "F INC")
    assert joint_mass / 216 == pytest.approx(.05, abs=1 / 216)
    assert "F INC" not in loaded.offense.qb_time.values()
    assert not any(result.startswith("F") and result != "F INC"
                   for result in loaded.offense.short_pass.values())
