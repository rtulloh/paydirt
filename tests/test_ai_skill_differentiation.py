"""Synthetic regressions for Medium team awareness and Easy coaching."""

import random
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.ai_analysis import EasyModeHelper, OffenseAnalyzer
from paydirt.chart_loader import OffenseChart
from paydirt.computer_ai import create_computer_ai
from paydirt.play_resolver import PlayType, chart_roll_weights, is_passing_play
from tests.game_fixtures import make_sample_game

RUN_COLUMNS = ("line_plunge", "off_tackle", "end_run", "draw")
PASS_COLUMNS = ("screen", "short_pass", "medium_pass", "long_pass", "te_short_long")


def strength_chart(favored: str) -> OffenseChart:
    """Fill every callable column; category counts must not affect strength."""
    chart = OffenseChart()
    for category, columns in (("run", RUN_COLUMNS), ("pass", PASS_COLUMNS)):
        for column in columns:
            setattr(chart, column, {
                roll: "5" if favored in (category, "balanced") else "0"
                for roll in range(10, 40)
            })
    return chart


def coaching_helper() -> EasyModeHelper:
    chart = OffenseChart(
        line_plunge={roll: "1" for roll in range(10, 40)},
        off_tackle={roll: "5" for roll in range(10, 40)},
        long_pass={roll: "12" if roll % 10 == 5 else "-2" for roll in range(10, 40)},
    )
    return EasyModeHelper(SimpleNamespace(offense=chart, defense=None))


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("down,distance", [(1, 10), (2, 2), (2, 6), (2, 12)])
@pytest.mark.parametrize("favored,shift", [("run", .1), ("pass", -.1)])
def test_medium_tilts_existing_early_down_mix(home: bool, down: int, distance: int,
                                            favored: str, shift: float) -> None:
    game = make_sample_game()
    cpu_chart = game.state.home_chart if home else game.state.away_chart
    cpu_chart.offense = strength_chart(favored)
    # Opponent has the opposite strengths, to expose wrong-team wiring.
    (game.state.away_chart if home else game.state.home_chart).offense = strength_chart(
        "pass" if favored == "run" else "run")
    game.state.is_home_possession = home
    game.state.down, game.state.yards_to_go = down, distance
    game.state.quarter, game.state.time_remaining = 1, 10.0
    game.state.ball_position = 40
    before = random.getstate()
    ai = create_computer_ai("medium", game, cpu_is_home=home)
    assert random.getstate() == before
    with patch("paydirt.computer_ai.random.choices", side_effect=lambda plays, **kw: [plays[0]]) as choose:
        ai.select_offense_with_clock_management(game)
    choose.assert_called_once()
    plays = choose.call_args.args[0]
    weights = choose.call_args.kwargs["weights"]
    original_run = sum(not is_passing_play(play) for play in plays) / len(plays)
    actual_run = sum(weight for play, weight in zip(plays, weights) if not is_passing_play(play))
    assert sum(weights) == pytest.approx(1)
    assert actual_run == pytest.approx(original_run + shift)
    # A category tilt must not turn into best-individual-play optimization.
    for passing in (False, True):
        group = [weight for play, weight in zip(plays, weights) if is_passing_play(play) == passing]
        assert max(group) == pytest.approx(min(group))
    assert ai.team_analyzer is None
    assert ai.opponent_model is None


@pytest.mark.parametrize("favored", ["balanced", "missing", "sparse"])
def test_medium_falls_back_without_clear_supported_strength(favored: str) -> None:
    game = make_sample_game()
    chart = strength_chart("balanced") if favored == "balanced" else OffenseChart()
    if favored == "sparse":
        chart.line_plunge = {15: "50"}
        chart.short_pass = {15: "0"}
    game.state.home_chart.offense = chart
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    with patch("paydirt.computer_ai.random.choice", side_effect=lambda plays: plays[0]) as old, patch(
        "paydirt.computer_ai.random.choices") as weighted:
        assert ai._first_down_offense(40) == PlayType.LINE_PLUNGE
    old.assert_called_once()
    weighted.assert_not_called()


@pytest.mark.parametrize("difficulty", ["easy", "hard"])
def test_other_modes_keep_existing_early_down_selection(difficulty: str) -> None:
    game = make_sample_game()
    game.state.home_chart.offense = strength_chart("pass")
    ai = create_computer_ai(difficulty, game, cpu_is_home=True)
    with patch("paydirt.computer_ai.random.choice", side_effect=lambda plays: plays[0]) as old, patch(
        "paydirt.computer_ai.random.choices") as weighted:
        assert ai._first_down_offense(40) == PlayType.LINE_PLUNGE
        assert ai._second_down_offense(6) == PlayType.OFF_TACKLE
    assert old.call_count == 2
    weighted.assert_not_called()


@pytest.mark.parametrize("situation", ["third", "fourth", "red-zone", "goal-line", "hurry", "kill"])
def test_medium_special_situations_bypass_team_tilt(situation: str) -> None:
    game = make_sample_game()
    game.state.home_chart.offense = strength_chart("run")
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 1, 10.0
    game.state.down, game.state.yards_to_go = 1, 10
    game.state.ball_position = 40
    if situation in ("third", "fourth"):
        game.state.down = 3 if situation == "third" else 4
    elif situation in ("red-zone", "goal-line"):
        game.state.ball_position = 85 if situation == "red-zone" else 97
    else:
        game.state.quarter, game.state.time_remaining = 4, 1.0
        game.state.home_score = 0 if situation == "hurry" else 14
        game.state.away_score = 7
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    with patch("paydirt.computer_ai.random.choices") as weighted:
        ai.select_offense_with_clock_management(game)
    weighted.assert_not_called()


@pytest.mark.parametrize("down,distance,target,expected", [
    (1, 10, 5, "Off Tackle"), (2, 10, 7, "Long"),
    (3, 1, 1, "Off Tackle"), (3, 10, 10, "Long"), (4, 10, 10, "Long"),
    (1, 3, 2, "Off Tackle"), (2, 3, 3, "Off Tackle"), (3, 0, 1, "Off Tackle"),
])
def test_easy_recommendations_follow_distance_target(down: int, distance: int, target: int,
                                                    expected: str) -> None:
    helper = coaching_helper()
    suggestions = helper.suggest_offense_plays(down, distance)
    assert suggestions[0]["play"] == expected
    assert all(s["target_yards"] == target for s in suggestions)
    assert str(target) in suggestions[0]["explanation"]
    assert "chart" in suggestions[0]["explanation"].lower()
    assert "success" not in helper.get_situation_tip(down, distance, 1, 10., 0).lower()


def test_easy_target_metrics_are_dice_weighted_not_positive_gain_odds() -> None:
    helper = coaching_helper()
    long = next(s for s in helper.suggest_offense_plays(3, 10) if s["play"] == "Long")
    probability = sum(weight for roll, weight in chart_roll_weights().items() if roll % 10 == 5) / 216
    assert long["target_rate"] == pytest.approx(100 * probability)
    assert long["success_rate"] == pytest.approx(100 * probability)
    assert long["avg_yards"] == pytest.approx(12 * probability - 2 * (1 - probability))
    assert long["coverage"] == pytest.approx(1)
    plunge = next(s for s in helper.suggest_offense_plays(3, 10) if s["play"] == "Line Plunge")
    assert plunge["target_rate"] == 0
    assert plunge["success_rate"] == 100


@pytest.mark.parametrize("unresolved", ["B", "BLACK", "OFF 5", "DEF 5", "F", "INT 10", "(4)", "DS", "T1"])
def test_easy_discloses_excluded_and_unresolved_chart_mass(unresolved: str) -> None:
    chart = OffenseChart(line_plunge={roll: unresolved for roll in range(10, 40)})
    chart.line_plunge[15] = "5"
    helper = EasyModeHelper(SimpleNamespace(offense=chart, defense=None))
    suggestion = helper.suggest_offense_plays(3, 5)[0]
    assert suggestion["coverage"] == pytest.approx(chart_roll_weights()[15] / 216)
    assert suggestion["limited_data"] is True
    assert "limited" in suggestion["explanation"].lower()
    assert suggestion["target_rate"] == 100  # Conditional, not full-engine conversion odds.


def test_easy_prefers_supported_estimates_to_sparse_perfection() -> None:
    chart = OffenseChart(line_plunge={15: "99"},
                         off_tackle={roll: "5" for roll in range(10, 40)},
                         breakaway={roll: "99" for roll in range(10, 40)})
    helper = EasyModeHelper(SimpleNamespace(offense=chart, defense=None))
    suggestions = helper.suggest_offense_plays(3, 10, 10)
    assert suggestions[0]["play"] == "Off Tackle"
    assert "B" not in [s["play"] for s in suggestions]
    assert helper.suggest_offense_plays(3, 10, 0) == []


def test_easy_analysis_is_read_only_and_empty_data_is_safe() -> None:
    helper = coaching_helper()
    chart = helper.team_analyzer.offense.chart
    original = deepcopy(chart)
    before = random.getstate()
    helper.suggest_offense_plays(3, 10)
    assert helper.explain_play("Long", 3, 10) != helper.explain_play("Long", 3, 1)
    assert chart == original
    assert random.getstate() == before
    empty = EasyModeHelper(SimpleNamespace(offense=OffenseChart(), defense=None))
    assert empty.suggest_offense_plays(3, 10) == []
    assert "Not enough" in empty.explain_play("Screen", 3, 10)


def test_cli_easy_advice_labels_chart_estimates_and_exclusions(capsys: pytest.CaptureFixture) -> None:
    game = make_sample_game()
    game.state.down, game.state.yards_to_go = 3, 10
    cli._show_easy_mode_helper(coaching_helper(), game, is_offense=True)
    text = capsys.readouterr().out.lower()
    assert "target 10" in text
    assert "positive gain" in text
    assert "coverage" in text
    assert "not conversion odds" in text
    assert "excluded" in text
    assert "% success" not in text


def test_existing_hard_chart_metric_is_not_redefined() -> None:
    analyzer = OffenseAnalyzer(OffenseChart(line_plunge={15: "BLACK", 10: "5"}))
    # With correct Paydirt dice: row 10 has weight 2, row 15 has weight 6
    # BLACK is a 0-yard failure (included in valid_rolls)
    # success_rate = (2 / (2+6)) * 100 = 25%
    assert analyzer.analyze_play_type("Line Plunge").success_rate == pytest.approx(25)


@pytest.mark.parametrize("favored,expected", [("run", .1), ("pass", -.1)])
def test_medium_category_summary_uses_dice_weights(favored: str, expected: float) -> None:
    chart = strength_chart("balanced")
    for category, columns in (("run", RUN_COLUMNS), ("pass", PASS_COLUMNS)):
        for column in columns:
            # With correct Paydirt dice weights:
            # - Rows (34, 35): weight 18+18=36 (most likely in 30s)
            # - Rows (10, 11, 12): weight 2+3+4=9 (rare in 10s)
            # The favored category gets the high-weight rows for more positive probability.
            winners = (34, 35) if category == favored else (10, 11, 12)
            setattr(chart, column, {roll: "4" if roll in winners else "0"
                                    for roll in range(10, 40)})
    original = deepcopy(chart)
    before = random.getstate()
    analyzer = OffenseAnalyzer(chart)
    assert analyzer.early_down_run_bias() == expected
    assert analyzer.get_target_stats("Line Plunge", 1) is analyzer.get_target_stats("Line Plunge", 1)
    assert chart == original
    assert random.getstate() == before


@pytest.mark.parametrize("positive_rows", [(10,), (10, 19)])
def test_medium_does_not_tilt_for_small_strength_gaps(positive_rows: tuple) -> None:
    # Test that small differences in category strength don't trigger bias.
    # With correct Paydirt dice, we need to use rows with similar small weights.
    # Row 10: weight 2, Row 19: weight 1 - both are rare/low probability rows.
    chart = strength_chart("balanced")
    for column in PASS_COLUMNS:
        setattr(chart, column, {roll: "0" if roll in positive_rows else "5"
                                for roll in range(10, 40)})
    assert OffenseAnalyzer(chart).early_down_run_bias() == 0


@pytest.mark.parametrize("difficulty,enabled", [("easy", False), ("medium", True),
                                               ("hard", False), ("unknown", True)])
def test_factory_enables_team_summary_only_for_medium(difficulty: str, enabled: bool) -> None:
    game = make_sample_game()
    assert create_computer_ai(difficulty, game, cpu_is_home=True).use_team_strength is enabled


def test_medium_replacing_team_resets_the_cached_strength() -> None:
    game = make_sample_game()
    game.state.home_chart.offense = strength_chart("run")
    ai = create_computer_ai("medium", game, cpu_is_home=True)
    assert ai._run_bias == .1
    ai.set_team(SimpleNamespace(offense=strength_chart("pass")))
    assert ai._run_bias == -.1
    ai.set_team(SimpleNamespace(offense=OffenseChart()))
    assert ai._run_bias == 0


def test_empty_easy_advice_is_explained_in_cli(capsys: pytest.CaptureFixture) -> None:
    game = make_sample_game()
    helper = EasyModeHelper(SimpleNamespace(offense=OffenseChart(), defense=None))
    cli._show_easy_mode_helper(helper, game, is_offense=True)
    assert "Not enough numeric chart data" in capsys.readouterr().out
