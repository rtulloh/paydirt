"""Synthetic regressions for nflverse empirical play classification."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

from paydirt.nflverse_play_by_play import (
    classify_nflverse_rows,
    load_nflverse_play_by_play,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season_type": "REG",
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
