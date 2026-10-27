"""Hurry-up pace is not a requirement to call only deep passes."""

import random
from collections import Counter
from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import CHART_PLAY_TYPES, PlayType, is_passing_play
from tests.test_ai_offense_variety import COLUMNS, synthetic_ai


@pytest.fixture(autouse=True)
def preserve_randomness():
    before = random.getstate()
    yield
    random.setstate(before)


def trailing_game(minutes: float = 15, deficit: int = 14, home: bool = True):
    game, ai = synthetic_ai(home=home)
    game.state.quarter, game.state.time_remaining = 4, minutes
    if home:
        game.state.home_score, game.state.away_score = 0, deficit
    else:
        game.state.home_score, game.state.away_score = deficit, 0
    return game, ai


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("home", [True, False])
def test_full_quarter_comeback_can_run_without_giving_up_hurry_up_pace(difficulty: str, home: bool) -> None:
    game, _ = trailing_game(home=home)
    ai = create_computer_ai(difficulty, game, home)
    ai._offense_rng = random.Random(8306)
    counts = Counter()
    for _ in range(1200):
        play, _, no_huddle, *_ = ai.select_offense_with_clock_management(game)
        assert no_huddle
        counts[play] += 1
    runs = sum(n for play, n in counts.items() if not is_passing_play(play))
    assert 120 < runs < 720
    assert len(counts) >= 7


@pytest.mark.parametrize("home", [True, False])
def test_passing_pressure_increases_as_clock_shrinks_but_does_not_ban_runs(home: bool) -> None:
    shares = []
    for minutes in (15, 4, .5):
        game, ai = trailing_game(minutes=minutes, home=home)
        counts = Counter(ai.select_offense(game) for _ in range(2400))
        shares.append(sum(n for play, n in counts.items() if is_passing_play(play)) / 2400)
    assert shares[0] < shares[1] < shares[2]
    assert .90 < shares[2] < 1


def test_larger_deficit_adds_pressure_with_same_clock() -> None:
    pass_shares = []
    for deficit in (7, 21):
        game, ai = trailing_game(minutes=3, deficit=deficit)
        pass_shares.append(sum(is_passing_play(ai.select_offense(game)) for _ in range(2400)))
    assert pass_shares[0] < pass_shares[1]


@pytest.mark.parametrize("favorite", CHART_PLAY_TYPES)
def test_hurry_up_uses_team_strengths_without_single_play_fixation(favorite: PlayType) -> None:
    game, ai = trailing_game()
    for play, column in COLUMNS.items():
        setattr(game.state.possession_team.offense, column,
                {roll: "8" if play == favorite else "6" for roll in range(10, 40)})
    ai.set_team(game.state.possession_team)
    counts = Counter(ai.select_offense(game) for _ in range(2400))
    assert len(counts) == 9
    assert max(counts.values()) / 2400 < .35
    comparable = [counts[play] for play in CHART_PLAY_TYPES
                  if is_passing_play(play) == is_passing_play(favorite) and play != favorite]
    assert counts[favorite] > sum(comparable) / len(comparable)


def test_hurry_up_repetition_adjustment_is_shared_with_ordinary_calls() -> None:
    game, ai = trailing_game()
    ai._offense_rng = random.Random(8306)
    before = Counter(ai.select_offense(game) for _ in range(2400))
    game.offensive_call_history = [{"is_home": True, "down": 1, "distance": 10, "play": "screen"}] * 8
    ai._offense_rng = random.Random(8306)
    after = Counter(ai.select_offense(game) for _ in range(2400))
    assert 0 < after[PlayType.SCREEN] < .7 * before[PlayType.SCREEN]


def test_hurry_up_keeps_only_credible_candidates_when_one_play_is_clearly_better() -> None:
    game, ai = trailing_game(minutes=1)
    game.state.down, game.state.yards_to_go = 3, 10
    for play in CHART_PLAY_TYPES:
        setattr(game.state.possession_team.offense, play.value,
                {roll: "12" if play == PlayType.MEDIUM_PASS else "-5" for roll in range(10, 40)})
    ai.set_team(game.state.possession_team)
    assert {ai.select_offense(game) for _ in range(100)} == {PlayType.MEDIUM_PASS}


def test_hurry_up_can_use_a_uniquely_suitable_run_without_a_pass_quota() -> None:
    game, ai = trailing_game(minutes=1)
    game.state.down, game.state.yards_to_go = 3, 2
    for play in CHART_PLAY_TYPES:
        setattr(game.state.possession_team.offense, play.value,
                {roll: "10" if play == PlayType.OFF_TACKLE else "-5" for roll in range(10, 40)})
    ai.set_team(game.state.possession_team)
    assert {ai.select_offense(game) for _ in range(100)} == {PlayType.OFF_TACKLE}


def test_hurry_up_goal_line_does_not_choose_long_routes_for_one_yard() -> None:
    game, ai = trailing_game(minutes=3)
    game.state.ball_position, game.state.yards_to_go = 99, 1
    assert PlayType.LONG_PASS not in {ai.select_offense(game) for _ in range(100)}


def test_hurry_up_preview_weights_are_read_only_and_match_sampled_candidates() -> None:
    game, ai = trailing_game()
    before = deepcopy(game.offensive_call_history), deepcopy(game.state.possession_team.offense), random.getstate()
    weights = ai.get_hurry_up_weights(game)
    with patch.object(ai._offense_rng, "choices", return_value=[next(iter(weights))]) as choose:
        ai.select_offense(game)
    assert dict(zip(choose.call_args.args[0], choose.call_args.kwargs["weights"])) == weights
    assert (game.offensive_call_history, game.state.possession_team.offense, random.getstate()) == before


@pytest.mark.parametrize("mode", ["fourth", "hail", "field-goal", "victory"])
def test_terminal_coaching_priorities_still_bypass_hurry_up_mixture(mode: str) -> None:
    game, ai = trailing_game(minutes=.1)
    if mode == "fourth":
        game.state.down, game.state.time_remaining = 4, 1
    elif mode == "field-goal":
        game.state.home_score, game.state.away_score = 0, 3
        game.state.ball_position = 80
    elif mode == "victory":
        game.state.home_score, game.state.away_score = 14, 0
    with patch.object(ai, "get_hurry_up_weights", create=True,
                      side_effect=AssertionError("unexpected hurry-up mixture")):
        assert isinstance(ai.select_offense(game), PlayType)


def test_eight_point_deficit_is_more_urgent_when_season_has_no_two_point_conversion() -> None:
    from dataclasses import replace

    pass_weights = []
    for can_go_for_two in (True, False):
        game, ai = trailing_game(minutes=3, deficit=8)
        game.season_rules = replace(game.season_rules, two_point_conversion=can_go_for_two)
        weights = ai.get_hurry_up_weights(game)
        pass_weights.append(sum(w for p, w in weights.items() if is_passing_play(p))
                            / sum(weights.values()))
    assert pass_weights[0] < pass_weights[1]
