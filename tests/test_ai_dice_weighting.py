"""Exact chart-dice probabilities, conditional analysis, and AI ranking regressions."""

from collections import Counter
from itertools import product
import random
from unittest.mock import patch

import pytest

from paydirt.ai_analysis import OffenseAnalyzer
from paydirt.chart_loader import OffenseChart
from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import PlayType, roll_chart_dice
from tests.game_fixtures import make_sample_game


@pytest.fixture(scope="module")
def frequencies() -> Counter:
    """Enumerate all 216 actual face combinations without using random samples."""
    counts = Counter()
    for black, white1, white2 in product((1, 1, 2, 2, 3, 3), range(6), range(6)):
        with (
            patch("paydirt.play_resolver.random.choice", return_value=black) as choose,
            patch("paydirt.play_resolver.random.randint", side_effect=[white1, white2]) as white,
        ):
            roll, description = roll_chart_dice()
        assert roll == black * 10 + min(white1 + white2, 9)
        assert description == f"B{black}+W{white1}+W{white2}={roll}"
        assert tuple(choose.call_args.args[0]) == (1, 1, 2, 2, 3, 3)
        assert white.call_args_list == [((0, 5),), ((0, 5),)]
        counts[roll] += 1
    assert sum(counts.values()) == 216
    assert set(counts) == set(range(10, 40))
    assert counts[15] == 6 * counts[10]
    assert counts[19] == 3 * counts[10]  # Sums 9 and 10 both use row 19.
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
    # Included weight is 2 + 6; excluded row 15 has weight 12.
    assert stats.avg_yards == pytest.approx(1.5)
    assert stats.success_rate == pytest.approx(25)
    assert stats.total_rolls == 3 and stats.valid_rolls == 2
    assert stats.total_yards == 6 and stats.positive_plays == 1 and stats.zero_plays == 1
    assert stats.first_down_rate == stats.first_downs == 0
    assert getattr(stats, "total_probability", None) == pytest.approx(20 / 216)
    assert getattr(stats, "valid_probability", None) == pytest.approx(8 / 216)
    assert getattr(stats, "positive_probability", None) == pytest.approx(2 / 216)


def test_sparse_chart_is_conditioned_only_on_present_valid_rows() -> None:
    chart = OffenseChart(line_plunge={10: "7", 15: "0", 19: "-3", 9: "999", 40: "999"})
    original = dict(chart.line_plunge)
    before = random.getstate()
    analyzer = OffenseAnalyzer(chart)
    stats = analyzer.analyze_play_type("Line Plunge")
    assert stats.avg_yards == pytest.approx(-0.2)
    assert stats.success_rate == pytest.approx(10)
    assert stats.total_rolls == stats.valid_rolls == 3
    assert stats.total_yards == 4
    assert stats.min_yards == -3 and stats.max_yards == 7
    assert analyzer.analyze_play_type("Line Plunge") is stats
    assert chart.line_plunge == original
    assert random.getstate() == before


@pytest.mark.parametrize("rows,average,success", [
    ({}, 0, 0),
    ({10: "6", 20: "0", 30: "-3"}, 1, 100 / 3),
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
    with patch("paydirt.computer_ai.random.random", return_value=0):
        assert ai.select_offense(game) == PlayType.OFF_TACKLE


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
