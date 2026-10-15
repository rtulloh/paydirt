"""Reproduce overtime post-score flow, period accounting, and CLI labels."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.chart_loader import load_team_chart
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome, ScoringPlay
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType


@pytest.fixture
def game() -> PaydirtGameEngine:
    season = Path(__file__).resolve().parents[1] / "seasons" / "1983"
    return PaydirtGameEngine(
        load_team_chart(str(season / "Colts")),
        load_team_chart(str(season / "Bengals")),
    )


def prepare_overtime(game: PaydirtGameEngine, offense_home: bool, score_type: str) -> None:
    game.state.home_score = game.state.away_score = 24
    game.start_overtime(coin_toss_winner_is_home=offense_home)
    game.state.time_remaining = 9 + 35 / 60
    game.state.ball_position = 82 if score_type == "field-goal" else 5
    game.state.down = 4
    game.state.yards_to_go = 1
    game.state.possession_team.special_teams.field_goal[10] = "24"
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)


@pytest.mark.parametrize("entry_point", ["resume", "new"])
@pytest.mark.parametrize("offense_home", [False, True])
@pytest.mark.parametrize("score_type", ["field-goal", "safety"])
def test_game_ending_ot_score_never_prompts_or_kicks(
    game, monkeypatch, capsys, entry_point: str, offense_home: bool, score_type: str,
) -> None:
    """Use real scoring paths in both CLI loops; mock only setup and decisions."""
    prepare_overtime(game, offense_home, score_type)
    play_type = PlayType.FIELD_GOAL if score_type == "field-goal" else PlayType.LINE_PLUNGE
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(cli.random, "choice", lambda choices: choices[0])
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        play_type, False, False, False, False, False,
    ))
    monkeypatch.setattr(cli, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(cli, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    monkeypatch.setattr(cli.ComputerAI, "select_offense_with_clock_management", lambda *args: (
        play_type, False, False, False, 0, False,
    ))
    monkeypatch.setattr(cli, "_offer_record_to_standings", lambda **kwargs: None)
    kickoff_choice = Mock(return_value=False)
    monkeypatch.setattr(cli, "get_kickoff_choice", kickoff_choice)
    kickoff_calls = []
    kickoff_outcome = PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
        description="Unrelated opening kickoff",
    )

    def kickoff(kicking_home: bool) -> PlayOutcome:
        kickoff_calls.append(kicking_home)
        if entry_point == "new" and len(kickoff_calls) == 1:
            prepare_overtime(game, offense_home, score_type)
        return kickoff_outcome

    monkeypatch.setattr(game, "kickoff", kickoff)
    free_kick = Mock(return_value=kickoff_outcome)
    monkeypatch.setattr(game, "safety_free_kick", free_kick)
    if entry_point == "resume":
        monkeypatch.setattr(cli, "get_save_info", lambda _: {
            "saved_at": "test", "away_team": "CIN", "home_team": "BAL",
            "away_score": 24, "home_score": 24, "quarter": 5, "time_remaining": 9.5,
        })
        monkeypatch.setattr(cli, "load_game", lambda _: (game, False, True, None))
    else:
        charts = iter([game.state.home_chart, game.state.away_chart])
        monkeypatch.setattr(cli, "select_team", lambda *args, **kwargs: next(charts))
        monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)

    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "Roll10")),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(10, "Roll10")),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
            PlayResult(ResultType.FUMBLE, yards=-6, raw_result="F - 6"),
        )),
    ):
        if entry_point == "resume":
            cli.resume_game("test-save.json", compact=True)
        else:
            cli.run_interactive_game(compact=True)

    output = capsys.readouterr().out
    assert game.state.game_over
    expected_score = (27, 24) if offense_home else (24, 27)
    if score_type == "safety":
        expected_score = (24, 26) if offense_home else (26, 24)
    assert (game.state.home_score, game.state.away_score) == expected_score
    assert len(kickoff_calls) == (1 if entry_point == "new" else 0)
    assert kickoff_choice.call_count == (1 if entry_point == "new" else 0)
    free_kick.assert_not_called()
    assert "FINAL" in output


def seed_reported_scores(game: PaydirtGameEngine) -> None:
    """The log has 24-24 through four quarters, followed by BAL's winning FG."""
    for quarter, home_points, away_points in [(1, 7, 0), (2, 0, 7), (3, 10, 7), (4, 7, 10), (5, 3, 0)]:
        for is_home, points in [(True, home_points), (False, away_points)]:
            if points:
                team = game.state.home_chart if is_home else game.state.away_chart
                game.state.scoring_plays.append(ScoringPlay(
                    quarter, 9.5, team.short_name, is_home, "FG", "Test score", points,
                ))
    game.state.home_score, game.state.away_score = 27, 24
    game.state.is_overtime = True
    game.state.ot_period = 1
    game.state.quarter = 5


def score_row(output: str, team: str) -> list[int]:
    line = next(line for line in output.splitlines() if line.startswith(f"|  {team}") and " - " not in line)
    return [int(value) for value in " ".join(line.split("|")[2:]).split()]


def test_box_score_separates_ot_points_from_fourth_quarter(game, capsys) -> None:
    seed_reported_scores(game)
    cli.display_box_score(game, "FINAL STATS")
    output = capsys.readouterr().out
    assert score_row(output, "BAL '83") == [7, 0, 10, 7, 3, 27]
    assert score_row(output, "CIN '83") == [0, 7, 7, 10, 0, 24]
    header = next(line for line in output.splitlines() if "TEAM" in line and "TOTAL" in line)
    assert "OT" in header


def test_scoring_summary_calls_fifth_period_overtime(game, capsys) -> None:
    seed_reported_scores(game)
    cli.display_box_score(game)
    output = capsys.readouterr().out
    assert "Overtime" in output
    assert "Q5" not in output


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("ot_period", [1, 2])
def test_cli_status_uses_engine_overtime_label(game, monkeypatch, capsys, compact, ot_period) -> None:
    prepare_overtime(game, True, "field-goal")
    game.state.ot_period = ot_period
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_game_status(game, game.state.home_chart, True)
    output = capsys.readouterr().out
    assert f"OT{ot_period}" in output
    assert "Q5" not in output


def test_second_overtime_score_is_recorded_in_its_own_period(game, capsys) -> None:
    game.state.home_score = game.state.away_score = 24
    game.state.is_playoff = True
    game.start_overtime(coin_toss_winner_is_home=True)
    game._use_time(15 * 60)
    assert game.state.ot_period == 2
    assert game.state.quarter == 6
    game._score_field_goal()
    assert game.state.scoring_plays[-1].quarter == 6
    cli.display_box_score(game)
    output = capsys.readouterr().out
    header = next(line for line in output.splitlines() if "TEAM" in line and "TOTAL" in line)
    assert "OT2" in header
    assert "Overtime 2" in output


def test_scoreless_overtime_still_has_box_score_column(game, capsys) -> None:
    prepare_overtime(game, True, "field-goal")
    cli.display_box_score(game)
    output = capsys.readouterr().out
    header = next(line for line in output.splitlines() if "TEAM" in line and "TOTAL" in line)
    assert "OT" in header
    assert score_row(output, "BAL '83") == [0, 0, 0, 0, 0, 24]


def test_regulation_box_score_has_only_four_quarters(game, capsys) -> None:
    cli.display_box_score(game)
    output = capsys.readouterr().out
    header = next(line for line in output.splitlines() if "TEAM" in line and "TOTAL" in line)
    assert "OT" not in header.split("|")[2].split()
    assert score_row(output, "BAL '83") == [0, 0, 0, 0, 0]


@pytest.mark.parametrize("mode", ["regulation", "modified_sudden_death"])
@pytest.mark.parametrize("offense_home", [False, True])
def test_nonwinning_field_goal_still_gets_kickoff(game, monkeypatch, mode, offense_home) -> None:
    """Do not suppress legitimate kickoffs in regulation or after a modified-OT FG."""
    prepare_overtime(game, offense_home, "field-goal")
    if mode == "regulation":
        game.state.is_overtime = False
        game.state.ot_period = 0
        game.state.quarter = 3
    else:
        game.season_rules.overtime.format = mode
    monkeypatch.setattr(cli, "get_save_info", lambda _: {
        "saved_at": "test", "away_team": "CIN", "home_team": "BAL",
        "away_score": 24, "home_score": 24, "quarter": game.state.quarter,
        "time_remaining": 9.5,
    })
    monkeypatch.setattr(cli, "load_game", lambda _: (game, False, True, None))
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.FIELD_GOAL, False, False, False, False, False,
    ))
    monkeypatch.setattr(cli, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    monkeypatch.setattr(cli.ComputerAI, "select_offense_with_clock_management", lambda *args: (
        PlayType.FIELD_GOAL, False, False, False, 0, False,
    ))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)

    class KickoffReached(Exception):
        """Stop before executing the legitimate post-score kickoff."""

    kickoff = Mock(side_effect=KickoffReached)
    monkeypatch.setattr(game, "kickoff", kickoff)
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "Roll10")),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(10, "Roll10")),
    ):
        with pytest.raises(KickoffReached):
            cli.resume_game("test-save.json", compact=True)
    assert not game.state.game_over
    kickoff.assert_called_once_with(kicking_home=offense_home)


def test_engine_period_scores_match_reported_game_without_mutating_log(game) -> None:
    seed_reported_scores(game)
    original = list(game.state.scoring_plays)
    periods = game.get_period_scores()
    assert [period["home"] for period in periods] == [7, 0, 10, 7, 3]
    assert [period["away"] for period in periods] == [0, 7, 7, 10, 0]
    assert [period["label"] for period in periods] == ["1Q", "2Q", "3Q", "4Q", "OT"]
    assert sum(period["home"] for period in periods) == game.state.home_score
    assert sum(period["away"] for period in periods) == game.state.away_score
    assert game.state.scoring_plays == original
