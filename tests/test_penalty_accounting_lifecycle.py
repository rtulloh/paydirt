"""STAT-005 investigation: the narrated foul sequence must reconcile.

This synthetic lifecycle is not a replay of the uncaptured manual-game RNG.
"""

from unittest.mock import patch

import pytest

from paydirt.interactive_game import handle_penalty_decision
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("human_home", [False, True])
def test_penalties_reconcile_across_halftime_return_and_rekick(human_home, monkeypatch, capsys) -> None:
    game = make_sample_game()
    state = game.state
    state.is_home_possession = human_home
    state.ball_position, state.down, state.yards_to_go = 35, 2, 10
    state.quarter, state.time_remaining = 2, 5 / 60
    offender = state.possession_team
    other = state.defense_team
    offender.offense.short_pass.update({10: "OFF 10", 29: "6"})
    other.defense.modifiers[("A", 1)] = {6: "0"}
    with (
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(10, "Foul"), (29, "Play")]),
        patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)),
    ):
        pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    game.apply_penalty_decision(pending, accept_play=False)
    assert state.quarter == 3
    stats = state.home_stats if human_home else state.away_stats
    assert (stats.penalties, stats.penalty_yards) == (1, 10)

    other.special_teams.kickoff[36] = "51"
    offender.special_teams.kickoff_return.update({14: "OFF 15", 22: "22"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(36, "Kick"), (14, "Foul"), (22, "Return")]):
        outcome = game.kickoff(kicking_home=not human_home)
    assert state.ball_position == 21
    assert (stats.penalties, stats.penalty_yards) == (2, 25)
    assert "OFF 15" in outcome.description

    state.quarter, state.time_remaining = 4, 12.9
    state.ball_position = 100  # Previous touchdown; kick establishes a new spot.
    offender.special_teams.kickoff.update({10: "DEF 5", 18: "66", 28: "65"})
    other.special_teams.kickoff_return.update({32: "14", 34: "16"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Foul"), (18, "Kick"), (32, "Return")]):
        pending = game.kickoff(kicking_home=human_home)
    assert (stats.penalties, stats.penalty_yards) == (2, 25)
    monkeypatch.setattr("builtins.input", lambda *args: "2")
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(28, "Rekick"), (34, "Return")]):
        final = handle_penalty_decision(game, pending, True, not human_home)
    assert not final.pending_penalty_decision
    assert state.ball_position == 21
    assert (stats.penalties, stats.penalty_yards) == (3, 30)
    # Submitting a stale decision must not assess the foul again.
    game.apply_kickoff_penalty_decision(pending, accept_penalty=True)
    assert (stats.penalties, stats.penalty_yards) == (3, 30)
    other_stats = state.away_stats if human_home else state.home_stats
    assert other_stats.penalties == other_stats.penalty_yards == 0
    assert "Kickoff Result" in capsys.readouterr().out
