"""
Regression tests for OOB/IB deduction and QB_SCRAMBLE TD detection
via the run_play_with_penalty_procedure -> _apply_play_result code path.

The existing OOB tests only exercise run_play() directly. The interactive
game uses run_play_with_penalty_procedure() which delegates to
_apply_play_result() — a separate method that was missing both the
OOB 5-yard deduction and the QB_SCRAMBLE touchdown check.
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.play_resolver import (
    PlayType, DefenseType, ResultType, PlayResult, PenaltyChoice,
)
from paydirt.game_engine import PaydirtGameEngine


@pytest.fixture
def game():
    """Create a game engine with mock team charts."""
    home_chart = MagicMock()
    away_chart = MagicMock()

    home_chart.peripheral = MagicMock()
    home_chart.peripheral.team_name = "Home Team"
    home_chart.peripheral.short_name = "HOM"
    home_chart.peripheral.year = 1983
    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"
    away_chart.peripheral.year = 1983

    game = PaydirtGameEngine(home_chart, away_chart)
    return game


def _no_penalty_choice(play_result):
    """Create a PenaltyChoice with no penalties (normal play path)."""
    return PenaltyChoice(
        play_result=play_result,
        penalty_options=[],
        offended_team="",
        offsetting=False,
    )


class TestOOBDeductionViaPenaltyProcedure:
    """OOB 5-yard deduction must work through run_play_with_penalty_procedure."""

    def test_oob_subtracts_5_yards(self, game):
        """OOB designation subtracts 5 yards from a normal gain."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=12,
            description="Gain of 12 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.yards_gained == 7, \
            "OOB should reduce 12 to 7 (12 - 5)"
        assert "Out of Bounds designation" in outcome.description

    def test_oob_minimum_zero(self, game):
        """OOB deduction should not make yardage negative."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=3,
            description="Gain of 3 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.yards_gained == 0, \
            "OOB should reduce 3 to 0 (max(0, 3-5))"

    def test_oob_not_applied_to_incomplete(self, game):
        """OOB deduction should NOT apply to incomplete passes."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.INCOMPLETE,
            yards=0,
            description="Incomplete pass",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LONG_PASS, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.yards_gained == 0
        assert "Out of Bounds designation" not in outcome.description

    def test_oob_not_applied_to_touchdown_result(self, game):
        """OOB deduction should NOT apply to ResultType.TOUCHDOWN."""
        game.state.ball_position = 95
        game.state.down = 1
        game.state.yards_to_go = 5
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.TOUCHDOWN,
            yards=10,
            description="TOUCHDOWN!",
            touchdown=True,
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.touchdown is True
        assert "Out of Bounds designation" not in outcome.description

    def test_oob_not_applied_to_already_oob(self, game):
        """OOB deduction should NOT apply if play was already out of bounds."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=15,
            description="Gain of 15 yards (out of bounds)",
            out_of_bounds=True,
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.END_RUN, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.yards_gained == 15, \
            "Already-OOB plays should keep full yardage"

    def test_oob_applied_to_qb_scramble(self, game):
        """OOB deduction should apply to QB scrambles with positive yards."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=15,
            description="QB scramble for 15 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        assert outcome.yards_gained == 10, \
            "OOB should reduce QB scramble 15 to 10 (15 - 5)"
        assert "Out of Bounds designation" in outcome.description


class TestQBScrambleTouchdownViaPenaltyProcedure:
    """QB_SCRAMBLE that crosses the goal line must score a TD."""

    def test_qb_scramble_td_from_8_yard_line(self, game):
        """QB scramble of 15 from the 8-yard line should be a touchdown.

        This is the exact bug from the user report: 1st & Goal @ LAC 8,
        Short Pass result QT (QB Take-off) for +15, but no TD was scored.
        """
        game.state.ball_position = 92  # opponent's 8-yard line
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=15,
            description="QB scramble for 15 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
            )

        assert outcome.touchdown is True, \
            "QB scramble of 15 from the 8-yard line must score a touchdown"

    def test_qb_scramble_td_with_oob_deduction(self, game):
        """QB scramble TD should still score even with OOB 5-yard deduction.

        From the 8: 15 - 5 (OOB) = 10 yards, still enough to score.
        """
        game.state.ball_position = 92  # opponent's 8-yard line
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=15,
            description="QB scramble for 15 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                out_of_bounds_designation=True,
            )

        # 15 - 5 = 10, from the 8 that's still a TD
        assert outcome.touchdown is True, \
            "QB scramble of 10 (after OOB) from 8-yard line must score"

    def test_qb_scramble_td_exact_distance(self, game):
        """QB scramble of exactly the remaining distance should be a TD."""
        game.state.ball_position = 95  # opponent's 5-yard line
        game.state.down = 1
        game.state.yards_to_go = 5
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=5,
            description="QB scramble for 5 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.MEDIUM_PASS, DefenseType.STANDARD,
            )

        assert outcome.touchdown is True

    def test_qb_scramble_short_of_goal_no_td(self, game):
        """QB scramble that doesn't reach the goal should NOT be a TD."""
        game.state.ball_position = 92  # opponent's 8-yard line
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=5,
            description="QB scramble for 5 yards",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
            )

        assert outcome.touchdown is False
        assert game.state.ball_position == 97  # 92 + 5

    def test_qb_scramble_safety_still_works(self, game):
        """QB scramble backward past own goal should still be a safety."""
        game.state.ball_position = 3  # own 3-yard line
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        play_result = PlayResult(
            result_type=ResultType.QB_SCRAMBLE,
            yards=-5,
            description="QB scramble for loss of 5",
        )

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp:
            mock_rpp.return_value = _no_penalty_choice(play_result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.MEDIUM_PASS, DefenseType.STANDARD,
            )

        assert outcome.safety is True
