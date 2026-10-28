"""AI-001: equivalent first downs must not cost the offense field position."""

from __future__ import annotations

import random
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[False, True], ids=["away-offense", "home-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 50
    engine.state.down = 2
    engine.state.yards_to_go = 10
    engine.state.quarter = 2
    engine.state.time_remaining = 10
    return engine


def penalty(yards: int, automatic: bool = False, kind: str = "DEF") -> PenaltyOption:
    return PenaltyOption(kind, f"{kind} {yards}", yards, "synthetic foul", auto_first_down=automatic)


def pending(game: PaydirtGameEngine, yards: int, options: list[PenaltyOption],
            priority_yards: bool = False) -> PlayOutcome:
    result = PlayResult(
        ResultType.YARDS, yards=5 if priority_yards else yards,
        offense_yards=yards, defense_modifier="DEF 5" if priority_yards else "",
    )
    choice = PenaltyChoice(result, penalty_options=options, offended_team="offense")
    state_before = deepcopy(game.state)
    rng_before = random.getstate()
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision
    assert game.state == state_before
    assert not game.play_log
    assert random.getstate() == rng_before
    return outcome


@pytest.mark.parametrize("down", [1, 2, 3, 4])
@pytest.mark.parametrize("priority_yards", [False, True], ids=["ordinary-yards", "priority-penalty-yards"])
def test_cpu_keeps_eleven_yard_first_down_instead_of_five_yard_automatic_first(
    game: PaydirtGameEngine, down: int, priority_yards: bool,
) -> None:
    game.state.down = down
    outcome = pending(game, 11, [penalty(5, True)], priority_yards)
    ai = ComputerAI(use_analysis=True)
    rng_before = random.getstate()
    accept, _ = ai.should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert accept
    assert random.getstate() == rng_before
    final = game.apply_penalty_decision(outcome, True)
    assert final.first_down
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (61, 1, 10)
    assert game.state.defense_stats.penalties == 0
    assert game.state.offense_stats.first_downs == 1


@pytest.mark.parametrize("yards,automatic,accept", [(5, True, False), (11, True, True), (15, False, False)])
def test_automatic_first_still_matters_but_equal_or_longer_first_down_is_compared_by_spot(
    game: PaydirtGameEngine, yards: int, automatic: bool, accept: bool,
) -> None:
    gain = 4 if yards == 5 else 11
    outcome = pending(game, gain, [penalty(yards, automatic)])
    decision, index = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert decision is accept
    final = game.apply_penalty_decision(outcome, decision, index or 0)
    assert final.first_down
    assert game.state.ball_position == 50 + (gain if accept else yards)


@pytest.mark.parametrize("options,expected", [
    ([penalty(5, True), penalty(15)], 1),
    ([penalty(15), penalty(5, True)], 0),
    ([penalty(5, True), penalty(8, kind="PI")], None),
    ([penalty(5, True), penalty(18, kind="PI")], 1),
])
def test_compare_all_first_down_options_using_original_option_indices(
    game: PaydirtGameEngine, options: list[PenaltyOption], expected: int | None,
) -> None:
    # Include an ineligible option to catch filtered-index mistakes.
    outcome = pending(game, 11, [penalty(30, kind="OFF"), *options])
    accept, index = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert accept is (expected is None)
    if expected is not None:
        assert index == expected + 1
    final = game.apply_penalty_decision(outcome, accept, index or 0)
    assert final.first_down
    assert game.state.down == 1
    assert game.state.ball_position == (61 if expected is None else 50 + options[expected].yards)


def test_half_distance_penalty_does_not_beat_better_first_down_gain(game: PaydirtGameEngine) -> None:
    game.state.ball_position = 94
    game.state.yards_to_go = 2
    outcome = pending(game, 4, [penalty(15, True)])
    accept, _ = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert accept
    final = game.apply_penalty_decision(outcome, True)
    assert final.first_down
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (98, 1, 2)


def test_preview_matches_real_enforcement_without_randomness_or_state_changes(game: PaydirtGameEngine) -> None:
    game.state.ball_position = 94
    game.state.yards_to_go = 2
    outcome = pending(game, 4, [penalty(15, True), penalty(10, kind="PI")])
    play_situation = getattr(outcome, "retained_play_situation", None)
    assert play_situation is not None
    assert (play_situation.ball_position, play_situation.down, play_situation.yards_to_go) == (98, 1, 2)
    for index, situation in outcome.penalty_situations.items():
        clone = deepcopy(game)
        final = clone.apply_penalty_decision(deepcopy(outcome), False, index)
        assert (situation.ball_position, situation.down, situation.yards_to_go, situation.first_down) == (
            clone.state.ball_position, clone.state.down, clone.state.yards_to_go, final.first_down,
        )


def test_real_priority_chart_retains_original_gain_against_def_five_x(game: PaydirtGameEngine) -> None:
    with (
        patch("paydirt.play_resolver.get_offense_result", return_value="11"),
        patch("paydirt.play_resolver.get_defense_modifier", return_value="DEF 5X"),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(12, "synthetic 12")) as rolls,
    ):
        outcome = game.run_play_with_penalty_procedure(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert rolls.call_count == 1
    assert outcome.pending_penalty_decision
    assert outcome.penalty_choice.penalty_options[0].auto_first_down
    assert outcome.result.offense_yards == 11
    accept, _ = ComputerAI(use_analysis=True).should_accept_penalty(
        outcome, False, not game.state.is_home_possession,
    )
    assert accept
    final = game.apply_penalty_decision(outcome, True)
    assert final.yards_gained == 11
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (61, 1, 10)


@pytest.mark.parametrize("quarter", [2, 4, 5, 6])
@pytest.mark.parametrize("time_left", [0, .1, .75])
def test_field_position_comparison_does_not_override_end_of_half_penalty_policy(
    game: PaydirtGameEngine, quarter: int, time_left: float,
) -> None:
    game.state.quarter = quarter
    game.state.time_remaining = time_left
    outcome = pending(game, 11, [penalty(5, True)])
    # The retained gain can expire the half/game, while a defensive penalty
    # may preserve time or an untimed down. Do not call these equivalent.
    accept, index = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert not accept
    assert index == 0


@pytest.mark.parametrize("quarter,time_left", [(1, .1), (3, .1), (2, .751), (4, .751)])
def test_non_expiring_gain_still_uses_first_down_comparison(
    game: PaydirtGameEngine, quarter: int, time_left: float,
) -> None:
    game.state.quarter = quarter
    game.state.time_remaining = time_left
    outcome = pending(game, 11, [penalty(5, True)])
    accept, _ = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert accept


def test_requested_spike_is_not_mistaken_for_equivalent_first_down(game: PaydirtGameEngine) -> None:
    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=11),
        penalty_options=[penalty(5, True)], offended_team="offense",
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.MEDIUM_PASS, DefenseType.STANDARD, call_spike=True,
        )
    assert outcome.retained_play_situation is None
    accept, index = ComputerAI().should_accept_penalty(outcome, False, not game.state.is_home_possession)
    assert not accept
    final = game.apply_penalty_decision(outcome, False, index)
    assert not final.spike_used
    assert game.state.down == 1
