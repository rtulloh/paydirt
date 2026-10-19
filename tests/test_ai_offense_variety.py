"""Play-independent Hard offense regressions using complete synthetic charts."""

from collections import Counter
from collections.abc import Iterator
from copy import deepcopy
import random
from unittest.mock import patch

import pytest

from paydirt.ai_analysis import OffenseAnalyzer
from paydirt.chart_loader import OffenseChart
from paydirt.computer_ai import ComputerAI, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType
from tests.game_fixtures import make_sample_game


COLUMNS = {
    PlayType.LINE_PLUNGE: "line_plunge", PlayType.OFF_TACKLE: "off_tackle",
    PlayType.END_RUN: "end_run", PlayType.DRAW: "draw", PlayType.SCREEN: "screen",
    PlayType.SHORT_PASS: "short_pass", PlayType.MEDIUM_PASS: "medium_pass",
    PlayType.LONG_PASS: "long_pass", PlayType.TE_SHORT_LONG: "te_short_long",
}


@pytest.fixture(autouse=True)
def preserve_gameplay_randomness() -> Iterator[None]:
    before = random.getstate()
    yield
    random.setstate(before)


def synthetic_ai(
    favorite: PlayType = PlayType.SCREEN, home: bool = True,
) -> tuple[PaydirtGameEngine, ComputerAI]:
    game = make_sample_game()
    chart = OffenseChart()
    for play, column in COLUMNS.items():
        setattr(chart, column, {roll: "8" if play == favorite else "6"
                                for roll in range(10, 40)})
    game.state.is_home_possession = home
    game.state.possession_team.offense = chart
    game.state.down, game.state.yards_to_go = 1, 10
    game.state.ball_position = 40
    game.state.quarter, game.state.time_remaining = 1, 10.0
    ai = create_computer_ai("hard", game, cpu_is_home=home)
    ai._offense_rng = random.Random(731)
    return game, ai


@pytest.mark.parametrize("favorite", list(COLUMNS))
@pytest.mark.parametrize("down,distance", [(1, 10), (2, 8), (3, 6)])
def test_no_callable_play_becomes_a_predictable_situation_default(
    favorite: PlayType, down: int, distance: int,
) -> None:
    game, ai = synthetic_ai(favorite)
    game.state.down, game.state.yards_to_go = down, distance
    counts = Counter()
    # Aggregate multiple fixed streams; no random pass/fail thresholds.
    for seed in range(12):
        random.seed(seed)
        ai._offense_rng = random.Random(seed)
        for _ in range(100):
            counts[ai.select_offense(game)] += 1
    # All nine calls are credible here. A 40% winner override is not.
    assert max(counts.values()) / 1200 < .30
    assert len(counts) == 9
    assert counts[favorite] > 1200 / 9


@pytest.mark.parametrize("favorite", list(COLUMNS))
@pytest.mark.parametrize("home", [False, True])
def test_recent_calls_in_same_situation_reduce_repetition_without_banning(
    favorite: PlayType, home: bool,
) -> None:
    game, ai = synthetic_ai(favorite, home)
    random.seed(71)
    ai._offense_rng = random.Random(71)
    before = Counter(ai.select_offense(game) for _ in range(1200))
    game.offensive_call_history = [
        {"is_home": home, "down": down, "distance": 10 if down == 1 else 3,
         "play": favorite.value if down == 1 else PlayType.DRAW.value}
        for _ in range(8) for down in (1, 2)
    ]
    random.seed(71)
    ai._offense_rng = random.Random(71)
    after = Counter(ai.select_offense(game) for _ in range(1200))
    assert 0 < after[favorite] < before[favorite] * .7
    assert len(after) == 9


@pytest.mark.parametrize("home", [False, True])
def test_other_team_and_other_situation_history_do_not_change_weights(home: bool) -> None:
    game, ai = synthetic_ai(home=home)
    random.seed(31)
    ai._offense_rng = random.Random(31)
    before = [ai.select_offense(game) for _ in range(100)]
    game.offensive_call_history = [
        {"is_home": not home, "down": 1, "distance": 10, "play": PlayType.SCREEN.value},
        {"is_home": home, "down": 2, "distance": 2, "play": PlayType.SCREEN.value},
    ] * 8
    random.seed(31)
    ai._offense_rng = random.Random(31)
    assert [ai.select_offense(game) for _ in range(100)] == before


@pytest.mark.parametrize("favorite", list(COLUMNS))
def test_uniquely_suitable_play_is_not_suppressed_for_variety(favorite: PlayType) -> None:
    game, ai = synthetic_ai(favorite)
    for play, column in COLUMNS.items():
        setattr(game.state.possession_team.offense, column,
                {roll: "10" if play == favorite else "-5" for roll in range(10, 40)})
    ai.set_team(game.state.possession_team)
    game.state.down, game.state.yards_to_go = 3, 10
    game.offensive_call_history = [
        {"is_home": True, "down": 3, "distance": 10, "play": favorite.value}
    ] * 12
    assert {ai.select_offense(game) for _ in range(30)} == {favorite}


def test_long_yardage_values_target_not_just_positive_yards() -> None:
    game, ai = synthetic_ai()
    for column in COLUMNS.values():
        getattr(game.state.possession_team.offense, column).clear()
    game.state.possession_team.offense.screen = {roll: "1" for roll in range(10, 40)}
    game.state.possession_team.offense.medium_pass = {roll: "12" for roll in range(10, 40)}
    ai.set_team(game.state.possession_team)
    game.state.down, game.state.yards_to_go = 3, 10
    assert {ai.select_offense(game) for _ in range(30)} == {PlayType.MEDIUM_PASS}


def test_standard_hard_selection_does_not_consume_gameplay_rng_or_mutate_history() -> None:
    game, ai = synthetic_ai()
    game.offensive_call_history = []
    chart = deepcopy(game.state.possession_team.offense)
    before = random.getstate()
    for _ in range(20):
        ai.select_offense(game)
    assert random.getstate() == before
    assert game.offensive_call_history == []
    assert game.state.possession_team.offense == chart


@pytest.mark.parametrize("secondary", ["breakaway", "qb_time"])
def test_analyzer_never_recommends_a_secondary_column(secondary: str) -> None:
    chart = OffenseChart(line_plunge={roll: "0" for roll in range(10, 40)})
    setattr(chart, secondary, {roll: "99" for roll in range(10, 40)})
    assert OffenseAnalyzer(chart).get_best_play_for_downs(False, False) == "Line Plunge"


@pytest.mark.parametrize("mode", ["goal", "red", "kill", "fourth", "victory"])
def test_special_coaching_priorities_bypass_standard_chart_selection(mode: str) -> None:
    game, ai = synthetic_ai()
    if mode in ("goal", "red"):
        game.state.ball_position = 97 if mode == "goal" else 85
    elif mode == "fourth":
        game.state.down = 4
    else:
        game.state.quarter, game.state.time_remaining = 4, .5
        game.state.home_score = 0 if mode == "hurry" else 14
        game.state.away_score = 7
    with patch.object(ai.offense_strategy, "weights", side_effect=AssertionError("standard analysis")):
        play = ai.select_offense(game)
    assert isinstance(play, PlayType)
    assert ai.last_mode is not None


@pytest.mark.parametrize("bad", ["INT 10", "F", "F+2", "F-2", "OFF 5", "BLACK"])
def test_failure_and_risk_mass_is_not_excluded_to_inflate_success(bad: str) -> None:
    game, ai = synthetic_ai()
    for column in COLUMNS.values():
        getattr(game.state.possession_team.offense, column).clear()
    game.state.possession_team.offense.line_plunge = {roll: "6" for roll in range(10, 40)}
    game.state.possession_team.offense.screen = {
        roll: "20" if roll == 10 else bad for roll in range(10, 40)}
    ai.set_team(game.state.possession_team)
    counts = Counter(ai.select_offense(game) for _ in range(100))
    assert counts[PlayType.LINE_PLUNGE] == 100


def test_sparse_perfect_cell_does_not_beat_supported_chart() -> None:
    game, ai = synthetic_ai()
    for column in COLUMNS.values():
        getattr(game.state.possession_team.offense, column).clear()
    game.state.possession_team.offense.line_plunge = {roll: "6" for roll in range(10, 40)}
    game.state.possession_team.offense.screen = {10: "99"}
    ai.set_team(game.state.possession_team)
    assert {ai.select_offense(game) for _ in range(100)} == {PlayType.LINE_PLUNGE}


@pytest.mark.parametrize("unresolved", ["B", "B*", "QT", "QT*", "DS", "X", "T1", "DEF 5", "PI 15", "(4)"])
def test_unresolved_analysis_never_draws_secondary_rolls(unresolved: str) -> None:
    game, ai = synthetic_ai()
    game.state.possession_team.offense.screen = {roll: unresolved for roll in range(10, 40)}
    ai.set_team(game.state.possession_team)
    before = random.getstate()
    ai.select_offense(game)
    assert random.getstate() == before


def test_history_effect_decays_with_subsequent_other_situations() -> None:
    game, ai = synthetic_ai()
    game.offensive_call_history = [
        {"is_home": True, "down": 1, "distance": 10, "play": PlayType.SCREEN.value}] * 8
    ai._offense_rng = random.Random(88)
    recent = Counter(ai.select_offense(game) for _ in range(1200))
    game.offensive_call_history.extend([
        {"is_home": True, "down": 2, "distance": 2, "play": PlayType.DRAW.value}] * 48)
    ai._offense_rng = random.Random(88)
    aged = Counter(ai.select_offense(game) for _ in range(1200))
    assert aged[PlayType.SCREEN] > recent[PlayType.SCREEN] * 1.5
