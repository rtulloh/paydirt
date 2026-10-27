"""NFL box-score regressions using public charts and synthetic play results."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[True, False], ids=["home-offense", "away-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.quarter = 3
    engine.state.time_remaining = 8
    engine.state.ball_position = 60
    engine.state.down = 2
    engine.state.yards_to_go = 10
    return engine


def play(game: PaydirtGameEngine, result: PlayResult, play_type: PlayType, procedure: bool) -> PlayOutcome:
    """Exercise both public execution paths without private season data."""
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
    ):
        run = game.run_play_with_penalty_procedure if procedure else game.run_play
        return run(play_type, DefenseType.STANDARD)


@pytest.mark.parametrize("code,yards,auto,ytg,first", [
    ("DEF 15", 15, True, 10, True),
    ("DEF 5X", 5, True, 10, True),
    ("DEF 5", 5, False, 5, True),
    ("DEF 5", 5, False, 10, False),
    ("PI 15", 15, True, 10, True),
    ("PI 50", 50, True, 10, True),
    ("OFF 10", 10, False, 10, False),
])
@pytest.mark.parametrize("accept_play", [False, True])
def test_penalty_first_downs_count_only_when_earned(
    game: PaydirtGameEngine, code: str, yards: int, auto: bool, ytg: int,
    first: bool, accept_play: bool,
) -> None:
    game.state.yards_to_go = ytg
    stats = game.state.offense_stats
    defense = game.state.defense_stats
    result = PlayResult(ResultType.YARDS, yards=2)
    option = PenaltyOption(code.split()[0], code, yards, code, auto_first_down=auto)
    choice = PenaltyChoice(result, penalty_options=[option], offended_team="defense" if code.startswith("OFF") else "offense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert stats.first_downs == 0  # Provisional results must not count.
    outcome = game.apply_penalty_decision(pending, accept_play=accept_play)
    assert stats.first_downs == int(first and not accept_play)
    assert defense.first_downs == 0
    assert outcome.first_down == (first and not accept_play)
    assert stats.total_yards == (2 if accept_play else 0)
    assert stats.passing_yards == (2 if accept_play else 0)
    # Applying an already finalized decision must not duplicate statistics.
    game.apply_penalty_decision(outcome, accept_play=accept_play)
    assert stats.first_downs == int(first and not accept_play)


@pytest.mark.parametrize("code,ytg,first", [("DEF 5", 8, False), ("DEF 5", 5, True), ("DEF 5X", 8, True)])
def test_field_goal_penalty_first_downs(game: PaydirtGameEngine, code: str, ytg: int, first: bool) -> None:
    game.state.ball_position = 70
    game.state.down = 4
    game.state.yards_to_go = ytg
    game.state.possession_team.special_teams.field_goal.update({22: code, 21: "F - 7"})
    stats = game.state.offense_stats
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(22, "P22"), (21, "FG21")]):
        outcome = game.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert stats.first_downs == 0
    outcome = game.apply_fg_penalty_decision(outcome, accept_play=False)
    assert outcome.first_down is first
    assert stats.first_downs == int(first)
    assert stats.total_yards == 0


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("play_type", [PlayType.OFF_TACKLE, PlayType.MEDIUM_PASS])
@pytest.mark.parametrize("kind,yards,position", [
    (ResultType.YARDS, 33, 68),  # Reported pass from TB 32.
    (ResultType.YARDS, 23, 89),  # Reported pass from TB 11.
    (ResultType.BREAKAWAY, 42, 79),  # Reported run from TB 21.
    (ResultType.YARDS, 5, 96),  # Reported run from TB 4.
    (ResultType.YARDS, 1, 99),
    (ResultType.TOUCHDOWN, 0, 89),  # Literal TD without numeric yardage.
    (ResultType.TOUCHDOWN, 75, 89),
])
def test_offensive_touchdown_counts_one_first_down(
    game: PaydirtGameEngine, procedure: bool, play_type: PlayType,
    kind: ResultType, yards: int, position: int,
) -> None:
    game.state.ball_position = position
    game.state.yards_to_go = min(10, 100 - position)
    stats = game.state.offense_stats
    defense = game.state.defense_stats
    outcome = play(game, PlayResult(kind, yards=yards), play_type, procedure)
    assert outcome.touchdown
    assert stats.first_downs == 1
    assert defense.first_downs == 0


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("play_type", [PlayType.OFF_TACKLE, PlayType.MEDIUM_PASS])
@pytest.mark.parametrize("kind,yards,position", [
    (ResultType.YARDS, 33, 68),
    (ResultType.YARDS, 23, 89),
    (ResultType.BREAKAWAY, 42, 79),
    (ResultType.YARDS, 5, 96),
    (ResultType.TOUCHDOWN, 0, 89),
    (ResultType.TOUCHDOWN, 75, 89),
])
def test_touchdown_yardage_stops_at_goal_line(
    game: PaydirtGameEngine, procedure: bool, play_type: PlayType,
    kind: ResultType, yards: int, position: int,
) -> None:
    game.state.ball_position = position
    stats = game.state.offense_stats
    expected = 100 - position
    outcome = play(game, PlayResult(kind, yards=yards, raw_result=str(yards)), play_type, procedure)
    assert outcome.touchdown
    assert outcome.yards_gained == expected
    assert stats.total_yards == expected
    assert stats.passing_yards == (expected if play_type == PlayType.MEDIUM_PASS else 0)
    assert stats.rushing_yards == (expected if play_type == PlayType.OFF_TACKLE else 0)
    assert f"{expected} yards" in game.state.scoring_plays[-1].description
    if outcome.transaction:
        assert outcome.transaction.yards_gained == expected
    assert outcome.result.raw_result == str(yards)  # Preserve raw chart evidence.


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("yards,first", [(0, False), (5, False), (10, True), (20, True)])
def test_non_scoring_yardage_and_first_down_controls(
    game: PaydirtGameEngine, procedure: bool, yards: int, first: bool,
) -> None:
    stats = game.state.offense_stats
    outcome = play(game, PlayResult(ResultType.YARDS, yards=yards), PlayType.OFF_TACKLE, procedure)
    assert not outcome.touchdown
    assert outcome.first_down is first
    assert stats.first_downs == int(first)
    assert outcome.yards_gained == yards
    assert stats.total_yards == yards


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("offense_recovers", [False, True])
def test_fumble_return_touchdown_first_down_attribution(
    game: PaydirtGameEngine, procedure: bool, offense_recovers: bool,
) -> None:
    stats = game.state.offense_stats
    defense = game.state.defense_stats
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    game.state.possession_team.special_teams.interception_return[13] = "40"
    # Offense recovers at 65 and advances 40; the defense's recovery 39 is a chart
    # return (RULE-015), so its chart must carry the touchdown.
    game.state.defense_team.special_teams.interception_return[13] = "TD"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (19 if offense_recovers else 39, "Recovery"), (13, "Return"),
    ]):
        outcome = play(game, PlayResult(ResultType.FUMBLE, yards=5), PlayType.OFF_TACKLE, procedure)
    assert outcome.touchdown
    assert stats.first_downs == int(offense_recovers)
    assert defense.first_downs == 0


@pytest.mark.parametrize("special,position,ytg,kind,yards,expected_first", [
    (PlayType.QB_SNEAK, 99, 1, ResultType.YARDS, 1, True),
    (PlayType.QB_SNEAK, 60, 1, ResultType.YARDS, 1, True),
    (PlayType.QB_SNEAK, 60, 10, ResultType.YARDS, 1, False),
    (PlayType.HAIL_MARY, 89, 11, ResultType.YARDS, 35, True),
    (PlayType.HAIL_MARY, 89, 11, ResultType.TOUCHDOWN, 11, True),
    (PlayType.HAIL_MARY, 60, 10, ResultType.YARDS, 25, True),
    (PlayType.HAIL_MARY, 60, 10, ResultType.PASS_INTERFERENCE, 25, True),
])
def test_special_scrimmage_first_downs(
    game: PaydirtGameEngine, special: PlayType, position: int, ytg: int,
    kind: ResultType, yards: int, expected_first: bool,
) -> None:
    game.state.ball_position = position
    game.state.yards_to_go = ytg
    stats = game.state.offense_stats
    result = PlayResult(kind, yards=yards, touchdown=kind == ResultType.TOUCHDOWN)
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(19, "Special19")),
        patch("paydirt.game_engine.resolve_qb_sneak", return_value=result),
        patch("paydirt.game_engine.resolve_hail_mary", return_value=result),
    ):
        outcome = game.run_play(special, DefenseType.STANDARD)
    assert stats.first_downs == int(expected_first)
    if kind != ResultType.PASS_INTERFERENCE:
        assert stats.total_yards == min(yards, 100 - position)
        assert outcome.yards_gained == min(yards, 100 - position)
    else:
        assert stats.total_yards == 0
        assert stats.passing_yards == 0


@pytest.mark.parametrize("procedure", [False, True])
def test_offensive_recovery_touchdown_yardage_is_capped(
    game: PaydirtGameEngine, procedure: bool,
) -> None:
    stats = game.state.offense_stats
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    game.state.possession_team.special_teams.interception_return[13] = "40"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(19, "Recovery"), (13, "Return")]):
        outcome = play(game, PlayResult(ResultType.FUMBLE, yards=5), PlayType.OFF_TACKLE, procedure)
    assert outcome.touchdown
    assert outcome.yards_gained == 40  # 60 -> opponent goal line, not 45.
    assert outcome.result.fumble_return_yards == 35
    assert stats.total_yards == 40
    assert stats.rushing_yards == 40
    if outcome.transaction:
        assert outcome.transaction.yards_gained == 40


@pytest.mark.parametrize("kind,code", [
    (ResultType.PENALTY_DEFENSE, "DEF S"),
    (ResultType.PASS_INTERFERENCE, "PI 15"),
])
def test_legacy_penalty_first_down_is_not_offensive_yardage(
    game: PaydirtGameEngine, kind: ResultType, code: str,
) -> None:
    stats = game.state.offense_stats
    with patch("paydirt.penalty_handler.roll_chart_dice", return_value=(37, "Penalty37")):
        outcome = play(game, PlayResult(kind, yards=15, raw_result=code), PlayType.MEDIUM_PASS, False)
    assert outcome.first_down
    assert stats.first_downs == 1
    assert stats.total_yards == 0
    assert stats.passing_yards == 0


@pytest.mark.parametrize("accept_play", [False, True])
def test_penalty_choice_does_not_credit_discarded_touchdown(
    game: PaydirtGameEngine, accept_play: bool,
) -> None:
    game.state.ball_position = 79
    stats = game.state.offense_stats
    result = PlayResult(ResultType.BREAKAWAY, yards=42)
    option = PenaltyOption("OFF", "OFF 10", 10, "Offensive penalty")
    choice = PenaltyChoice(result, penalty_options=[option], offended_team="defense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    assert stats.first_downs == stats.total_yards == 0
    assert not game.state.scoring_plays
    outcome = game.apply_penalty_decision(pending, accept_play=accept_play)
    assert stats.first_downs == int(accept_play)
    assert stats.total_yards == (21 if accept_play else 0)
    assert outcome.touchdown is accept_play
    assert len(game.state.scoring_plays) == int(accept_play)


@pytest.mark.parametrize("compact", [False, True])
def test_box_score_displays_engine_first_downs_and_capped_yards(
    game: PaydirtGameEngine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    compact: bool,
) -> None:
    from paydirt import interactive_game as cli

    game.state.ball_position = 89
    play(game, PlayResult(ResultType.YARDS, yards=23), PlayType.MEDIUM_PASS, True)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_box_score(game)
    output = capsys.readouterr().out
    assert "First Downs" in output
    first_down_line = next(line for line in output.splitlines() if "First Downs" in line)
    yardage_line = next(line for line in output.splitlines() if "Total Yards" in line)
    values = [cell.strip() for cell in first_down_line.split("|")[2:4]]
    yards = [cell.strip() for cell in yardage_line.split("|")[2:4]]
    assert values == (["0", "1"] if game.state.is_home_possession else ["1", "0"])
    assert yards == (["0", "11"] if game.state.is_home_possession else ["11", "0"])


@pytest.mark.parametrize("procedure", [False, True])
def test_scramble_touchdown_credits_capped_rushing_yards(
    game: PaydirtGameEngine, procedure: bool,
) -> None:
    game.state.ball_position = 89
    stats = game.state.offense_stats
    outcome = play(game, PlayResult(ResultType.QB_SCRAMBLE, yards=23), PlayType.MEDIUM_PASS, procedure)
    assert outcome.touchdown
    assert outcome.yards_gained == 11
    assert stats.first_downs == 1
    assert stats.total_yards == 11
    assert stats.rushing_yards == 11
    assert stats.passing_yards == 0
