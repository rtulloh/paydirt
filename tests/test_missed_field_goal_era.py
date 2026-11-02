"""RULE-024: missed kicks use the possession spot for the season's rules."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("declined", [True, False])
@pytest.mark.parametrize("year,position,expected", [
    (1973, 65, 20), (1974, 65, 35), (1983, 65, 35), (1993, 65, 35),
    (1994, 65, 42), (2026, 65, 42),
    (1983, 85, 20), (2026, 85, 22), (2026, 95, 20),
])
def test_missed_field_goal_uses_era_spot(
    home: bool, declined: bool, year: int, position: int, expected: int,
) -> None:
    game = make_sample_game()
    game.season_rules.season = year  # Synthetic era; no historical charts loaded.
    state = game.state
    state.is_home_possession = home
    state.quarter, state.time_remaining = 4, 4.2
    state.ball_position, state.down, state.yards_to_go = position, 4, 8
    state.possession_team.special_teams.field_goal.update({10: "DEF 5", 29: "0"})
    rolls = [10, 29] if declined else [29]
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
        (roll, f"Synthetic {roll}") for roll in rolls
    ]), patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
        if declined:
            assert outcome.pending_penalty_decision
            assert state.ball_position == position
            outcome = game.apply_fg_penalty_decision(outcome, accept_play=True)
    assert state.ball_position == expected
    assert state.is_home_possession is not home
    assert (state.down, state.yards_to_go) == (1, 10)
    assert not outcome.field_goal_made
    assert not state.scoring_plays
    assert state.home_stats.penalties == state.away_stats.penalties == 0
