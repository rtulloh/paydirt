"""RULE-005: only an accepted defensive (or offsetting) kick foul extends a half.

An accepted *offensive* foul on a field-goal attempt replays the down and charges
its normal scrimmage interval. It must not set ``untimed_down_pending``: that
flag belongs to the defensive-foul rule, and a stale flag outlives the play,
survives the next change of possession and grants a free snap at 0:00.
"""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    DefenseType,
    FieldGoalResult,
    PenaltyOption,
    PlayType,
)
from tests.game_fixtures import make_sample_game


@pytest.fixture(params=[False, True], ids=["away-kicking", "home-kicking"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    """Q3, 0:24 left, 4th & 8 on the opponent's 32 - the reported play."""
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.ball_position = 68
    engine.state.down, engine.state.yards_to_go = 4, 8
    engine.state.quarter, engine.state.time_remaining = 3, 24 / 60
    engine.state.two_minute_warning_called = True
    engine.state.home_score = engine.state.away_score = 10
    return engine


def foul(yards: int = 5, kind: str = "OFF") -> PenaltyOption:
    return PenaltyOption(kind, f"{kind} {yards}", yards, "synthetic kick foul")


def pending_kick(
    game: PaydirtGameEngine, *options: PenaltyOption, offsetting: bool = False,
) -> object:
    result = FieldGoalResult(
        dice_roll=21, dice_desc="B2+W0+W1=21", raw_result="32", chart_yards=32,
        is_penalty=True, penalty_options=list(options), offsetting=offsetting,
        offended_team="defense" if options and options[0].penalty_type == "OFF" else "offense",
        reroll_log=[],
    )
    with patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=result):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.pending_penalty_decision is (not offsetting)
    return outcome


def test_accepted_offensive_foul_does_not_extend_the_period(game: PaydirtGameEngine) -> None:
    """The reported Q3 0:24 foul must end the quarter, not create a free down."""
    outcome = pending_kick(game, foul(5))
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        final = game.apply_fg_penalty_decision(deepcopy(outcome), accept_play=False)

    assert final.penalty_applied
    assert "UNTIMED DOWN" not in final.description.upper()
    assert "HALF EXTENDED" not in final.description.upper()
    assert not game.has_untimed_down()
    # 24 seconds remain and an enforced replay costs 25-45 seconds.
    assert game.state.quarter == 4 and game.state.time_remaining == 15.0


def test_accepted_offensive_foul_charges_the_replay_interval(game: PaydirtGameEngine) -> None:
    """The replay is not free: the clock still runs down from 0:24."""
    game.state.time_remaining = 90 / 60
    outcome = pending_kick(game, foul(5))
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        game.apply_fg_penalty_decision(deepcopy(outcome), accept_play=False)

    assert game.state.quarter == 3
    assert game.state.time_remaining == pytest.approx(45 / 60)
    assert not game.has_untimed_down()


def test_no_phantom_snap_after_the_next_change_of_possession(game: PaydirtGameEngine) -> None:
    """A stale extension previously survived a punt and granted a free play."""
    outcome = pending_kick(game, foul(5))
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        game.apply_fg_penalty_decision(deepcopy(outcome), accept_play=False)

    # Quarter is over; the next punt starts the fourth quarter with time running.
    assert game.state.quarter == 4
    game.state.defense_team.special_teams.punt.update({12: "41"})
    with patch("paydirt.play_resolver.roll_chart_dice", return_value=(12, "41")), \
         patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        game.run_play(PlayType.PUNT, DefenseType.STANDARD)

    assert not game.has_untimed_down()
    assert game.state.time_remaining > 0


def test_offensive_foul_in_the_fourth_quarter_still_ends_regulation(
    game: PaydirtGameEngine,
) -> None:
    """A stale flag must not suppress game-over at 0:00 of the fourth quarter."""
    possession = game.state.is_home_possession
    game.state.quarter = 4
    game.state.home_score, game.state.away_score = (10, 3) if possession else (3, 10)
    outcome = pending_kick(game, foul(5))
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        game.apply_fg_penalty_decision(deepcopy(outcome), accept_play=False)

    assert not game.has_untimed_down()
    assert game.state.time_remaining == 0
    assert game.state.game_over is True


def test_accepted_defensive_foul_still_extends_the_period(game: PaydirtGameEngine) -> None:
    """Control: the defensive-foul rule is unchanged by dropping the OFF branch."""
    outcome = pending_kick(game, foul(5, kind="DEF"))
    with patch("paydirt.game_engine.random.uniform", side_effect=lambda low, high: high):
        final = game.apply_fg_penalty_decision(deepcopy(outcome), accept_play=False)

    assert "(Untimed down)" in final.description
    assert game.has_untimed_down()
    assert game.state.quarter == 3 and game.state.time_remaining == 0


def test_offsetting_field_goal_fouls_preserve_an_untimed_down(
    game: PaydirtGameEngine,
) -> None:
    """Control: offsetting fouls nullify the kick and extend an expired period."""
    game.state.time_remaining = 3 / 60
    outcome = pending_kick(game, foul(5), foul(15, kind="DEF"), offsetting=True)
    final = game.apply_fg_penalty_decision(outcome, accept_play=False)

    assert game.has_untimed_down()
    assert "UNTIMED DOWN" in final.description.upper()
    assert game.state.quarter == 3 and game.state.time_remaining == 0


def test_cli_untimed_down_banner_is_not_limited_to_defensive_fouls() -> None:
    """Offsetting kick fouls also extend the period, so the banner must not mislabel them."""
    from paydirt import interactive_game as cli

    notice = cli.untimed_down_notice()
    text = "\n".join(notice).lower()
    assert "untimed down" in text
    assert "defensive penalty" not in text
    assert "accepted penalty" in text or "accepted foul" in text


def test_cli_untimed_down_banner_explains_the_extension() -> None:
    from paydirt import interactive_game as cli

    joined = " ".join(cli.untimed_down_notice())
    assert "cannot end" in joined.lower()
