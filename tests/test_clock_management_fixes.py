"""
Tests for clock management fixes:
1. OOB designation (+) forces 10-second timing in ALL quarters (not just final minutes)
2. No-huddle reduces play time from ~40 sec to ~20 sec

Bug context:
- OOB designation (+) previously only worked in Q2 <=2:00 and Q4 <=5:00 because
  it relied on _use_time's in_final_minutes gate. Players paid 5 yards for no benefit
  in Q1/Q3.
- No-huddle flag was purely cosmetic — toggled in UI but never passed to game engine.
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult
from paydirt.game_engine import PaydirtGameEngine


@pytest.fixture
def game():
    """Create a game engine with mock team charts."""
    home_chart = MagicMock()
    away_chart = MagicMock()

    home_chart.peripheral = MagicMock()
    home_chart.peripheral.team_name = "Home Team"
    home_chart.peripheral.short_name = "HOM"
    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"

    game = PaydirtGameEngine(home_chart, away_chart)
    return game


def _make_yards_result(yards=8, out_of_bounds=False):
    """Helper to create a simple yardage PlayResult."""
    return PlayResult(
        result_type=ResultType.YARDS,
        yards=yards,
        description=f"Gain of {yards} yards",
        out_of_bounds=out_of_bounds,
    )


def _make_sack_result(yards=-5):
    """Helper to create a sack PlayResult."""
    return PlayResult(
        result_type=ResultType.SACK,
        yards=yards,
        description=f"Sacked for {abs(yards)} yard loss",
    )


# ---------------------------------------------------------------------------
# OOB designation (+) forces 10-sec timing in ALL quarters
# ---------------------------------------------------------------------------
class TestOOBDesignationForces10SecAllQuarters:
    """OOB designation (+) should always use exactly 10 seconds, regardless of quarter."""

    def test_oob_designation_q1_forces_10_sec(self, game):
        """In Q1 (not final minutes), + should still force exactly 10 seconds."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_q2_early_forces_10_sec(self, game):
        """In Q2 with >2:00 remaining (not final minutes), + should still force 10 sec."""
        game.state.quarter = 2
        game.state.time_remaining = 8.0  # 8 minutes left, well outside 2-minute window
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True)

        time_used_min = 8.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_q3_forces_10_sec(self, game):
        """In Q3 (never final minutes), + should still force exactly 10 seconds."""
        game.state.quarter = 3
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True)

        time_used_min = 5.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_q4_early_forces_10_sec(self, game):
        """In Q4 with >5:00 remaining (not final minutes), + should still force 10 sec."""
        game.state.quarter = 4
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_q2_final_minutes_still_10_sec(self, game):
        """In Q2 final minutes, + should also be 10 sec (same as natural OOB)."""
        game.state.quarter = 2
        game.state.time_remaining = 1.5  # Within 2-minute window
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True)

        time_used_min = 1.5 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_sack_does_not_force_10_sec(self, game):
        """Sack with + should NOT force 10-sec (QB can't choose to go OOB if sacked)."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_sack_result()):
            with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD,
                              out_of_bounds_designation=True)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        # Should use full 30 seconds, not 10
        assert time_used_sec == pytest.approx(30.0, abs=0.1)

    def test_in_bounds_designation_overrides_oob(self, game):
        """In-bounds designation (-) should override + and use normal timing."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                              out_of_bounds_designation=True,
                              in_bounds_designation=True)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        # In-bounds overrides OOB; should use normal 30 seconds
        assert time_used_sec == pytest.approx(30.0, abs=0.1)


class TestOOBDesignationPenaltyProcedurePath:
    """OOB designation should also force 10-sec via _apply_play_result (penalty path)."""

    def test_oob_designation_penalty_path_q1_forces_10_sec(self, game):
        """+ through penalty procedure path should also force 10-sec in Q1."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = _make_yards_result()
        game._apply_play_result(
            PlayType.SHORT_PASS, DefenseType.STANDARD, result,
            "OWN 50", 1, 50, 10,
            out_of_bounds_designation=True, in_bounds_designation=False,
        )

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_oob_designation_penalty_path_q3_forces_10_sec(self, game):
        """+ through penalty procedure path should also force 10-sec in Q3."""
        game.state.quarter = 3
        game.state.time_remaining = 7.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = _make_yards_result()
        game._apply_play_result(
            PlayType.SHORT_PASS, DefenseType.STANDARD, result,
            "OWN 50", 1, 50, 10,
            out_of_bounds_designation=True, in_bounds_designation=False,
        )

        time_used_min = 7.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)


# ---------------------------------------------------------------------------
# Natural * OOB marker still respects in_final_minutes gate
# ---------------------------------------------------------------------------
class TestNaturalOOBMarkerStillGated:
    """Natural * markers from chart should only give 10-sec in final minutes."""

    def test_natural_oob_q1_uses_normal_timing(self, game):
        """Chart * marker in Q1 should NOT force 10-sec (not final minutes)."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play',
                    return_value=_make_yards_result(out_of_bounds=True)):
            with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        # Natural OOB in Q1 = normal timing
        assert time_used_sec == pytest.approx(30.0, abs=0.1)

    def test_natural_oob_q4_final_minutes_uses_10_sec(self, game):
        """Chart * marker in Q4 final minutes should use 10 sec."""
        game.state.quarter = 4
        game.state.time_remaining = 3.0  # Within 5-minute window
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play',
                    return_value=_make_yards_result(out_of_bounds=True)):
            with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        time_used_min = 3.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        # Natural OOB in final minutes = 10 sec
        assert time_used_sec == pytest.approx(10.0, abs=0.1)


# ---------------------------------------------------------------------------
# No-huddle reduces play time
# ---------------------------------------------------------------------------
class TestNoHuddleReducesPlayTime:
    """No-huddle should reduce play time from ~40 sec to ~20 sec."""

    def test_no_huddle_reduces_time_via_run_play(self, game):
        """No-huddle through run_play should use random.uniform(5, 20)."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            with patch('paydirt.game_engine.random.uniform', return_value=15.0) as mock_rand:
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                              no_huddle=True)

        # Verify random.uniform was called with (5, 20) range
        mock_rand.assert_called_with(5, 20)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(15.0, abs=0.1)

    def test_normal_play_uses_full_range(self, game):
        """Without no-huddle, play time should use random.uniform(5, 40)."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            with patch('paydirt.game_engine.random.uniform', return_value=25.0) as mock_rand:
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                              no_huddle=False)

        mock_rand.assert_called_with(5, 40)

    def test_no_huddle_penalty_procedure_path(self, game):
        """No-huddle through _apply_play_result should also reduce time."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = _make_yards_result()
        with patch('paydirt.game_engine.random.uniform', return_value=15.0) as mock_rand:
            game._apply_play_result(
                PlayType.SHORT_PASS, DefenseType.STANDARD, result,
                "OWN 50", 1, 50, 10,
                out_of_bounds_designation=False, in_bounds_designation=False,
                no_huddle=True,
            )

        mock_rand.assert_called_with(5, 20)

    def test_no_huddle_default_false_in_apply_play_result(self, game):
        """_apply_play_result defaults no_huddle=False (backwards compatible)."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = _make_yards_result()
        with patch('paydirt.game_engine.random.uniform', return_value=25.0) as mock_rand:
            game._apply_play_result(
                PlayType.SHORT_PASS, DefenseType.STANDARD, result,
                "OWN 50", 1, 50, 10,
                out_of_bounds_designation=False, in_bounds_designation=False,
            )

        mock_rand.assert_called_with(5, 40)


# ---------------------------------------------------------------------------
# Interaction: OOB designation + No-huddle
# ---------------------------------------------------------------------------
class TestOOBDesignationOverridesNoHuddle:
    """OOB designation should force exactly 10 sec, overriding no-huddle range."""

    def test_oob_plus_no_huddle_uses_10_sec(self, game):
        """With both + and no-huddle, 10-sec from + takes priority."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
            game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD,
                          out_of_bounds_designation=True,
                          no_huddle=True)

        time_used_min = 10.0 - game.state.time_remaining
        time_used_sec = time_used_min * 60
        assert time_used_sec == pytest.approx(10.0, abs=0.1)

    def test_sack_with_oob_and_no_huddle_uses_no_huddle_range(self, game):
        """Sack ignores + but no-huddle should still apply reduced timing."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        with patch('paydirt.game_engine.resolve_play', return_value=_make_sack_result()):
            with patch('paydirt.game_engine.random.uniform', return_value=15.0) as mock_rand:
                game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD,
                              out_of_bounds_designation=True,
                              no_huddle=True)

        # Sack ignores OOB designation, falls through to no_huddle range
        mock_rand.assert_called_with(5, 20)


# ---------------------------------------------------------------------------
# run_play_with_penalty_procedure passes no_huddle through
# ---------------------------------------------------------------------------
class TestPenaltyProcedurePassesNoHuddle:
    """run_play_with_penalty_procedure should pass no_huddle to run_play."""

    def test_penalty_procedure_passes_no_huddle_to_run_play(self, game):
        """Special teams plays route through run_play; no_huddle should be forwarded."""
        game.state.quarter = 1
        game.state.time_remaining = 10.0
        game.state.ball_position = 99
        game.state.down = 1
        game.state.yards_to_go = 1
        game.state.is_home_possession = True

        with patch.object(game, 'run_play', wraps=game.run_play) as mock_run_play:
            with patch('paydirt.game_engine.resolve_play', return_value=_make_yards_result()):
                # QB_SNEAK goes through run_play directly (special teams path)
                game.run_play_with_penalty_procedure(
                    PlayType.QB_SNEAK, DefenseType.STANDARD,
                    no_huddle=True,
                )

        # Verify no_huddle=True was passed to run_play
        assert mock_run_play.called
        call_kwargs = mock_run_play.call_args
        assert call_kwargs.kwargs.get('no_huddle') is True or \
               (len(call_kwargs.args) > 6 and call_kwargs.args[6] is True)
