"""Clock invariants must reject the RULE-005 class of silent rule bug.

These drive the real engine so the observer is validated against the same
transitions it watches in the audit: an accepted offensive field-goal foul, an
accepted defensive foul, offsetting fouls, a punt-return foul (whose chart label
reverses), and ordinary charged replays.
"""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest

import paydirt.game_engine as ge
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    FieldGoalResult,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.clock_invariants import ClockInvariantAudit
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[False, True], ids=["away-kicking", "home-kicking"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    """Q3 0:24, 4th & 8 on the opponent's 32 - the reported RULE-005 play."""
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 68, 4, 8
    engine.state.quarter, engine.state.time_remaining = 3, 24 / 60
    engine.state.two_minute_warning_called = True
    engine.state.home_score = engine.state.away_score = 10
    return engine


def foul(yards: int = 5, kind: str = "OFF") -> PenaltyOption:
    return PenaltyOption(kind, f"{kind} {yards}", yards, "synthetic kick foul")


def kick(game: PaydirtGameEngine, *options: PenaltyOption) -> object:
    result = FieldGoalResult(
        dice_roll=21, dice_desc="B2+W0+W1=21", raw_result="32", chart_yards=32,
        is_penalty=True, penalty_options=list(options), offsetting=False,
        offended_team="defense", reroll_log=[],
    )
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=result):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision
    return outcome


def observe(audit: ClockInvariantAudit, game: PaydirtGameEngine, outcome,
            index: int = 0) -> None:
    """Mirror the audit's hooks: decision window, accepted foul, then result."""
    audit.decision(game)
    audit.penalty(outcome, (False, index))


def test_accepted_offensive_kick_foul_charges_its_replay(
    game: PaydirtGameEngine,
) -> None:
    """The exact RULE-005 shape: the replay is timed and never extends the half."""
    audit = ClockInvariantAudit()
    outcome = kick(game, foul(5))
    observe(audit, game, outcome)
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        final = game.apply_fg_penalty_decision(deepcopy(outcome), False, 0)

    audit.result(game, final)
    assert audit.counts["period_extension"] == 0
    assert audit.counts["charged_replay"] == 1
    assert audit.counts["accepted_foul"] == 1


def test_observer_rejects_a_reintroduced_offensive_extension(
    game: PaydirtGameEngine,
) -> None:
    """Control: if the old direct flag returns, the observer must raise."""
    audit = ClockInvariantAudit()
    outcome = kick(game, foul(5))
    observe(audit, game, outcome)
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        final = game.apply_fg_penalty_decision(deepcopy(outcome), False, 0)

    # Re-create exactly what the pre-fix code did: set the flag with no hold.
    game.state.untimed_down_pending = True
    with pytest.raises(ValueError, match="without a defensive-foul clock hold"):
        audit.result(game, final)


def test_observer_rejects_a_replay_that_charges_no_clock(game: PaydirtGameEngine) -> None:
    """Control: the old code also suppressed the replay's clock charge."""
    audit = ClockInvariantAudit()
    outcome = kick(game, foul(5))
    observe(audit, game, outcome)
    outcome.penalty_applied = True
    outcome.clock_trace = None
    with pytest.raises(ValueError, match="charged no clock time"):
        audit.result(game, outcome)


def test_accepted_defensive_kick_foul_extension_is_allowed(game: PaydirtGameEngine) -> None:
    """Control: a defensive foul may extend the period through the engine hold."""
    game.state.time_remaining = 3 / 60
    audit = ClockInvariantAudit()
    outcome = kick(game, foul(5, kind="DEF"))
    observe(audit, game, outcome)

    original = ge.PaydirtGameEngine._use_time

    def observed(engine, seconds, out_of_bounds=False, *, defensive_penalty=False):
        audit.charge(engine, defensive_penalty)
        return original(engine, seconds, out_of_bounds, defensive_penalty=defensive_penalty)

    with patch.object(ge.PaydirtGameEngine, "_use_time", observed), \
         patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        final = game.apply_fg_penalty_decision(deepcopy(outcome), False, 0)

    assert game.has_untimed_down()
    audit.result(game, final)
    assert audit.counts["period_extension"] == 1


def test_offsetting_fouls_may_extend_the_period(game: PaydirtGameEngine) -> None:
    """Control: offsetting fouls extend an expired period legitimately."""
    game.state.time_remaining = 3 / 60
    audit = ClockInvariantAudit()
    audit.decision(game)
    result = FieldGoalResult(
        dice_roll=21, dice_desc="B2+W0+W1=21", raw_result="32", chart_yards=32,
        is_penalty=True, penalty_options=[foul(5), foul(15, kind="DEF")],
        offsetting=True, offended_team="", reroll_log=[],
    )
    original = ge.PaydirtGameEngine._use_time

    def observed(engine, seconds, out_of_bounds=False, *, defensive_penalty=False):
        audit.charge(engine, defensive_penalty)
        return original(engine, seconds, out_of_bounds, defensive_penalty=defensive_penalty)

    with patch.object(ge.PaydirtGameEngine, "_use_time", observed), \
         patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=result):
        final = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)

    audit.penalty(final, (False, 0))
    assert game.has_untimed_down()
    audit.result(game, final)
    assert audit.counts["period_extension"] == 1


@pytest.mark.parametrize("possession_home", [False, True], ids=["away-punting", "home-punting"])
def test_return_foul_extends_even_though_the_chart_says_off(
    possession_home: bool,
) -> None:
    """A kicking team's return foul is a defensive foul, so it may extend.

    The chart's ``OFF`` label is relative to the punt chart's offense. On the
    return the kicking team is the defense, so this extension is legitimate.
    An invariant that keyed on the chart label alone would wrongly reject it.
    """
    game = make_sample_game()
    game.state.is_home_possession = possession_home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 3 / 60
    game.state.possession_team.special_teams.punt = {10: "40", 14: "40"}
    game.state.defense_team.special_teams.punt_return = {11: "OFF 10", 12: "DEF 15", 15: "3"}

    audit = ClockInvariantAudit()
    audit.decision(game)
    original = ge.PaydirtGameEngine._use_time

    def observed(engine, seconds, out_of_bounds=False, *, defensive_penalty=False):
        audit.charge(engine, defensive_penalty)
        return original(engine, seconds, out_of_bounds, defensive_penalty=defensive_penalty)

    with patch.object(ge.PaydirtGameEngine, "_use_time", observed), \
         patch("paydirt.game_engine.roll_chart_dice",
               side_effect=[(n, str(n)) for n in [10, 11, 12, 14, 15]]), \
         patch("paydirt.game_engine.random.uniform", return_value=8):
        final = game.run_play(PlayType.PUNT, DefenseType.STANDARD)

    assert game.has_untimed_down(), final.description
    audit.result(game, final)
    assert audit.counts["period_extension"] == 1


def test_ordinary_scrimmage_replay_is_counted(game: PaydirtGameEngine) -> None:
    """Control: a normal scrimmage foul keeps its clock charge and is counted."""
    game.state.time_remaining = 1.0
    game.state.quarter = 1
    audit = ClockInvariantAudit()
    audit.decision(game)

    result = PlayResult(ResultType.YARDS, yards=3, raw_result="3", description="3 yards")
    choice = PenaltyChoice(
        play_result=result, penalty_options=[foul(5, kind="DEF")], offended_team="offense",
    )
    outcome = PlayOutcome(
        play_type=PlayType.OFF_TACKLE,
        defense_type=DefenseType.STANDARD,
        result=result,
        yards_gained=3,
        field_position_before=game.state.field_position_str(),
        field_position_after=game.state.field_position_str(),
        description=result.description,
        penalty_choice=choice,
        pending_penalty_decision=True,
    )

    audit.penalty(outcome, (False, 0))
    assert audit.counts["accepted_foul"] == 1

    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        applied = game.apply_penalty_decision(deepcopy(outcome), False, 0)

    assert applied.penalty_applied
    audit.result(game, applied)
    assert audit.counts["charged_replay"] == 1
    assert audit.counts["period_extension"] == 0
