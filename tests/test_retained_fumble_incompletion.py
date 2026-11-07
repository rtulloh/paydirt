"""Synthetic regressions for a retained fumble followed by an incomplete pass."""

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    DefenseType,
    PlayType,
    ResultType,
    parse_result_string,
    resolve_breakaway,
    resolve_play,
    resolve_play_with_penalties,
    resolve_qb_scramble,
    resolve_qb_sneak,
)
from paydirt.priority_chart import (
    PriorityResult,
    ResultCategory,
    apply_priority_chart,
    categorize_result,
)


@pytest.fixture
def teams() -> tuple[TeamChart, TeamChart]:
    """Use synthetic charts with the public sample season's real rules."""
    season = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    return tuple(
        TeamChart(
            peripheral=PeripheralData(
                year=2026, team_name=name, team_nickname=name, short_name=name,
                power_rating=50, fumble_recovered_range=(10, 20),
            ),
            offense=OffenseChart(), defense=DefenseChart(),
            special_teams=SpecialTeamsChart(), team_dir=str(season / name),
        )
        for name in ("Synthetic Home", "Synthetic Away")
    )


@contextmanager
def selected_cells(offense: tuple[str, ...] = ("F INC",), defense: str = "0"):
    """Keep chart selection deterministic while running the real priority/resolvers."""
    with (
        patch("paydirt.play_resolver.get_offense_result", side_effect=offense),
        patch("paydirt.play_resolver.get_defense_modifier", return_value=defense),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(10, "10")) as rolls,
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
    ):
        yield rolls


def assert_retained_incompletion(result) -> None:
    assert result.result_type == ResultType.INCOMPLETE
    assert result.retained_fumble_incompletion is True
    assert result.yards == 0
    assert result.turnover is False
    assert result.touchdown is False
    assert result.out_of_bounds is False
    assert result.fumble_recovery_roll == result.fumble_return_dice == 0
    assert result.qb_scramble_dice == result.breakaway_dice == 0
    # Existing zero defaults mean unset; no internal recovery spot is invented.
    assert result.fumble_spot == result.fumble_return_yards == 0
    assert "retained" in result.description.lower()
    assert "incomplete" in result.description.lower()


def test_canonical_composite_has_fumble_category() -> None:
    assert categorize_result("F INC") == (ResultCategory.FUMBLE, 0)


@pytest.mark.parametrize("defense", ["0", "5", "-2", "(3)", "BLACK", "QT", "INT 25", "(TD)", "F"])
def test_selected_composite_uses_fumble_priority_without_generic_turnover(defense: str) -> None:
    combined = apply_priority_chart("F INC", defense)
    assert combined.priority == PriorityResult.FUMBLE
    assert combined.retained_fumble_incompletion is True
    assert combined.is_incomplete is True
    assert combined.is_turnover is False
    assert combined.final_yards == 0
    assert not combined.use_qt_column and not combined.use_breakaway
    assert not combined.is_touchdown and not combined.out_of_bounds


@pytest.mark.parametrize("penalty", ["OFF 5", "DEF 5"])
def test_priority_penalty_suppresses_unselected_occurrence(penalty: str) -> None:
    combined = apply_priority_chart("F INC", penalty)
    assert combined.retained_fumble_incompletion is False
    assert combined.is_incomplete is False
    assert combined.is_turnover is False


def test_fumble_priority_deliberately_differs_from_black() -> None:
    black = apply_priority_chart("BLACK", "INT 25")
    retained = apply_priority_chart("F INC", "INT 25")
    assert black.is_turnover and not black.is_incomplete
    assert retained.is_incomplete and not retained.is_turnover


@pytest.mark.parametrize("offense,defense,passing", [("F INC", "0", False), ("0", "F INC", True)])
def test_composite_rejects_unsupported_chart_context(offense: str, defense: str, passing: bool) -> None:
    with pytest.raises(ValueError, match="F INC.*primary.*passing"):
        apply_priority_chart(offense, defense, is_passing_play=passing)


def test_context_free_parser_rejects_primary_only_composite() -> None:
    with pytest.raises(ValueError, match="F INC.*primary.*passing"):
        parse_result_string("F INC")


@pytest.mark.parametrize("column,resolver", [("qb_time", resolve_qb_scramble),
                                             ("breakaway", resolve_breakaway)])
def test_secondary_columns_reject_primary_only_composite(teams, column, resolver) -> None:
    setattr(teams[0].offense, column, {10: "F INC"})
    with pytest.raises(ValueError, match="F INC.*primary.*passing"):
        resolver(teams[0].offense, 10)


def test_qb_sneak_rejects_primary_passing_only_composite(teams) -> None:
    teams[0].offense.line_plunge = {10: "F INC"}
    with pytest.raises(ValueError, match="F INC.*primary.*passing"):
        resolve_qb_sneak(teams[0].offense, 10)


@pytest.mark.parametrize("resolver", [resolve_play, resolve_play_with_penalties])
@pytest.mark.parametrize("play", [PlayType.SCREEN, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                                 PlayType.LONG_PASS, PlayType.TE_SHORT_LONG])
def test_both_resolvers_finish_primary_pass_without_recovery_roll(teams, resolver, play) -> None:
    with selected_cells(defense="INT 25") as rolls:
        resolved = resolver(*teams, play, DefenseType.STANDARD)
    result = resolved.play_result if hasattr(resolved, "play_result") else resolved
    assert_retained_incompletion(result)
    assert rolls.call_count == 1
    if hasattr(resolved, "transaction"):
        assert len(resolved.transaction.events) == 1  # Lookup only; no invented recovery.


@pytest.mark.parametrize("resolver", [resolve_play, resolve_play_with_penalties])
@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.HAIL_MARY])
def test_resolvers_reject_composite_outside_primary_passing_columns(teams, resolver, play) -> None:
    with selected_cells(), pytest.raises(ValueError, match="F INC.*primary.*passing"):
        resolver(*teams, play, DefenseType.STANDARD)


@pytest.mark.parametrize("penalty", ["DEF 5", "DEF 15"])
def test_ordinary_resolver_does_not_credit_fumble_when_penalty_wins(teams, penalty) -> None:
    with selected_cells(defense=penalty) as rolls:
        result = resolve_play(*teams, PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert result.retained_fumble_incompletion is False
    assert result.result_type in (ResultType.PENALTY_OFFENSE, ResultType.PENALTY_DEFENSE)
    assert rolls.call_count == 1


@pytest.mark.parametrize("resolver", [resolve_play, resolve_play_with_penalties])
@pytest.mark.parametrize("token,expected", [("BLACK", ResultType.INCOMPLETE), ("5", ResultType.YARDS),
                                          ("F", ResultType.FUMBLE), ("QT", ResultType.SACK)])
def test_legacy_passing_symbols_keep_their_results(teams, resolver, token, expected) -> None:
    # The synthetic QT secondary column contains -3; ordinary F uses existing recovery.
    teams[0].offense.qb_time = {10: "-3"}
    with selected_cells((token,)):
        resolved = resolver(*teams, PlayType.SHORT_PASS, DefenseType.STANDARD)
    result = resolved.play_result if hasattr(resolved, "play_result") else resolved
    assert result.result_type == expected
    assert getattr(result, "retained_fumble_incompletion", False) is False
    if token == "F" and resolver is resolve_play_with_penalties:
        assert result.fumble_recovery_roll == 10


@pytest.mark.parametrize("penalty_route", [False, True])
@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("position", [2, 50, 98])
@pytest.mark.parametrize("down", [1, 4])
def test_engine_matches_ordinary_incompletion_state_clock_and_stats(teams, penalty_route, home, position, down) -> None:
    outcomes = []
    for token in ("BLACK", "F INC"):
        game = PaydirtGameEngine(*deepcopy(teams))
        game.state.is_home_possession = home
        game.state.ball_position = position
        game.state.down = down
        game.state.yards_to_go = min(10, 100 - position)
        game.state.quarter = 2
        game.state.time_remaining = 1.5
        game.state.two_minute_warning_called = True
        method = game.run_play_with_penalty_procedure if penalty_route else game.run_play
        with selected_cells((token,)) as rolls:
            outcome = method(PlayType.SHORT_PASS, DefenseType.STANDARD)
        assert rolls.call_count == 1
        assert outcome.yards_gained == 0
        assert not outcome.turnover and not outcome.touchdown and not outcome.safety
        assert outcome.turnover_on_downs is (down == 4)
        assert game.state.is_home_possession is (not home if down == 4 else home)
        assert game.state.ball_position == (100 - position if down == 4 else position)
        assert game.state.down == (1 if down == 4 else down + 1)
        assert game.state.time_remaining == pytest.approx(1.5 - 5 / 60)
        assert len(game.play_log) == 1
        if token == "F INC":
            assert_retained_incompletion(outcome.result)
        outcomes.append((game.state, outcome))
    ordinary, retained = outcomes
    assert retained[0].home_stats == ordinary[0].home_stats
    assert retained[0].away_stats == ordinary[0].away_stats
    assert retained[1].clock_trace == ordinary[1].clock_trace


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("position", [2, 50, 98])
@pytest.mark.parametrize("down", [1, 4])
@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5", "defense-chart"])
@pytest.mark.parametrize("accept_play", [False, True])
def test_penalty_choice_credits_only_retained_play(teams, home, position, down, foul, accept_play) -> None:
    game = PaydirtGameEngine(*teams)
    game.state.is_home_possession = home
    game.state.ball_position = position
    game.state.down = down
    game.state.yards_to_go = min(10, 100 - position)
    game.state.quarter = 2
    game.state.time_remaining = 1.5
    game.state.two_minute_warning_called = True
    stats = game.state.offense_stats
    cells = ("F INC",) if foul == "defense-chart" else (foul, "F INC")
    defense = "DEF 5" if foul == "defense-chart" else "0"
    with selected_cells(cells, defense) as rolls:
        pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
        assert pending.pending_penalty_decision
        assert game.state.down == down and game.state.ball_position == position
        assert game.state.time_remaining == 1.5
        result = game.apply_penalty_decision(pending, accept_play=accept_play)
    assert rolls.call_count == len(cells)
    assert not result.pending_penalty_decision
    assert result.result.retained_fumble_incompletion is accept_play
    assert not result.turnover and not result.touchdown and not result.safety
    assert stats.total_yards == stats.passing_yards == stats.rushing_yards == 0
    assert stats.sacks == stats.fumbles_lost == stats.interceptions_thrown == stats.turnovers == 0
    if accept_play:
        assert_retained_incompletion(result.result)
        assert game.state.down == (1 if down == 4 else down + 1)
        assert result.turnover_on_downs is (down == 4)
        assert game.state.time_remaining == pytest.approx(1.5 - 5 / 60)
    else:
        assert result.penalty_applied
        assert result.penalty_choice.play_result.retained_fumble_incompletion
        assert game.state.is_home_possession is home
        assert game.state.down == down
        assert game.state.time_remaining == pytest.approx(1.5 - 5 / 60)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("down", [1, 4])
def test_offsetting_fouls_void_candidate_occurrence_stats_and_down(teams, home, down) -> None:
    game = PaydirtGameEngine(*teams)
    game.state.is_home_possession = home
    game.state.ball_position = 50
    game.state.down = down
    game.state.time_remaining = 10
    with selected_cells(("OFF 5", "F INC"), "DEF 5") as rolls:
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert rolls.call_count == 2
    assert outcome.penalty_choice.offsetting
    assert outcome.result.retained_fumble_incompletion is False
    assert outcome.penalty_choice.play_result.retained_fumble_incompletion
    assert game.state.is_home_possession is home
    assert game.state.ball_position == 50 and game.state.down == down
    assert game.state.time_remaining == pytest.approx(10 - 10 / 60)
    assert game.state.home_stats == game.state.away_stats
    assert not outcome.turnover_on_downs and not outcome.turnover


@pytest.mark.parametrize("home", [False, True])
def test_two_point_attempt_matches_ordinary_incomplete_try_without_turnover(teams, home) -> None:
    states = []
    for token in ("BLACK", "F INC"):
        game = PaydirtGameEngine(*deepcopy(teams))
        game.state.is_home_possession = home
        original = (game.state.ball_position, game.state.down, game.state.yards_to_go)
        with selected_cells((token,)) as rolls:
            success, defensive_points, _ = game.attempt_two_point(PlayType.SHORT_PASS, DefenseType.STANDARD)
        assert (success, defensive_points) == (False, 0)
        assert rolls.call_count == 1
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == original
        assert game.state.is_home_possession is home
        assert game.state.home_score == game.state.away_score == 0
        assert game.play_log == [] and game.offensive_call_history == []
        assert game.last_clock_trace.charged_seconds == 0
        states.append(game.state)
    # Both selected incompletion types are untimed tries, outside ordinary logs.
    # The dedicated resolver tests above still assert the retained subtype.
    assert states[0].time_remaining == states[1].time_remaining == 15.0
    assert states[0].home_stats == states[1].home_stats
    assert states[0].away_stats == states[1].away_stats


def test_hail_mary_table_does_not_consume_primary_chart_composite(teams) -> None:
    game = PaydirtGameEngine(*teams)
    game.state.time_remaining = .1
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(30, "30")),
        patch("paydirt.play_resolver.get_offense_result") as primary_lookup,
    ):
        outcome = game.run_play(PlayType.HAIL_MARY, DefenseType.STANDARD)
    primary_lookup.assert_not_called()
    assert outcome.result.result_type == ResultType.INCOMPLETE
    assert getattr(outcome.result, "retained_fumble_incompletion", False) is False
