"""Regression coverage for advancing an offensive fumble recovery."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game
from tests.game_fixtures import make_sample_game
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType


@pytest.fixture
def game() -> PaydirtGameEngine:
    engine = make_sample_game("BAL '83", "CIN '83")
    # Minimal synthetic inputs for BLACK/QT -> fumble -> recovery advance.
    engine.state.home_chart.offense.long_pass[35] = "BLACK"
    engine.state.home_chart.offense.qb_time[26] = "F - 10"
    engine.state.away_chart.defense.modifiers[("F", 5)] = {8: "QT"}
    engine.state.home_chart.peripheral.fumble_recovered_range = (10, 32)
    engine.state.home_chart.special_teams.interception_return[13] = "41"
    engine.state.is_home_possession = True
    engine.state.quarter = 3
    engine.state.time_remaining = 4.15
    engine.state.ball_position = 50
    engine.state.down = 1
    engine.state.yards_to_go = 10
    return engine


def run_long_pass(game: PaydirtGameEngine, penalty_procedure: bool) -> PlayOutcome:
    """Use synthetic inputs: BLACK/QT -> F - 10, recovery 19, advance 41."""
    run_play = game.run_play_with_penalty_procedure if penalty_procedure else game.run_play
    with (
        patch("paydirt.play_resolver.random.choice", side_effect=[3, 2]),
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(35, "O35"), (26, "QT26")]),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[(19, "R19"), (13, "Ret13")]),
    ):
        return run_play(PlayType.LONG_PASS, DefenseType.BLITZ)


@pytest.mark.parametrize("penalty_procedure", [False, True])
def test_long_pass_recovery_advance_reaches_first_down(game, penalty_procedure: bool) -> None:
    outcome = run_long_pass(game, penalty_procedure)
    assert outcome.result.fumble_spot == 40
    assert outcome.result.fumble_recovery_roll == 19
    assert outcome.result.fumble_return_dice == 13
    assert outcome.result.fumble_return_yards == 41
    assert game.state.ball_position == 81
    assert outcome.first_down
    assert not outcome.turnover
    assert (game.state.down, game.state.yards_to_go) == (1, 10)
    assert outcome.yards_gained == 31
    assert game.state.home_stats.first_downs == 1
    if outcome.transaction:
        assert outcome.transaction.yards_gained == 31
        assert outcome.transaction.first_down


@pytest.mark.parametrize("penalty_procedure", [False, True])
@pytest.mark.parametrize("compact", [False, True])
def test_long_pass_recovery_advance_explained_in_cli(
    game, monkeypatch, capsys, penalty_procedure: bool, compact: bool,
) -> None:
    outcome = run_long_pass(game, penalty_procedure)
    monkeypatch.setattr(interactive_game, "COMPACT_MODE", compact)
    interactive_game.display_play_result(
        game, outcome, PlayType.LONG_PASS, DefenseType.BLITZ,
        game.state.home_chart, True,
    )
    output = capsys.readouterr().out
    assert "advanced 41 yards" in output
    assert "net gain 31 yards" in output
    assert "FIRST DOWN" in output
    assert "Ret:13" in output
    assert "41" in output
    assert "CIN 19" in output


@pytest.mark.parametrize("penalty_procedure", [False, True])
@pytest.mark.parametrize("offense_is_home", [False, True])
@pytest.mark.parametrize("recovery_roll", [17, 18, 19])
@pytest.mark.parametrize("down", [1, 4])
@pytest.mark.parametrize("return_result", ["41", "15", "0", "-5", "60", "TD", "-45"])
def test_recovery_advance_uses_final_spot_for_downs_and_scores(
    game: PaydirtGameEngine,
    penalty_procedure: bool,
    offense_is_home: bool,
    recovery_roll: int,
    down: int,
    return_result: str,
) -> None:
    """Handle all special recovery rolls, failed fourth downs, and either goal line."""
    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType

    game.state.is_home_possession = offense_is_home
    game.state.down = down
    offense = game.state.possession_team
    offense.peripheral.fumble_recovered_range = (10, 32)
    offense.special_teams.interception_return[13] = return_result
    offense_stats = game.state.offense_stats
    result = PlayResult(ResultType.FUMBLE, yards=-10, raw_result="F - 10")
    run_play = game.run_play_with_penalty_procedure if penalty_procedure else game.run_play
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
        patch("paydirt.game_engine.roll_chart_dice", side_effect=[
            (recovery_roll, "Recovery"), (13, "Return13"),
        ]),
    ):
        outcome = run_play(PlayType.LONG_PASS, DefenseType.BLITZ)

    return_yards = 60 if return_result == "TD" else int(return_result)
    net_yards = return_yards - 10
    touchdown = return_yards >= 60
    safety = return_yards <= -40
    first_down = not touchdown and not safety and net_yards >= 10
    turnover = down == 4 and not touchdown and not safety and not first_down
    final_position = 40 + return_yards
    expected_position = (
        97 if touchdown else 20 if safety else
        100 - final_position if turnover else final_position
    )
    assert outcome.touchdown == touchdown
    assert outcome.safety == safety
    assert outcome.first_down == first_down
    assert outcome.turnover == turnover
    assert outcome.yards_gained == net_yards
    assert game.state.ball_position == expected_position
    assert game.state.is_home_possession == (not offense_is_home if turnover else offense_is_home)
    assert offense_stats.first_downs == int(first_down)
    assert offense_stats.fumbles_lost == 0
    if touchdown:
        assert result.scoring_team == offense.peripheral.short_name
        assert (game.state.home_score, game.state.away_score) == (
            (6, 0) if offense_is_home else (0, 6)
        )
    elif safety:
        assert (game.state.home_score, game.state.away_score) == (
            (0, 2) if offense_is_home else (2, 0)
        )
    elif first_down:
        assert (game.state.down, game.state.yards_to_go) == (1, 10)
    elif turnover:
        assert game.state.down == 1
    else:
        assert (game.state.down, game.state.yards_to_go) == (2, 10 - net_yards)
    assert result.rule_explanation
    assert "interception-chart advance" in result.rule_explanation
    if outcome.transaction:
        assert outcome.transaction.yards_gained == net_yards
        assert outcome.transaction.first_down == first_down
