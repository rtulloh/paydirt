"""Hard-mode balance regressions for situational defense and humanization.

These tests describe the first-pass policy: special situations remain
authoritative, third/fourth down blends the opponent model with situational
coaching, and tendency evidence decays instead of averaging the whole game.
"""

import random
from collections import Counter
from unittest.mock import Mock

import pytest

from paydirt.ai_analysis import OpponentTendencyTracker
from paydirt.computer_ai import HARD_PRECISION, create_computer_ai
from paydirt.offense_strategy import OffensiveStrategy
from paydirt.play_resolver import DefenseType
from tests.game_fixtures import make_sample_game


def hard_defender(game, *, cpu_is_home: bool = False):
    """Build a Hard defender against the current home/away possession."""
    return create_computer_ai("hard", game, cpu_is_home=cpu_is_home)


def basic_defense_game(*, home_has_ball: bool = True):
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home_has_ball
    state.down, state.yards_to_go = 1, 10
    state.ball_position = 50
    state.quarter, state.time_remaining = 1, 10.0
    state.home_score = state.away_score = 0
    return game


def stub_model(ai, recommendation: str = "A") -> None:
    """Make the model deterministic while retaining both old and new APIs."""
    ai.opponent_model.predict_defense = Mock(return_value=recommendation)
    ai.opponent_model.predict_defense_weights = Mock(
        return_value={recommendation: 1.0}
    )


def test_hard_goal_line_uses_situational_defense_before_model():
    game = basic_defense_game()
    game.state.ball_position = 97
    game.state.yards_to_go = 2
    ai = hard_defender(game)
    stub_model(ai, "C")
    ai._goal_line_defense = Mock(return_value=DefenseType.SHORT_YARDAGE)

    assert ai.select_defense(game) == DefenseType.SHORT_YARDAGE
    assert ai._goal_line_defense.call_args.args[:2] == (1, 2)
    assert isinstance(ai._goal_line_defense.call_args.args[2], random.Random)


@pytest.mark.parametrize(
    "field_pos,quarter,time_left,defense_lead,handler",
    [
        (85, 1, 10.0, 0, "_red_zone_defense"),
        (50, 4, 4.0, 14, "_prevent_defense"),
        (50, 4, 3.0, 7, "_two_minute_defense"),
    ],
)
def test_hard_special_situations_beat_model(
    field_pos: int, quarter: int, time_left: float, defense_lead: int, handler: str,
):
    game = basic_defense_game()
    game.state.ball_position = field_pos
    game.state.quarter = quarter
    game.state.time_remaining = time_left
    game.state.home_score = 0
    game.state.away_score = defense_lead
    ai = hard_defender(game)
    stub_model(ai, "A")
    situational = Mock(return_value=DefenseType.BLITZ)
    setattr(ai, handler, situational)

    assert ai.select_defense(game) == DefenseType.BLITZ
    situational.assert_called_once()


def test_hard_defense_does_not_consume_the_gameplay_dice():
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 3, 10
    ai = hard_defender(game)
    for _ in range(20):
        ai.opponent_model.record_opponent_play(3, 10, "Long", 15, is_pass=True)
    before = random.getstate()

    for _ in range(200):
        ai.select_defense(game)

    assert random.getstate() == before


@pytest.mark.parametrize("down,handler", [(3, "_third_down_defense"), (4, "_fourth_down_defense")])
def test_hard_key_downs_blend_model_and_situational_calls(down: int, handler: str):
    game = basic_defense_game()
    game.state.down = down
    ai = hard_defender(game)
    stub_model(ai, "A")
    situational = Mock(return_value=DefenseType.BLITZ)
    setattr(ai, handler, situational)
    ai._decision_rng = Mock()

    ai._decision_rng.random.return_value = 0.0
    assert ai.select_defense(game) == DefenseType.BLITZ

    ai._decision_rng.random.return_value = 1.0
    assert ai.select_defense(game) == DefenseType.STANDARD


@pytest.mark.parametrize("home_has_ball", [False, True])
def test_hard_fourth_and_short_prefers_run_defense_without_evidence(home_has_ball: bool):
    """A zero-evidence 4th-and-short is a run situation, not a Spread default.

    The 256-game Hard audit showed 4th-and-short scrimmage conversions at 80%
    against Standard and 47% against Short Yardage, with 111 of 129 calls
    carrying no tendency evidence. Formation must stay symmetric for both
    teams.
    """
    game = basic_defense_game(home_has_ball=home_has_ball)
    game.state.down, game.state.yards_to_go = 4, 1
    game.state.ball_position = 65
    ai = hard_defender(game, cpu_is_home=home_has_ball)
    assert ai.opponent_model.tracker.observation_count(4, 1) == 0
    ai._formation_rng().seed(20261124)

    calls = Counter(ai.select_defense(game) for _ in range(400))

    assert calls[DefenseType.SHORT_YARDAGE] > calls[DefenseType.STANDARD]
    assert calls[DefenseType.SHORT_YARDAGE] >= 240
    assert not calls[DefenseType.SPREAD]


@pytest.mark.parametrize("home_has_ball", [False, True])
def test_hard_fourth_and_short_never_treats_a_kick_down_as_standard(home_has_ball: bool):
    """Punts and field goals ignore the formation, so A protects nothing."""
    game = basic_defense_game(home_has_ball=home_has_ball)
    game.state.down, game.state.yards_to_go = 4, 1
    game.state.ball_position = 30
    ai = hard_defender(game, cpu_is_home=home_has_ball)
    ai._formation_rng().seed(20261124)

    calls = Counter(ai.select_defense(game) for _ in range(300))

    assert calls[DefenseType.SHORT_YARDAGE] > calls[DefenseType.STANDARD]


def test_hard_fourth_and_short_fix_does_not_consume_gameplay_dice():
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 4, 1
    game.state.ball_position = 65
    ai = hard_defender(game)
    before = random.getstate()

    for _ in range(200):
        ai.select_defense(game)

    assert random.getstate() == before


def test_hard_fourth_and_medium_or_long_keeps_the_model_read():
    """The short-yardage authority must not spill onto 4th-and-4 or longer."""
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 4, 5
    game.state.ball_position = 65
    ai = hard_defender(game)
    stub_model(ai, "D")
    ai._decision_rng = Mock()
    ai._decision_rng.random.return_value = 0.99

    assert ai.select_defense(game) == DefenseType.SHORT_PASS


def test_hard_early_downs_still_use_the_opponent_model():
    game = basic_defense_game()
    ai = hard_defender(game)
    stub_model(ai, "E")

    assert ai.select_defense(game) == DefenseType.LONG_PASS


def test_hard_uses_the_model_weight_map_on_key_downs():
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 3, 10
    ai = hard_defender(game)
    ai.opponent_model.predict_defense_weights = Mock(
        return_value={"E": 0.8, "F": 0.2})
    ai._decision_rng = Mock()
    ai._decision_rng.random.return_value = 0.99
    ai._defense_rng = Mock()
    ai._defense_rng.choices.side_effect = lambda plays, weights, k: [plays[0]]

    assert ai.select_defense(game) == DefenseType.LONG_PASS


def test_second_choice_noise_uses_the_documented_bound():
    ai = hard_defender(basic_defense_game())
    ai._decision_rng = Mock()
    weights = {"A": 0.8, "B": 0.2}

    ai._decision_rng.random.return_value = (
        OpponentTendencyTracker.SECOND_CHOICE_CHANCE - 0.001)
    assert ai._model_defense(weights) == DefenseType.SHORT_YARDAGE

    ai._decision_rng.random.return_value = (
        OpponentTendencyTracker.SECOND_CHOICE_CHANCE + 0.001)
    assert ai._model_defense(weights) == DefenseType.STANDARD


def test_hard_obvious_passing_downs_keep_a_bounded_long_pass_and_blitz_mix():
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 3, 10
    ai = hard_defender(game)
    for _ in range(20):
        ai.opponent_model.record_opponent_play(3, 10, "Long", 15, is_pass=True)
    weights = ai.opponent_model.predict_defense_weights(3, 10, 0, 1, 10.0)

    assert weights["D"] > weights["E"] > weights["F"] > 0
    assert weights["E"] + weights["F"] < weights["D"]


def test_tendency_tracker_weights_recent_plays_over_lifetime_counts():
    tracker = OpponentTendencyTracker()
    for _ in range(10):
        tracker.record_play(3, 10, "Long", 15, is_pass=True)
    for _ in range(10):
        tracker.record_play(3, 10, "Off Tackle", 4, is_pass=False)

    assert tracker.get_defense_recommendation(3, 10) == "B"


def test_tendency_tracker_uses_a_neutral_prior_before_evidence():
    tracker = OpponentTendencyTracker()

    assert tracker.get_defense_recommendation(1, 10) == "A"


@pytest.mark.parametrize("is_pass,expected", [(True, "D"), (False, "B")])
def test_tendency_tracker_preserves_the_original_60_40_calls(
    is_pass: bool, expected: str,
):
    tracker = OpponentTendencyTracker()
    for _ in range(10):
        tracker.record_play(3, 10, "Long" if is_pass else "Off Tackle", 5,
                            is_pass=is_pass)

    assert tracker.get_defense_recommendation(3, 10) == expected


def test_tendency_tracker_keeps_spread_for_a_mixed_opponent():
    tracker = OpponentTendencyTracker()
    for _ in range(10):
        tracker.record_play(3, 10, "Long", 5, is_pass=True)
        tracker.record_play(3, 10, "Off Tackle", 5, is_pass=False)

    assert tracker.get_defense_recommendation(3, 10) == "C"


def test_every_tendency_recommendation_has_a_ranked_second_choice():
    for plays in ([], [(True, 10)], [(False, 10)], [(True, 10), (False, 10)] * 10):
        tracker = OpponentTendencyTracker()
        for is_pass, _ in plays:
            tracker.record_play(3, 10, "Long" if is_pass else "Off Tackle", 5,
                                is_pass=is_pass)
        weights = tracker.defense_weights(3, 10)
        assert len(weights) > 1


def test_hard_model_can_show_long_pass_and_blitz_on_obvious_passing_downs():
    game = basic_defense_game()
    game.state.down, game.state.yards_to_go = 3, 10
    ai = hard_defender(game)
    for _ in range(10):
        ai.opponent_model.record_opponent_play(3, 10, "Long", 15, is_pass=True)
    ai._decision_rng = random.Random(20261123)

    calls = Counter(ai.select_defense(game) for _ in range(500))

    assert calls[DefenseType.SHORT_PASS] > calls[DefenseType.LONG_PASS] > 0
    assert calls[DefenseType.BLITZ] > 0


def test_hard_factory_uses_tiny_precision_noise_and_reduced_aggression():
    game = basic_defense_game()
    ai = create_computer_ai("hard", game, cpu_is_home=True)

    assert ai.aggression == pytest.approx(0.6)
    assert HARD_PRECISION.fg_optimism == pytest.approx(0.0075)
    assert HARD_PRECISION.band_confusion == pytest.approx(0.04)
    assert HARD_PRECISION.band_margin == pytest.approx(0.06)


def test_hard_offense_uses_a_little_more_variety():
    assert OffensiveStrategy.TEMPERATURE == pytest.approx(0.55)
    assert OffensiveStrategy.COMPETITIVE_GAP == pytest.approx(1.0)
