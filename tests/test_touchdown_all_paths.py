"""
Comprehensive tests for touchdown detection across ALL result types.

Ensures every ResultType that can produce a touchdown is tested through
_apply_play_result (the run_play_with_penalty_procedure code path used
by the interactive game). This prevents regressions where a TD check
is present in run_play but missing in _apply_play_result.
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
    home_chart.peripheral.fumble_recovered_range = (10, 29)
    home_chart.peripheral.fumble_lost_range = (30, 39)
    home_chart.special_teams = MagicMock()
    home_chart.special_teams.interception_return = {20: "10"}

    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"
    away_chart.peripheral.year = 1983
    away_chart.peripheral.fumble_recovered_range = (10, 29)
    away_chart.peripheral.fumble_lost_range = (30, 39)
    away_chart.special_teams = MagicMock()
    away_chart.special_teams.interception_return = {20: "10"}

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


class TestTouchdownViaYards:
    """TD via ResultType.YARDS through penalty procedure path."""

    def test_yards_td_at_goal_line(self, game):
        """YARDS result crossing goal line should score TD."""
        game.state.ball_position = 92  # 8-yard line
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.YARDS, yards=10,
                            description="Gain of 10")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert outcome.touchdown is True

    def test_yards_td_exact_distance(self, game):
        """YARDS result of exactly remaining distance should score TD."""
        game.state.ball_position = 95
        game.state.down = 1
        game.state.yards_to_go = 5
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.YARDS, yards=5,
                            description="Gain of 5")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD)

        assert outcome.touchdown is True

    def test_yards_short_of_goal_no_td(self, game):
        """YARDS result that doesn't reach goal should NOT score TD."""
        game.state.ball_position = 92
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.YARDS, yards=5,
                            description="Gain of 5")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert outcome.touchdown is False


class TestTouchdownViaBreakaway:
    """TD via ResultType.BREAKAWAY through penalty procedure path."""

    def test_breakaway_td(self, game):
        """BREAKAWAY result crossing goal line should score TD."""
        game.state.ball_position = 60
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.BREAKAWAY, yards=45,
                            description="Breakaway for 45!")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.END_RUN, DefenseType.STANDARD)

        assert outcome.touchdown is True


class TestTouchdownViaQBScramble:
    """TD via ResultType.QB_SCRAMBLE through penalty procedure path."""

    def test_qb_scramble_td(self, game):
        """QB_SCRAMBLE crossing goal line should score TD."""
        game.state.ball_position = 92
        game.state.down = 1
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.QB_SCRAMBLE, yards=15,
                            description="QB scramble for 15")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True

    def test_qb_scramble_exact_distance_td(self, game):
        """QB_SCRAMBLE of exact remaining distance should score TD."""
        game.state.ball_position = 97
        game.state.down = 1
        game.state.yards_to_go = 3
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.QB_SCRAMBLE, yards=3,
                            description="QB scramble for 3")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.MEDIUM_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True


class TestTouchdownViaDirect:
    """TD via ResultType.TOUCHDOWN (direct chart result) through penalty procedure path."""

    def test_direct_td_result(self, game):
        """ResultType.TOUCHDOWN should always score TD."""
        game.state.ball_position = 70
        game.state.down = 2
        game.state.yards_to_go = 5
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.TOUCHDOWN, yards=30,
                            description="TOUCHDOWN!", touchdown=True)
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LONG_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True

    def test_direct_td_from_own_territory(self, game):
        """Direct TD result from deep in own territory should still score."""
        game.state.ball_position = 20
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.TOUCHDOWN, yards=80,
                            description="TOUCHDOWN!", touchdown=True)
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LONG_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True


class TestTouchdownViaInterception:
    """Defensive TD via interception through penalty procedure path."""

    def test_interception_in_offense_end_zone_td(self, game):
        """INT in offense's end zone (raw_spot <= 0) should be defensive TD."""
        game.state.ball_position = 5  # near own goal line
        game.state.down = 2
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        # INT with negative yards = behind offense's goal line
        result = PlayResult(result_type=ResultType.INTERCEPTION, yards=-10,
                            description="Intercepted!")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True
        assert outcome.turnover is True

    def test_interception_return_td(self, game):
        """INT with return to end zone should be defensive TD."""
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        # INT at the 60 (50 + 10), defense gets ball at their 40 (100 - 60)
        # Return of "TD" should score
        result = PlayResult(result_type=ResultType.INTERCEPTION, yards=10,
                            description="Intercepted!")

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp, \
             patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_rpp.return_value = _no_penalty_choice(result)
            # Return dice roll
            mock_dice.return_value = (20, "B2+W0+W0=20")
            # Make INT return chart return "TD"
            game.state.defense_team.special_teams.interception_return = {20: "TD"}

            outcome = game.run_play_with_penalty_procedure(
                PlayType.LONG_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is True
        assert outcome.turnover is True


class TestTouchdownViaFumble:
    """TD via fumble recovery through penalty procedure path."""

    def test_fumble_in_end_zone_offense_recovers_td(self, game):
        """Offense fumble into end zone + offense recovers = TD."""
        game.state.ball_position = 95
        game.state.down = 1
        game.state.yards_to_go = 5
        game.state.is_home_possession = True

        # Fumble at spot 95 + 8 = 103 (in end zone)
        result = PlayResult(result_type=ResultType.FUMBLE, yards=8,
                            description="Fumble!")

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp, \
             patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_rpp.return_value = _no_penalty_choice(result)
            # Recovery roll 15 = offense recovers (range 10-29)
            mock_dice.return_value = (15, "B1+W0+W5=15")

            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD)

        assert outcome.touchdown is True

    def test_fumble_in_own_end_zone_defense_recovers_td(self, game):
        """Fumble in offense's own end zone + defense recovers = defensive TD."""
        game.state.ball_position = 3
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        # Fumble at spot 3 + (-5) = -2 (behind own goal)
        result = PlayResult(result_type=ResultType.FUMBLE, yards=-5,
                            description="Fumble!")

        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_rpp, \
             patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_rpp.return_value = _no_penalty_choice(result)
            # Recovery roll 35 = defense recovers (outside 10-29)
            mock_dice.return_value = (35, "B3+W0+W5=35")

            outcome = game.run_play_with_penalty_procedure(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert outcome.touchdown is True
        assert outcome.turnover is True


class TestNoFalseTouchdowns:
    """Verify that non-TD situations don't incorrectly score."""

    def test_incomplete_no_td(self, game):
        """Incomplete pass should never be a TD."""
        game.state.ball_position = 99
        game.state.down = 1
        game.state.yards_to_go = 1
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.INCOMPLETE, yards=0,
                            description="Incomplete")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.SHORT_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is False

    def test_sack_no_td(self, game):
        """Sack should never be a TD (even from opponent's 1)."""
        game.state.ball_position = 99
        game.state.down = 1
        game.state.yards_to_go = 1
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.SACK, yards=-5,
                            description="Sacked for 5 yard loss")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LONG_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is False
        assert game.state.ball_position == 94

    def test_zero_yards_no_td(self, game):
        """Zero-yard gain at goal line should NOT be a TD."""
        game.state.ball_position = 99
        game.state.down = 1
        game.state.yards_to_go = 1
        game.state.is_home_possession = True

        result = PlayResult(result_type=ResultType.YARDS, yards=0,
                            description="No gain")
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock:
            mock.return_value = _no_penalty_choice(result)
            outcome = game.run_play_with_penalty_procedure(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD)

        assert outcome.touchdown is False
