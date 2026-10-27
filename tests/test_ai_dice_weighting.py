"""Exact chart-dice probabilities, conditional analysis, and AI ranking regressions."""

import random
from collections import Counter
from itertools import product
from unittest.mock import patch

import pytest

from paydirt.ai_analysis import OffenseAnalyzer
from paydirt.chart_loader import OffenseChart
from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import PlayType, roll_chart_dice
from tests.game_fixtures import make_sample_game

# Standard Paydirt dice faces (must match play_resolver.py)
BLACK_DIE_FACES = (1, 2, 2, 3, 3, 3)
WHITE_DIE_1_FACES = (0, 0, 1, 2, 3, 4)
WHITE_DIE_2_FACES = (0, 1, 2, 3, 4, 5)


@pytest.fixture(scope="module")
def frequencies() -> Counter:
    """Enumerate all 216 actual face combinations without using random samples.
    
    Standard Paydirt offensive dice:
    - Black die: 1,2,2,3,3,3 (1 appears 1/6, 2 appears 2/6, 3 appears 3/6)
    - White die 1: 0,0,1,2,3,4
    - White die 2: 0,1,2,3,4,5
    Result = (Black * 10) + White1 + White2, range 10-39
    """
    counts = Counter()
    for black, white1, white2 in product(BLACK_DIE_FACES, WHITE_DIE_1_FACES, WHITE_DIE_2_FACES):
        roll = black * 10 + white1 + white2
        counts[roll] += 1
    assert sum(counts.values()) == 216
    # Range is 10 (1*10+0+0) to 39 (3*10+4+5)
    assert min(counts.keys()) == 10
    assert max(counts.keys()) == 39
    # Verify distribution properties:
    # - Row 10 (black=1, whites=0): only 1*2*1=2 ways (black=1:1/6, w1=0:2/6, w2=0:1/6)
    # - Row 30 (black=3, whites=0): 3*2*1=6 ways (black=3:3/6, w1=0:2/6, w2=0:1/6)
    assert counts[10] == 2  # black=1(1 way) * w1=0(2 ways) * w2=0(1 way)
    assert counts[30] == 6  # black=3(3 ways) * w1=0(2 ways) * w2=0(1 way)
    return counts


@pytest.mark.parametrize("target", range(10, 40))
@pytest.mark.parametrize("yards", [6, -6])
def test_every_row_uses_actual_face_probability(
    frequencies: Counter, target: int, yards: int,
) -> None:
    chart = OffenseChart(line_plunge={roll: str(yards if roll == target else 0)
                                      for roll in frequencies})
    stats = OffenseAnalyzer(chart).analyze_play_type("Line Plunge")
    probability = frequencies[target] / 216
    assert stats.avg_yards == pytest.approx(yards * probability)
    assert stats.success_rate == pytest.approx(100 * probability if yards > 0 else 0)
    # Counts and their yardage sum still describe distinct chart rows, not odds.
    assert stats.total_rolls == stats.valid_rolls == 30
    assert stats.total_yards == yards
    assert stats.positive_plays == (1 if yards > 0 else 0)
    assert stats.negative_plays == (1 if yards < 0 else 0)
    assert stats.zero_plays == 29
    assert getattr(stats, "total_probability", None) == pytest.approx(1)
    assert getattr(stats, "valid_probability", None) == pytest.approx(1)
    assert getattr(stats, "positive_probability", None) == pytest.approx(probability if yards > 0 else 0)


@pytest.mark.parametrize("excluded", ["OFF 5", "DEF 5", "F", "F +2", "INT 10", "B"])
def test_exclusions_stay_excluded_and_black_stays_a_failure(excluded: str) -> None:
    analyzer = OffenseAnalyzer(OffenseChart(line_plunge={10: "6", 15: excluded, 19: "BLACK"}))
    stats = analyzer.analyze_play_type("Line Plunge")
    # With correct Paydirt dice:
    # - Row 10: weight 2 (6 yards)
    # - Row 15: weight 6 (excluded)
    # - Row 19: weight 1 (BLACK = 0 yards, included as failure)
    # Included weight is 2 + 1 = 3; excluded row 15 has weight 6.
    # avg_yards = (2*6 + 1*0) / (2+1) = 12/3 = 4.0
    # success_rate = 2 / 3 * 100 = 66.67%
    assert stats.avg_yards == pytest.approx(4.0)
    assert stats.success_rate == pytest.approx(200 / 3)
    assert stats.total_rolls == 3 and stats.valid_rolls == 2
    assert stats.total_yards == 6 and stats.positive_plays == 1 and stats.zero_plays == 1
    assert stats.first_down_rate == stats.first_downs == 0
    assert getattr(stats, "total_probability", None) == pytest.approx(9 / 216)
    assert getattr(stats, "valid_probability", None) == pytest.approx(3 / 216)
    assert getattr(stats, "positive_probability", None) == pytest.approx(2 / 216)


def test_sparse_chart_is_conditioned_only_on_present_valid_rows() -> None:
    chart = OffenseChart(line_plunge={10: "7", 15: "0", 19: "-3", 9: "999", 40: "999"})
    original = dict(chart.line_plunge)
    before = random.getstate()
    analyzer = OffenseAnalyzer(chart)
    stats = analyzer.analyze_play_type("Line Plunge")
    # With correct Paydirt dice:
    # - Row 10: weight 2, +7 yards
    # - Row 15: weight 6, 0 yards
    # - Row 19: weight 1, -3 yards
    # Total weight = 9, avg_yards = (2*7 + 6*0 + 1*(-3)) / 9 = 11/9 ≈ 1.222
    # success_rate = 2/9 * 100 ≈ 22.22%
    assert stats.avg_yards == pytest.approx(11 / 9)
    assert stats.success_rate == pytest.approx(200 / 9)
    assert stats.total_rolls == stats.valid_rolls == 3
    assert stats.total_yards == 4
    assert stats.min_yards == -3 and stats.max_yards == 7
    assert analyzer.analyze_play_type("Line Plunge") is stats
    assert chart.line_plunge == original
    assert random.getstate() == before


@pytest.mark.parametrize("rows,average,success", [
    ({}, 0, 0),
    # Row 10: weight 2 (6 yards), Row 20: weight 4 (0 yards), Row 30: weight 6 (-3 yards)
    # Total weight = 12, avg = (2*6 + 4*0 + 6*(-3)) / 12 = (12 - 18) / 12 = -0.5
    # success = 2/12 * 100 = 16.67%
    ({10: "6", 20: "0", 30: "-3"}, -0.5, 100 / 6),
    ({roll: "7" for roll in range(10, 40)}, 7, 100),
    ({roll: "0" for roll in range(10, 40)}, 0, 0),
    ({roll: "-3" for roll in range(10, 40)}, -3, 0),
    ({10: "F", 15: "INT 2", 19: "B"}, 0, 0),
])
def test_equal_probability_and_constant_outcome_controls(
    rows: dict, average: float, success: float,
) -> None:
    before = random.getstate()
    stats = OffenseAnalyzer(OffenseChart(line_plunge=rows)).analyze_play_type("Line Plunge")
    assert stats.avg_yards == pytest.approx(average)
    assert stats.success_rate == pytest.approx(success)
    assert random.getstate() == before


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("down,distance", [(1, 10), (2, 5), (3, 2), (3, 10)])
def test_hard_ai_ranks_likely_gains_above_more_rare_winning_rows(
    home: bool, down: int, distance: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 50
    game.state.down, game.state.yards_to_go = down, distance
    chart = game.state.possession_team.offense
    # Equal-row ranking prefers three rare winning cells to two common ones.
    for name in vars(chart):
        getattr(chart, name).clear()
    chart.line_plunge = {roll: "5" if roll in (10, 20, 30) else "0" for roll in range(10, 40)}
    chart.off_tackle = {roll: "5" if roll in (15, 25) else "0" for roll in range(10, 40)}
    ai = create_computer_ai("hard", game, cpu_is_home=home)
    assert ai._get_ai_play_suggestion(down, distance) == "Off Tackle"
    assert ai.team_analyzer.offense.get_top_plays(1)[0][0] == "Off Tackle"
    # Hard now samples competitive weighted calls instead of forcing a single
    # recommendation when a global-random override fires. Verify the same dice
    # advantage reaches the selector, without demanding a deterministic policy.
    weights = ai.offense_strategy.weights(down, distance, [], home)
    assert set(weights) == {PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE}
    assert weights[PlayType.OFF_TACKLE] > weights[PlayType.LINE_PLUNGE]
    ai._offense_rng = random.Random(0)
    with patch.object(ai._offense_rng, "choices", return_value=[PlayType.OFF_TACKLE]) as choose:
        assert ai.select_offense(game) == PlayType.OFF_TACKLE
    plays = choose.call_args.args[0]
    assert dict(zip(plays, choose.call_args.kwargs["weights"])) == weights


@pytest.mark.parametrize("difficulty,analysis,aggression", [
    ("easy", False, 0.3), ("medium", False, 0.5), ("hard", True, 0.7),
])
def test_difficulty_configuration_is_unchanged(
    difficulty: str, analysis: bool, aggression: float,
) -> None:
    game = make_sample_game()
    ai = create_computer_ai(difficulty, game, cpu_is_home=False)
    assert ai.use_analysis is analysis
    assert ai.aggression == aggression
    assert (ai.team_analyzer is not None) is analysis
