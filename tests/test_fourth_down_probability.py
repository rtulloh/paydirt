"""Fourth-down kick/punt/go decisions must follow the kicking team's chart.

AI-024: the CPU previously applied fixed 1983 distance tiers (35/47/55) to
every season. These regressions bind the decision to the engine-owned,
chart-weighted make probability and to the season's fourth-down aggression.
"""

from unittest.mock import MagicMock

import pytest

from paydirt.chart_loader import SpecialTeamsChart
from paydirt.computer_ai import ComputerAI
from paydirt.play_resolver import PlayType
from paydirt.season_rules import AIBehavior, AIStrategic
from tests.game_fixtures import make_sample_game

GO_FOR_IT = {
    PlayType.LINE_PLUNGE,
    PlayType.OFF_TACKLE,
    PlayType.END_RUN,
    PlayType.DRAW,
    PlayType.QB_SNEAK,
    PlayType.SHORT_PASS,
    PlayType.MEDIUM_PASS,
    PlayType.LONG_PASS,
    PlayType.SCREEN,
    PlayType.TE_SHORT_LONG,
}


def set_fg_chart(game, makes_from_roll: int, make_value: str = "40",
                 miss_value: str = "10", away: bool = False) -> None:
    """Give the possession team's chart a chosen make/miss split by dice row."""
    chart = game.state.away_chart if away else game.state.home_chart
    chart.special_teams.field_goal = {
        roll: (make_value if roll >= makes_from_roll else miss_value)
        for roll in range(10, 40)
    }


def fourth_down(position: int = 70, ytg: int = 5, quarter: int = 1,
                time_left: float = 10.0, lead: int = 0):
    game = make_sample_game()
    state = game.state
    state.down = 4
    state.yards_to_go = ytg
    state.ball_position = position
    state.quarter = quarter
    state.time_remaining = time_left
    state.is_home_possession = True
    state.home_score = 14 + lead
    state.away_score = 14
    return game


def ai(aggression: float = 0.5, season_aggression: float = 0.5) -> ComputerAI:
    return ComputerAI(
        aggression=aggression,
        ai_behavior=AIBehavior(strategic=AIStrategic(
            fourth_down_aggression=season_aggression)),
    )


def test_weak_chart_punts_where_strong_chart_kicks() -> None:
    """Same 47-yard kick: a 0% chart punts, a 100% chart kicks (AI-024 core)."""
    weak = fourth_down(position=70, ytg=5)
    set_fg_chart(weak, makes_from_roll=40)  # no roll makes 30 yards to goal
    assert ai().select_offense(weak) == PlayType.PUNT

    strong = fourth_down(position=70, ytg=5)
    set_fg_chart(strong, makes_from_roll=10)  # every roll makes it
    assert ai().select_offense(strong) == PlayType.FIELD_GOAL


def test_decision_uses_the_possession_team_chart() -> None:
    """A strong opponent chart must not make our kick look good."""
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=40)  # home chart cannot make it
    set_fg_chart(game, makes_from_roll=10, away=True)  # away chart is strong
    assert ai().select_offense(game) == PlayType.PUNT


def test_era_aggression_changes_a_borderline_kick() -> None:
    """The season profile, not only difficulty, now moves the same decision."""
    # Rolls 34-39 make it: p(distance 30) ~= 0.31, a long-but-possible kick.
    conservative = fourth_down(position=70, ytg=5)
    set_fg_chart(conservative, makes_from_roll=34)
    assert ai(aggression=0.5, season_aggression=0.3).select_offense(conservative) == PlayType.PUNT

    modern = fourth_down(position=70, ytg=5)
    set_fg_chart(modern, makes_from_roll=34)
    assert ai(aggression=0.5, season_aggression=0.7).select_offense(modern) == PlayType.FIELD_GOAL


def test_makeable_probability_kicks_at_low_aggression() -> None:
    """A ~37% chart kick is taken even by a conservative coach."""
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=33)  # p ~= 0.375
    assert ai(aggression=0.3, season_aggression=0.5).select_offense(game) == PlayType.FIELD_GOAL


def test_fourth_and_one_still_goes_for_it_in_long_range() -> None:
    game = fourth_down(position=70, ytg=1)
    set_fg_chart(game, makes_from_roll=34)  # long range, p ~= 0.31
    assert ai(aggression=0.5).select_offense(game) in GO_FOR_IT


def test_end_of_half_field_goal_uses_the_chart() -> None:
    """The 10-second kick is no longer a fixed 47-yard rule."""
    strong = fourth_down(position=70, ytg=5, quarter=2, time_left=8 / 60)
    set_fg_chart(strong, makes_from_roll=10)
    assert ai().select_offense(strong) == PlayType.FIELD_GOAL

    weak = fourth_down(position=70, ytg=5, quarter=2, time_left=8 / 60)
    set_fg_chart(weak, makes_from_roll=40)
    assert ai().select_offense(weak) != PlayType.FIELD_GOAL


def test_last_seconds_tying_kick_uses_the_chart() -> None:
    strong = fourth_down(position=70, ytg=5, quarter=4, time_left=1.0, lead=-3)
    set_fg_chart(strong, makes_from_roll=10)
    assert ai().select_offense(strong) == PlayType.FIELD_GOAL

    weak = fourth_down(position=70, ytg=5, quarter=4, time_left=1.0, lead=-3)
    set_fg_chart(weak, makes_from_roll=40)
    assert ai().select_offense(weak) not in (PlayType.FIELD_GOAL, PlayType.PUNT)


def test_probability_query_does_not_roll_gameplay_dice() -> None:
    import random

    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=33)
    before = random.getstate()
    ai().select_offense(game)
    assert random.getstate() == before


def test_repeated_decisions_are_deterministic() -> None:
    game = fourth_down(position=70, ytg=5)
    set_fg_chart(game, makes_from_roll=33)
    coach = ai()
    assert {coach.select_offense(game) for _ in range(20)} == {PlayType.FIELD_GOAL}


def test_uncharted_mock_chart_keeps_the_documented_distance_fallback() -> None:
    """Mock charts carry no field-goal rows; the legacy curve is explicit."""
    game = make_sample_game()
    game.state.home_chart.special_teams = MagicMock(spec=SpecialTeamsChart)
    game.state.down = 4
    game.state.yards_to_go = 5
    game.state.quarter = 1
    game.state.time_remaining = 10.0
    game.state.is_home_possession = True
    game.state.home_score = game.state.away_score = 14
    coach = ai()

    game.state.ball_position = 75  # 42 statistical yards, inside the fallback
    assert coach.select_offense(game) == PlayType.FIELD_GOAL

    game.state.ball_position = 45  # 72 statistical yards, outside it
    assert coach.select_offense(game) == PlayType.PUNT
