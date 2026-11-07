"""Synthetic regressions for nflverse empirical play classification."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

import pytest

from paydirt.nflverse_play_by_play import (
    classify_nflverse_rows,
    load_nflverse_play_by_play,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season_type": "REG",
        "two_point_attempt": 0,
        "game_id": "2024_01_ARI_BUF",
        "play_id": 1,
        "posteam": "ARI",
        "defteam": "BUF",
        "play_type": "run",
        "desc": "Runner left end for 7 yards",
        "yards_gained": 7,
        "run_location": "left",
        "run_gap": "end",
        "qb_scramble": 0,
        "qb_kneel": 0,
        "qb_spike": 0,
        "pass_length": "",
        "air_yards": "",
        "ydstogo": 10,
        "complete_pass": 0,
        "incomplete_pass": 0,
        "interception": 0,
        "sack": 0,
        "touchdown": 0,
        "return_touchdown": 0,
        "fumble": 0,
        "fumble_lost": 0,
        "out_of_bounds": 0,
        "penalty": 0,
        "penalty_team": "",
        "penalty_yards": "",
        "penalty_type": "",
        "field_goal_result": "",
        "kick_distance": "",
        "return_team": "",
        "return_yards": "",
        "punt_blocked": 0,
        "punt_fair_catch": 0,
        "punt_out_of_bounds": 0,
        "punt_downed": 0,
        "touchback": 0,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize("overrides", [
    {"play_type": "run", "yards_gained": 2},
    {"play_type": "run", "yards_gained": 0, "fumble": 1, "fumble_lost": 1},
    {"play_type": "pass", "pass_attempt": 1, "complete_pass": 1, "yards_gained": 2},
    {"play_type": "pass", "pass_attempt": 1, "incomplete_pass": 1},
    {"play_type": "pass", "pass_attempt": 1, "interception": 1},
    {"play_type": "pass", "pass_attempt": 1, "sack": 1, "yards_gained": -5},
    {"penalty": 1, "penalty_team": "BUF", "penalty_type": "Offside", "penalty_yards": 5},
])
def test_two_point_attempts_do_not_supply_regular_chart_events(overrides: dict) -> None:
    conversion = classify_nflverse_rows([_row(two_point_attempt=1, **overrides)])
    assert not conversion.plays
    assert not conversion.fumbles
    assert not conversion.field_goals
    assert not conversion.event_counts
    assert conversion.diagnostics["excluded_two_point_attempts"] == 1
    assert conversion.games == conversion.source_rows == 1
    assert len(conversion.excluded_conversions) == 1
    excluded = conversion.excluded_conversions[0]
    assert (excluded["game_id"], excluded["play_number"], excluded["team"]) == (
        "2024_01_ARI_BUF", 1, "ARI",
    )
    assert excluded["evidence"] == "structured_flag"
    assert excluded["sack"] == bool(overrides.get("sack"))
    # The same ordinary scrimmage remains eligible; no broad run/pass filter.
    regular = classify_nflverse_rows([_row(two_point_attempt=0, **overrides)])
    assert regular.plays
    assert regular.diagnostics.get("excluded_two_point_attempts", 0) == 0


def test_missing_conversion_capability_stays_explicit_and_does_not_drop_touchdown() -> None:
    row = _row(yards_gained=2, touchdown=1)
    row.pop("two_point_attempt")
    ordinary = classify_nflverse_rows([row])
    assert [(play.chart, play.result) for play in ordinary.plays] == [("end_run", "2")]
    assert ordinary.diagnostics["missing_two_point_flags"] == 1
    assert not ordinary.excluded_conversions


@pytest.mark.parametrize("play_type,penalty", [("pass", 0), ("no_play", 1)])
def test_explicit_conversion_marker_survives_missing_provider_flag(play_type: str, penalty: int) -> None:
    row = _row(play_type=play_type, penalty=penalty, penalty_team="BUF",
               penalty_type="Offside", penalty_yards=5,
               desc="TWO-POINT CONVERSION ATTEMPT. Pass incomplete. PENALTY Offside - No Play")
    row.pop("two_point_attempt")
    season = classify_nflverse_rows([row])
    assert not season.plays
    assert season.diagnostics["excluded_conversion_rows"] == 1
    assert season.diagnostics.get("excluded_two_point_attempts", 0) == 0
    assert season.excluded_conversions[0]["credited_offensive_attempt"] is None
    assert season.diagnostics["missing_two_point_flags"] == 1
    assert season.excluded_conversions[0]["evidence"] == "explicit_description"



@pytest.mark.parametrize("overrides,procedure", [
    ({"play_type": "no_play", "penalty": 1, "penalty_team": "BUF",
      "penalty_type": "Offside", "penalty_yards": 5,
      "desc": "TWO-POINT CONVERSION ATTEMPT. Offside - No Play"}, "voided_offensive_attempt"),
    ({"play_type": "extra_point", "extra_point_attempt": 1,
      "desc": "Extra point is BLOCKED. DEFENSIVE TWO-POINT ATTEMPT. Returner scores."},
     "defensive_return"),
])
def test_zero_conversion_flag_has_known_noncredited_procedures(
    overrides: dict[str, object], procedure: str,
) -> None:
    season = classify_nflverse_rows([_row(**overrides)])
    assert not season.plays and not season.fumbles and not season.event_counts
    assert season.diagnostics.get("conflicting_two_point_flags", 0) == 0
    assert season.diagnostics["excluded_conversion_rows"] == 1
    assert season.diagnostics.get("excluded_two_point_attempts", 0) == 0
    assert season.excluded_conversions[0]["procedure"] == procedure
    assert season.excluded_conversions[0]["credited_offensive_attempt"] is False


@pytest.mark.parametrize("play_type,extra", [
    ("", {}), ("no_play", {}), ("kickoff", {}),
])
def test_missing_conversion_flag_on_non_scrimmage_context_is_inventoried(
    play_type: str, extra: dict[str, object],
) -> None:
    row = _row(play_type=play_type, desc="Administrative or special-teams procedure", **extra)
    row.pop("two_point_attempt")
    season = classify_nflverse_rows([row])
    assert season.diagnostics.get("missing_two_point_flags", 0) == 0
    assert season.diagnostics["not_applicable_two_point_flags"] == 1
    assert not season.excluded_conversions


@pytest.mark.parametrize("play_type,penalty", [("run", 0), ("pass", 0), ("no_play", 1)])
def test_missing_conversion_flag_remains_unknown_on_scrimmage_or_foul(
    play_type: str, penalty: int,
) -> None:
    row = _row(play_type=play_type, penalty=penalty)
    row.pop("two_point_attempt")
    season = classify_nflverse_rows([row])
    assert season.diagnostics["missing_two_point_flags"] == 1
    assert season.diagnostics.get("not_applicable_two_point_flags", 0) == 0


def test_zero_flag_with_retained_ordinary_conversion_marker_remains_conflicting() -> None:
    season = classify_nflverse_rows([_row(
        play_type="pass", desc="TWO-POINT CONVERSION ATTEMPT. Pass complete.", complete_pass=1,
    )])
    assert season.diagnostics["conflicting_two_point_flags"] == 1
    assert season.excluded_conversions[0]["procedure"] == "offensive_attempt"
    assert season.excluded_conversions[0]["credited_offensive_attempt"] is False


def test_credited_and_noncredited_conversion_rows_reconcile_separately() -> None:
    season = classify_nflverse_rows([
        _row(two_point_attempt=1),
        _row(play_id=2, play_type="no_play", penalty=1,
             desc="TWO-POINT CONVERSION ATTEMPT. Offside - No Play"),
        _row(play_id=3, play_type="extra_point", extra_point_attempt=1,
             desc="Extra point BLOCKED. DEFENSIVE TWO-POINT ATTEMPT."),
    ])
    assert season.diagnostics["excluded_conversion_rows"] == 3
    assert season.diagnostics["excluded_two_point_attempts"] == 1
    assert sum(row["credited_offensive_attempt"] for row in season.excluded_conversions) == 1


def test_retained_sack_penalty_keeps_official_source_count() -> None:
    row = _row(
        play_type="pass", sack=1, pass_attempt=1, yards_gained=-5,
        desc="Passer sacked for 5 yards. Unnecessary Roughness, 15 yards",
        penalty=1, penalty_type="Unnecessary Roughness", penalty_team="BUF", penalty_yards=15,
    )
    season = classify_nflverse_rows([row])
    assert season.diagnostics["sacks"] == 1
    assert season.event_counts["ARI"]["sacks"] == 1
    assert season.diagnostics["sacks_with_retained_penalty"] == 1
    # The chart penalty sample and official event count have different purposes.
    assert [play.result for play in season.plays] == ["DEF 15"]


def test_ordinary_sack_and_nullified_sack_counts_are_separate() -> None:
    ordinary = _row(play_type="pass", sack=1, pass_attempt=1, yards_gained=-8)
    nullified = _row(play_id=2, play_type="no_play", sack=0, penalty=1,
                     penalty_team="BUF", penalty_type="Offside", penalty_yards=5,
                     desc="Passer sacked. Offside - No Play")
    season = classify_nflverse_rows([ordinary, nullified])
    assert season.diagnostics["sacks"] == 1
    assert season.diagnostics.get("sacks_with_retained_penalty", 0) == 0
    assert len([play for play in season.plays if play.result == "QT"]) == 1


def test_classifies_empirical_offense_with_opponents_and_markers() -> None:
    rows = [
        _row(out_of_bounds=1),
        _row(play_id=2, qb_scramble=1, run_gap="", yards_gained=11),
        _row(
            play_id=3,
            play_type="pass",
            desc="Pass complete short right for 5 yards, fumble",
            yards_gained=5,
            air_yards=-2,
            complete_pass=1,
            fumble=1,
            fumble_lost=1,
        ),
        _row(
            play_id=4,
            play_type="pass",
            desc="Pass incomplete deep left",
            yards_gained=0,
            air_yards=25,
            incomplete_pass=1,
        ),
        _row(
            play_id=5,
            play_type="pass",
            desc="Pass intercepted and returned 18 yards",
            yards_gained=0,
            air_yards=12,
            interception=1,
            return_team="BUF",
            return_yards=18,
        ),
        _row(
            play_id=6,
            play_type="pass",
            desc="Quarterback sacked for -8 yards and fumbles",
            yards_gained=-8,
            sack=1,
            fumble=1,
            fumble_lost=1,
        ),
    ]

    season = classify_nflverse_rows(rows)
    offense = [play for play in season.plays if play.unit == "offense"]

    assert [(play.chart, play.result, play.opponent) for play in offense] == [
        ("end_run", "7*", "BUF"),
        ("qb_time", "11", "BUF"),
        ("screen", "F + 5", "BUF"),
        ("long_pass", "BLACK", "BUF"),
        ("medium_pass", "INT 12", "BUF"),
        ("short_pass", "QT", "BUF"),
        ("qb_time", "F - 8", "BUF"),
    ]
    assert [(play.team, play.chart, play.result) for play in season.plays if play.unit == "special_teams"] == [
        ("BUF", "interception_return", "18")
    ]
    assert [(event.team, event.unit, event.lost) for event in season.fumbles] == [
        ("ARI", "passing", True),
        ("ARI", "passing", True),
    ]


def test_penalties_use_result_symbols_and_ignore_offsetting_rows() -> None:
    rows = [
        _row(
            play_id=1,
            play_type="no_play",
            desc="Pass incomplete short right. Defensive Pass Interference, 6 yards - No Play",
            penalty=1,
            penalty_team="BUF",
            penalty_yards=6,
            penalty_type="Defensive Pass Interference",
            air_yards=4,
        ),
        _row(
            play_id=2,
            desc="Runner right tackle for 4 yards. Penalty declined",
            penalty=1,
            penalty_team="BUF",
            penalty_yards=5,
            penalty_type="Offside",
            run_gap="tackle",
            yards_gained=4,
        ),
        _row(
            play_id=3,
            desc="Runner middle for 3 yards. Offsetting penalties",
            penalty=1,
            penalty_team="ARI",
            penalty_yards=10,
            penalty_type="Holding",
            run_location="middle",
            run_gap="guard",
            yards_gained=3,
        ),
    ]

    season = classify_nflverse_rows(rows)

    assert [(play.chart, play.result) for play in season.plays] == [
        ("short_pass", "PI 6"),
        ("off_tackle", "4"),
    ]
    assert season.diagnostics["offsetting_penalties"] == 1


def test_retains_field_goals_and_regular_season_filter(tmp_path: Path) -> None:
    rows = [
        _row(
            play_id=1,
            play_type="field_goal",
            desc="Field goal is good",
            field_goal_result="made",
            kick_distance=52,
        ),
        _row(
            play_id=2,
            season_type="POST",
            play_type="field_goal",
            desc="Postseason field goal is no good",
            field_goal_result="missed",
            kick_distance=48,
        ),
    ]
    path = tmp_path / "plays.csv.gz"
    with gzip.open(path, "wt", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    season = load_nflverse_play_by_play(path)

    assert [(attempt.team, attempt.distance, attempt.made) for attempt in season.field_goals] == [
        ("ARI", 52, True)
    ]
    assert season.source_rows == 1
    assert season.games == 1


def test_touchdown_results_follow_developer_chart_conventions() -> None:
    """Encode scoring plays the same way as the developer-created charts."""
    rows = [
        _row(
            play_id=1,
            desc="Runner right tackle for 2 yards, touchdown",
            yards_gained=2,
            run_location="right",
            run_gap="tackle",
            touchdown=1,
        ),
        _row(
            play_id=2,
            play_type="pass",
            desc="Pass complete deep right for 35 yards, touchdown",
            yards_gained=35,
            air_yards=25,
            complete_pass=1,
            touchdown=1,
        ),
        _row(
            play_id=3,
            play_type="pass",
            desc="Pass complete deep right for 45 yards, touchdown",
            yards_gained=45,
            air_yards=30,
            complete_pass=1,
            touchdown=1,
        ),
        _row(
            play_id=4,
            play_type="punt",
            desc="Punt returned 65 yards for touchdown",
            posteam="ARI",
            defteam="BUF",
            touchdown=1,
            return_touchdown=1,
            return_team="BUF",
            return_yards=65,
        ),
        _row(
            play_id=5,
            play_type="pass",
            desc="Pass intercepted and returned 55 yards for touchdown",
            posteam="ARI",
            defteam="BUF",
            air_yards=10,
            interception=1,
            touchdown=1,
            return_touchdown=1,
            return_team="BUF",
            return_yards=55,
        ),
        _row(
            play_id=6,
            play_type="pass",
            desc="Pass intercepted and returned 70 yards for touchdown",
            posteam="ARI",
            defteam="BUF",
            air_yards=10,
            interception=1,
            touchdown=1,
            return_touchdown=1,
            return_team="BUF",
            return_yards=70,
        ),
    ]

    season = classify_nflverse_rows(rows)
    offense = [play for play in season.plays if play.unit == "offense"]
    punt_returns = [play for play in season.plays if play.chart == "punt_return"]
    interception_returns = [
        play for play in season.plays if play.chart == "interception_return"
    ]

    assert [(play.chart, play.result) for play in offense[:3]] == [
        ("off_tackle", "2"),
        ("long_pass", "35"),
        ("long_pass", "45"),
    ]
    assert any(play.result.startswith("INT ") for play in offense)
    assert [(play.team, play.result) for play in punt_returns] == [("BUF", "65")]
    assert [(play.team, play.result) for play in interception_returns] == [
        ("BUF", "55"),
        ("BUF", "70"),
    ]


def test_special_teams_penalties_are_classified_on_the_correct_chart() -> None:
    rows = [
        _row(
            play_id=1,
            play_type="kickoff",
            desc="Kickoff returned 20 yards. Holding on receiving team declined",
            posteam="BUF",
            defteam="ARI",
            kick_distance=65,
            return_team="BUF",
            return_yards=20,
            penalty=1,
            penalty_team="BUF",
            penalty_yards=10,
            penalty_type="Holding",
        ),
        _row(
            play_id=2,
            play_type="punt",
            desc="Punt returned 7 yards. Holding on kicking team",
            posteam="ARI",
            defteam="BUF",
            kick_distance=44,
            return_team="BUF",
            return_yards=7,
            penalty=1,
            penalty_team="ARI",
            penalty_yards=10,
            penalty_type="Holding",
        ),
        _row(
            play_id=3,
            play_type="field_goal",
            desc="Field goal no play because of defensive offside",
            posteam="ARI",
            defteam="BUF",
            field_goal_result="made",
            kick_distance=42,
            penalty=1,
            penalty_team="BUF",
            penalty_yards=5,
            penalty_type="Offside",
        ),
        _row(
            play_id=4,
            play_type="pass",
            desc="Pass intercepted and returned 18 yards. Holding on return team",
            posteam="ARI",
            defteam="BUF",
            air_yards=12,
            interception=1,
            return_team="BUF",
            return_yards=18,
            penalty=1,
            penalty_team="BUF",
            penalty_yards=10,
            penalty_type="Holding",
        ),
    ]

    season = classify_nflverse_rows(rows)

    assert [
        (play.team, play.chart, play.result)
        for play in season.plays
        if play.unit == "special_teams"
    ] == [
        ("BUF", "kickoff_return", "OFF 10"),
        ("BUF", "punt_return", "DEF 10"),
        ("ARI", "field_goal", "DEF 5"),
        ("BUF", "interception_return", "OFF 10"),
    ]
    assert any(
        play.unit == "offense" and play.result == "INT 12"
        for play in season.plays
    )
    assert season.diagnostics["special_teams_penalties"] == 4


def test_kickoff_foul_without_return_is_relative_to_kicking_team() -> None:
    season = classify_nflverse_rows([_row(
        play_type='kickoff', posteam='BUF', defteam='ARI',
        desc='Kickoff, kicking team offside, no play',
        penalty=1, penalty_team='ARI', penalty_type='Offside', penalty_yards=5,
    )])
    assert [(p.team, p.chart, p.result) for p in season.plays] == [('ARI', 'kickoff', 'OFF 5')]


def test_return_out_of_bounds_does_not_make_kickoff_illegal() -> None:
    season = classify_nflverse_rows([_row(
        play_type='kickoff', posteam='BUF', defteam='ARI',
        desc='Kickoff 65 yards, returned 20 yards out of bounds',
        kick_distance=65, return_yards=20, out_of_bounds=1,
    )])
    assert [(p.chart,p.result) for p in season.plays] == [('kickoff','65'),('kickoff_return','20*')]


def test_half_distance_foul_preserves_nominal_yards_and_first_down() -> None:
    rows = [
        _row(play_type='no_play', desc='False Start', penalty=1, penalty_team='ARI',
             penalty_type='False Start', penalty_yards=2),
        _row(play_id=2, play_type='no_play', desc='Defensive Holding', penalty=1,
             penalty_team='BUF', penalty_type='Defensive Holding', penalty_yards=3),
    ]
    season = classify_nflverse_rows(rows)
    assert [p.result for p in season.plays] == ['OFF 5', 'DEF 5X']


def test_punt_touchback_does_not_generate_a_zero_yard_return() -> None:
    season = classify_nflverse_rows([_row(
        play_type='punt', kick_distance=50, return_team='BUF', return_yards=0,
        touchback=1, desc='Punt 50 yards, touchback',
    )])
    assert [(p.chart,p.result) for p in season.plays] == [('punt','50†')]


def test_kickoff_oob_penalty_uses_the_illegal_kick_procedure() -> None:
    season = classify_nflverse_rows([_row(
        play_type='kickoff', posteam='BUF', defteam='ARI',
        desc='Kickoff out of bounds, no play',
        penalty=1, penalty_team='ARI', penalty_type='Kickoff Out of Bounds', penalty_yards=5,
        kickoff_out_of_bounds=1,
    )])
    assert [(p.chart,p.result) for p in season.plays] == [('kickoff','OB')]


def test_qb_scramble_foul_is_not_a_supplemental_penalty_sample():
    row = {"season_type": "REG", "game_id": "2026-TEST", "play_id": "17",
           "posteam": "AAA", "defteam": "BBB", "play_type": "run", "qb_scramble": "1",
           "rush_attempt": "1", "yards_gained": "4", "ydstogo": "8",
           "penalty": "1", "penalty_team": "AAA", "penalty_type": "Offensive Holding",
           "penalty_yards": "10", "desc": "QB scrambles. PENALTY Offensive Holding, no play"}
    classified = classify_nflverse_rows([row])
    assert len(classified.plays) == 1
    assert classified.plays[0].chart in {"screen", "short_pass", "medium_pass", "long_pass"}
    assert classified.plays[0].result == "OFF 10"
    assert classified.diagnostics["supplemental_penalties_as_primary"] == 1
    assert classified.diagnostics["heuristic_penalty_pass_family"] == 1


@pytest.mark.parametrize("gain", [None, "", "nan", "invalid"])
@pytest.mark.parametrize("overrides", [
    {"play_type": "pass", "sack": 1},
    {"play_type": "pass", "complete_pass": 1},
    {"play_type": "run"},
])
def test_unknown_required_gain_is_not_a_zero_outcome(gain: object, overrides: dict) -> None:
    season = classify_nflverse_rows([_row(yards_gained=gain, **overrides)])
    assert not season.plays
    assert season.diagnostics["missing_required_gains"] == 1
    if overrides.get("sack"):
        assert season.event_counts["ARI"]["sacks"] == 1


@pytest.mark.parametrize("lost,expected", [(None, None), ("", None), ("invalid", None), (0, False), (1, True)])
def test_fumble_loss_capability_preserves_unknown_and_known_zero(lost: object, expected: bool | None) -> None:
    season = classify_nflverse_rows([_row(fumble=1, fumble_lost=lost)])
    assert len(season.fumbles) == 1
    assert season.fumbles[0].lost is expected
    assert season.diagnostics.get("unknown_fumble_recoveries", 0) == int(expected is None)


@pytest.mark.parametrize("overrides", [{"play_type": "run"}, {"play_type": "pass", "complete_pass": 1}])
def test_known_zero_required_gain_remains_eligible(overrides: dict) -> None:
    season = classify_nflverse_rows([_row(yards_gained=0, **overrides)])
    assert [play.result for play in season.plays] == ["0"]
    assert season.diagnostics.get("missing_required_gains", 0) == 0



def test_retained_touchdown_does_not_erase_known_fumble_occurrence() -> None:
    season = classify_nflverse_rows([_row(touchdown=1, fumble=1, fumble_lost=0)])
    assert len(season.fumbles) == 1
    assert season.fumbles[0].lost is False
