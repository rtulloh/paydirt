"""Field-goal penalty enforcement must preserve the line to gain and discard the kick."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[True, False], ids=["home-kicking", "away-kicking"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game(
        "CLE '83" if request.param else "SEA '83",
        "SEA '83" if request.param else "CLE '83",
    )
    for chart in (engine.state.home_chart, engine.state.away_chart):
        chart.special_teams.field_goal.update({22: "DEF 5", 21: "F - 7"})
    engine.state.is_home_possession = request.param
    engine.state.home_score = engine.state.away_score = 7
    engine.state.quarter = 3
    engine.state.time_remaining = 7.8
    engine.state.ball_position = 70
    engine.state.down = 4
    engine.state.yards_to_go = 8
    return engine


def pending_kick(game: PaydirtGameEngine) -> PlayOutcome:
    """Use the reported rolls: CLE FG 22 -> DEF 5, then 21 -> F - 7."""
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
        (22, "B2+W1+W1=22"), (21, "B2+W0+W1=21"),
    ]):
        outcome = game.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision
    assert outcome.result.raw_result == game.state.possession_team.special_teams.field_goal[21]
    return outcome


def test_reported_def_five_keeps_line_to_gain(game: PaydirtGameEngine) -> None:
    possession = game.state.is_home_possession
    outcome = pending_kick(game)
    assert outcome.result.raw_result == "F - 7"
    result = game.apply_fg_penalty_decision(outcome, accept_play=False)
    assert game.state.ball_position == 75
    assert game.state.down == 4
    assert game.state.yards_to_go == 3
    assert game.state.is_home_possession == possession
    assert result.down_after == 4
    assert result.penalty_applied
    assert not result.field_goal_made
    assert not result.turnover
    assert (game.state.home_score, game.state.away_score) == (7, 7)
    assert not game.state.scoring_plays


@pytest.mark.parametrize("compact", [True, False])
@pytest.mark.parametrize("reroll", ["F - 7", "24", "40", "BK -4"])
def test_accepted_penalty_is_not_displayed_as_field_goal(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch, capsys, compact: bool, reroll: str,
) -> None:
    game.state.possession_team.special_teams.field_goal[21] = reroll
    outcome = pending_kick(game)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    monkeypatch.setattr("builtins.input", lambda *args: "2")
    human_home = game.state.is_home_possession
    chart = game.state.possession_team
    result = cli.handle_penalty_decision(game, outcome, True, human_home)
    capsys.readouterr()  # The choice menu legitimately describes the discarded kick.
    cli.display_play_result(game, result, PlayType.FIELD_GOAL, DefenseType.STANDARD, chart, human_home)
    output = capsys.readouterr().out
    assert "PENALTY" in output
    assert result.description in output
    assert "4th & 3" in output
    assert "SEA 25" in output
    assert "NO GOOD" not in output
    assert "GOOD!" not in output
    assert "BLOCKED" not in output
    assert "FIELD GOAL ATTEMPT" not in output
    assert "Needed:" not in output
    assert "FG 5 yards" not in output
    assert not result.field_goal_made
    assert not game.state.scoring_plays


@pytest.mark.parametrize("penalty,position,ytg,expected_position,expected_down,expected_ytg,first", [
    ("DEF 5", 70, 8, 75, 4, 3, False),
    ("DEF 5", 70, 5, 75, 1, 10, True),
    ("DEF 5", 70, 3, 75, 1, 10, True),
    ("DEF 15", 70, 8, 85, 1, 10, True),
    ("DEF 5X", 70, 8, 75, 1, 10, True),
    ("OFF 10", 70, 8, 60, 4, 18, False),
    ("DEF 5", 96, 4, 98, 4, 2, False),
    ("OFF 10", 8, 8, 4, 4, 12, False),
    ("DEF 5X", 96, 4, 98, 1, 2, True),
])
def test_fg_penalty_enforcement_matches_scrimmage_rules(
    game: PaydirtGameEngine, penalty: str, position: int, ytg: int,
    expected_position: int, expected_down: int, expected_ytg: int, first: bool,
) -> None:
    state = game.state
    state.ball_position, state.yards_to_go = position, ytg
    state.possession_team.special_teams.field_goal[22] = penalty
    outcome = pending_kick(game)
    result = game.apply_fg_penalty_decision(outcome, accept_play=False)
    assert (state.ball_position, state.down, state.yards_to_go) == (
        expected_position, expected_down, expected_ytg,
    )
    assert result.down_after == expected_down
    assert result.first_down is first
    assert result.penalty_applied
    assert result.yards_gained == expected_position - position
    assert not result.field_goal_made
    assert not result.turnover
    stats = state.offense_stats if penalty.startswith("OFF") else state.defense_stats
    assert stats.penalties == 1
    assert stats.penalty_yards == abs(expected_position - position)


@pytest.mark.parametrize("reroll,success", [("24", False), ("40", True)])
def test_declined_penalty_still_reports_actual_kick(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch, capsys, reroll: str, success: bool,
) -> None:
    game.state.possession_team.special_teams.field_goal[21] = reroll
    chart = game.state.possession_team
    human_home = game.state.is_home_possession
    result = game.apply_fg_penalty_decision(pending_kick(game), accept_play=True)
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    cli.display_play_result(game, result, PlayType.FIELD_GOAL, DefenseType.STANDARD, chart, human_home)
    output = capsys.readouterr().out
    assert "PENALTY:" not in output
    assert ("GOOD!" if success else "NO GOOD") in output
    assert result.field_goal_made is success
    assert not result.penalty_applied
