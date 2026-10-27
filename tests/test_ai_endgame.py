"""Deterministic endgame decisions across difficulties and possession orientations."""

from collections.abc import Callable
from unittest.mock import Mock

import pytest

from paydirt.computer_ai import ComputerAI, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[(mode, home) for mode in ("easy", "medium", "hard") for home in (False, True)],
                ids=[f"{mode}-{'home' if home else 'away'}" for mode in ("easy", "medium", "hard")
                     for home in (False, True)])
def endgame(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Callable[..., tuple]:
    mode, home = request.param
    game = make_sample_game()
    game.season_rules.two_point_conversion = True
    ai = create_computer_ai(mode, game, cpu_is_home=home)
    # Make discretionary choices deterministic; correctness must not depend on luck.
    monkeypatch.setattr("paydirt.computer_ai.random.random", lambda: .99)
    monkeypatch.setattr("paydirt.computer_ai.random.choice", lambda choices: choices[0])

    def configure(seconds: float = 60, down: int = 1, lead: int = 1,
                  position: int = 50, timeouts: int = 0, quarter: int = 4,
                  overtime: bool = False) -> tuple[PaydirtGameEngine, ComputerAI]:
        state = game.state
        state.is_home_possession = home
        state.home_score = 21 + (lead if home else 0)
        state.away_score = 21 + (lead if not home else 0)
        state.quarter = 5 if overtime else quarter
        state.is_overtime = overtime
        state.ot_period = 1 if overtime else 0
        if overtime:
            game.season_rules.overtime.format = "modified_sudden_death"
        state.time_remaining = seconds / 60
        state.down, state.yards_to_go = down, 10
        state.ball_position = position
        state.home_timeouts = 3 if home else timeouts
        state.away_timeouts = timeouts if home else 3
        state.two_minute_warning_called = True
        return game, ai

    return configure


@pytest.mark.parametrize("down,seconds,timeouts,position,expected", [
    (1, 120, 0, 50, True), (1, 121, 0, 50, False),
    (2, 80, 0, 50, True), (2, 81, 0, 50, False),
    (3, 40, 0, 50, True), (3, 41, 0, 50, False),
    (4, 6, 0, 50, False),
    (1, 90, 1, 50, True), (1, 91, 1, 50, False),
    (1, 60, 2, 50, True), (1, 61, 2, 50, False),
    (1, 30, 3, 50, True), (1, 31, 3, 50, False),
    (3, 10, 1, 50, True), (3, 11, 1, 50, False),
    (3, 90, 3, 50, False),  # The original third-down/three-timeout regression.
    (3, 40, 0, 3, True), (3, 40, 0, 2, False),
    (2, 80, 0, 3, False), (2, 80, 0, 4, False), (2, 80, 0, 5, True),
    (1, 6, 3, 80, True),  # Protect a win instead of attempting another FG.
])
def test_victory_formation_budget(endgame: Callable[..., tuple], down: int, seconds: float,
                                 timeouts: int, position: int, expected: bool) -> None:
    game, ai = endgame(seconds=seconds, down=down, timeouts=timeouts, position=position)
    decision = ai.select_offense_with_clock_management(game)
    assert (decision[0] == PlayType.QB_KNEEL) is expected
    if expected:
        assert decision[1:] == (False, False, False, 0, False)
        assert not ai.should_call_timeout_on_offense(game)


@pytest.mark.parametrize("quarter,overtime,lead", [(2, False, 14), (3, False, 14),
                                                    (4, False, 0), (4, False, -1),
                                                    (5, True, 0), (5, True, -3),
                                                    (5, True, 3)])
def test_no_victory_formation_without_a_game_to_win(endgame: Callable[..., tuple], quarter: int,
                                                  overtime: bool, lead: int) -> None:
    game, ai = endgame(seconds=30, quarter=quarter, overtime=overtime, lead=lead)
    assert ai.select_offense(game) != PlayType.QB_KNEEL


@pytest.mark.parametrize("down,seconds,timeouts,position", [(1, 120, 0, 50), (2, 50, 1, 50),
                                                           (1, 30, 3, 50), (3, 40, 0, 3)])
def test_victory_plan_finishes_through_real_engine(endgame: Callable[..., tuple],
                                                  down: int, seconds: float, timeouts: int,
                                                  position: int) -> None:
    game, ai = endgame(seconds=seconds, down=down, timeouts=timeouts, position=position)
    original_home = game.state.is_home_possession
    for _ in range(3):
        before = game.state.time_remaining
        quarter = game.state.quarter
        assert ai.select_offense(game) == PlayType.QB_KNEEL
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
        assert not outcome.safety
        assert not outcome.turnover
        # Exercise the engine's real post-play defensive-timeout adjustment.
        if game.state.defense_timeouts > 0 and before > 10 / 60:
            assert game.state.use_timeout(not original_home)
            game._apply_timeout(before, quarter)
        if game.state.game_over:
            break
    assert game.state.game_over
    assert game.state.time_remaining == 0
    assert game.state.is_home_possession is original_home


@pytest.mark.parametrize("quarter,overtime,lead,position,seconds,expected", [
    (2, False, 7, 80, 6, True), (2, False, -7, 80, 10, True),
    (2, False, -7, 80, 10.1, False),
    (4, False, 0, 80, 6, True), (4, False, -1, 80, 6, True),
    (4, False, -2, 80, 6, True), (4, False, -3, 70, 6, True),
    (4, False, -3, 69, 6, False),
    (4, False, -4, 80, 6, False), (4, False, -7, 80, 6, False),
    (5, True, 0, 80, 6, True), (5, True, -3, 80, 6, True),
    (5, True, -7, 80, 6, False),
])
def test_last_seconds_scoring_choice(endgame: Callable[..., tuple], quarter: int, overtime: bool,
                                    lead: int, position: int, seconds: float, expected: bool) -> None:
    game, ai = endgame(seconds=seconds, lead=lead, position=position,
                       quarter=quarter, overtime=overtime)
    decision = ai.select_offense_with_clock_management(game)
    assert (decision[0] == PlayType.FIELD_GOAL) is expected
    if expected:
        assert decision[2] is True  # Preserve the clock for the kick.
        assert decision[1] is False
        assert decision[5] is False


@pytest.mark.parametrize("overtime", [False, True])
@pytest.mark.parametrize("down", [1, 2, 3, 4])
def test_last_play_needing_touchdown_reaches_endzone(endgame: Callable[..., tuple], overtime: bool,
                                                   down: int) -> None:
    game, ai = endgame(seconds=6, down=down, lead=-7, position=50, overtime=overtime)
    assert ai.select_offense(game) == PlayType.HAIL_MARY


@pytest.mark.parametrize("overtime", [False, True])
@pytest.mark.parametrize("seconds", [119, 120])
@pytest.mark.parametrize("position", [20, 80])
def test_fourth_down_needing_touchdown_does_not_surrender(endgame: Callable[..., tuple],
                                                        overtime: bool, seconds: float,
                                                        position: int) -> None:
    game, ai = endgame(seconds=seconds, down=4, lead=-7, position=position, overtime=overtime)
    assert ai.select_offense(game) not in (PlayType.PUNT, PlayType.FIELD_GOAL, PlayType.QB_KNEEL)


@pytest.mark.parametrize("lead,quarter,overtime,allowed,expected", [
    (0, 4, False, True, False), (-1, 4, False, True, False),
    (-2, 4, False, True, True), (1, 4, False, True, True),
    (-8, 4, False, True, True), (-9, 4, False, True, True),
    (14, 4, False, True, False), (-2, 2, False, True, False),
    (-2, 4, False, False, False), (1, 4, False, False, False),
    (0, 5, True, True, False), (-2, 5, True, True, True),
])
def test_conversion_score_and_season_matrix(endgame: Callable[..., tuple], lead: int, quarter: int,
                                           overtime: bool, allowed: bool, expected: bool) -> None:
    game, ai = endgame(seconds=60, lead=lead, quarter=quarter, overtime=overtime)
    game.season_rules.two_point_conversion = allowed
    assert ai.should_go_for_two(game) is expected


@pytest.mark.parametrize("overtime", [False, True])
def test_no_conversion_after_game_over(endgame: Callable[..., tuple], overtime: bool) -> None:
    game, ai = endgame(seconds=0, lead=-2, overtime=overtime)
    game.state.game_over = True
    assert not ai.should_go_for_two(game)


@pytest.mark.parametrize("overtime", [False, True])
@pytest.mark.parametrize("on_offense", [False, True])
@pytest.mark.parametrize("timeouts,expected", [(0, False), (1, True)])
def test_timeouts_preserve_a_comeback(endgame: Callable[..., tuple], overtime: bool,
                                     on_offense: bool, timeouts: int, expected: bool) -> None:
    game, ai = endgame(seconds=60, lead=-7 if on_offense else 7, overtime=overtime)
    game.state.home_timeouts = game.state.away_timeouts = timeouts
    choose = ai.should_call_timeout_on_offense if on_offense else ai.should_call_timeout_on_defense
    assert choose(game) is expected


@pytest.mark.parametrize("lead,seconds,expected", [(-1, 119, True), (-1, 120, True),
                                                 (-1, 121, False), (0, 60, False), (1, 60, False)])
def test_onside_kick_desperation_boundary(endgame: Callable[..., tuple], lead: int,
                                         seconds: float, expected: bool) -> None:
    game, ai = endgame(seconds=seconds, lead=lead)
    assert ai.should_onside_kick(game) is expected


@pytest.mark.parametrize("seconds", [0, 10])
def test_no_victory_plan_for_an_untimed_down(endgame: Callable[..., tuple], seconds: float) -> None:
    game, ai = endgame(seconds=seconds)
    game.state.untimed_down_pending = True
    assert ai.select_offense(game) != PlayType.QB_KNEEL


def test_hard_analysis_cannot_override_a_guaranteed_win(endgame: Callable[..., tuple]) -> None:
    game, ai = endgame(seconds=6, position=80)
    ai._get_ai_play_suggestion = Mock(side_effect=AssertionError("Do not risk a safe win"))
    assert ai.select_offense(game) == PlayType.QB_KNEEL
    ai._get_ai_play_suggestion.assert_not_called()
