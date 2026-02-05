"""
Tests for asterisk (*) and dagger (†) out-of-bounds timing rules.

Official rules:
- Asterisk and dagger indicate play ended out of bounds
- Normal timing applies EXCEPT in last 2 minutes of 1st half and last 5 minutes of 2nd half
- In those final minutes, only 10 seconds elapse on out-of-bounds plays
- Play is NOT out of bounds if defense overrules or if play results in fumble
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult, parse_result_string


class TestOutOfBoundsParsing:
    """Tests for parsing asterisk and dagger markers."""
    
    def test_asterisk_detected(self):
        """Asterisk should be detected as out of bounds."""
        result = parse_result_string("5*")
        assert result.out_of_bounds is True
        assert result.yards == 5
    
    def test_dagger_detected(self):
        """Dagger (†) should be detected as out of bounds."""
        result = parse_result_string("8†")
        assert result.out_of_bounds is True
        assert result.yards == 8
    
    def test_plus_detected_as_out_of_bounds(self):
        """Plus sign should be detected as out of bounds (alternate marker)."""
        result = parse_result_string("3+")
        assert result.out_of_bounds is True
        assert result.yards == 3
    
    def test_no_marker_not_out_of_bounds(self):
        """Result without marker should not be out of bounds."""
        result = parse_result_string("5")
        assert result.out_of_bounds is False
        assert result.yards == 5
    
    def test_negative_yards_with_asterisk(self):
        """Negative yards with asterisk should work."""
        result = parse_result_string("-3*")
        assert result.out_of_bounds is True
        assert result.yards == -3
    
    def test_description_includes_out_of_bounds(self):
        """Description should mention out of bounds."""
        result = parse_result_string("7*")
        assert "out of bounds" in result.description.lower()


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5"},
        kickoff={},
        kickoff_return={},
        punt={},
        punt_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "5*", 11: "3", 12: "F + 2"},  # 10 = out of bounds
    )


@pytest.fixture
def mock_team_chart(mock_special_teams, mock_offense):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
        ),
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestOutOfBoundsTimingFirstHalf:
    """Tests for out-of-bounds timing in first half."""
    
    def test_normal_timing_early_first_half(self, game):
        """Normal timing should apply early in first half."""
        game.state.quarter = 2
        game.state.time_remaining = 10.0  # 10 minutes left
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play with 30 seconds
        game._use_time(30.0, out_of_bounds=True)
        
        # Should use full 30 seconds (0.5 minutes)
        assert game.state.time_remaining == pytest.approx(initial_time - 0.5, abs=0.01)
    
    def test_reduced_timing_last_2_minutes_first_half(self, game):
        """Only 10 seconds should elapse in last 2 minutes of first half."""
        game.state.quarter = 2
        game.state.time_remaining = 1.5  # 1:30 left (within 2 minutes)
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play with 30 seconds
        game._use_time(30.0, out_of_bounds=True)
        
        # Should only use 10 seconds (10/60 = 0.167 minutes)
        expected_time = initial_time - (10.0 / 60.0)
        assert game.state.time_remaining == pytest.approx(expected_time, abs=0.01)
    
    def test_normal_timing_in_bounds_last_2_minutes(self, game):
        """Normal timing should apply for in-bounds plays even in final minutes."""
        game.state.quarter = 2
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate in-bounds play with 30 seconds
        game._use_time(30.0, out_of_bounds=False)
        
        # Should use full 30 seconds
        assert game.state.time_remaining == pytest.approx(initial_time - 0.5, abs=0.01)


class TestOutOfBoundsTimingSecondHalf:
    """Tests for out-of-bounds timing in second half."""
    
    def test_normal_timing_early_fourth_quarter(self, game):
        """Normal timing should apply early in fourth quarter."""
        game.state.quarter = 4
        game.state.time_remaining = 10.0  # 10 minutes left
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play with 30 seconds
        game._use_time(30.0, out_of_bounds=True)
        
        # Should use full 30 seconds
        assert game.state.time_remaining == pytest.approx(initial_time - 0.5, abs=0.01)
    
    def test_reduced_timing_last_5_minutes_fourth_quarter(self, game):
        """Only 10 seconds should elapse in last 5 minutes of fourth quarter."""
        game.state.quarter = 4
        game.state.time_remaining = 4.0  # 4 minutes left (within 5 minutes)
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play with 30 seconds
        game._use_time(30.0, out_of_bounds=True)
        
        # Should only use 10 seconds
        expected_time = initial_time - (10.0 / 60.0)
        assert game.state.time_remaining == pytest.approx(expected_time, abs=0.01)
    
    def test_reduced_timing_at_exactly_5_minutes(self, game):
        """Reduced timing should apply at exactly 5 minutes."""
        game.state.quarter = 4
        game.state.time_remaining = 5.0  # Exactly 5 minutes
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play
        game._use_time(30.0, out_of_bounds=True)
        
        # Should only use 10 seconds
        expected_time = initial_time - (10.0 / 60.0)
        assert game.state.time_remaining == pytest.approx(expected_time, abs=0.01)


class TestOutOfBoundsExceptions:
    """Tests for exceptions to out-of-bounds timing."""
    
    def test_fumble_negates_out_of_bounds(self, game):
        """Fumble should negate out-of-bounds timing."""
        game.state.quarter = 4
        game.state.time_remaining = 2.0  # Final minutes
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        # Create a fumble result with out_of_bounds marker
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=2,
            turnover=True,
            raw_result="F + 2*",
            out_of_bounds=True,  # Has marker but fumble negates it
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")  # Recovered
                
                with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                    initial_time = game.state.time_remaining
                    game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Should use full time, not reduced (fumble negates out of bounds)
        # Time used should be 30 seconds = 0.5 minutes
        assert game.state.time_remaining < initial_time - 0.3  # Used more than 10 seconds
    
    def test_defense_overrule_negates_out_of_bounds(self, game):
        """Defense overrule should negate out-of-bounds timing."""
        game.state.quarter = 4
        game.state.time_remaining = 2.0  # Final minutes
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        # Create a result with out_of_bounds and defense modifier
        mock_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=5,
            raw_result="5*",
            out_of_bounds=True,
            defense_modifier="(3)",  # Defense overruled
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.random.uniform', return_value=30.0):
                initial_time = game.state.time_remaining
                game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Should use full time, not reduced (defense overruled)
        assert game.state.time_remaining < initial_time - 0.3  # Used more than 10 seconds


class TestOutOfBoundsThirdQuarter:
    """Tests to ensure out-of-bounds timing doesn't apply in 3rd quarter."""
    
    def test_normal_timing_third_quarter(self, game):
        """Normal timing should apply in third quarter regardless of time."""
        game.state.quarter = 3
        game.state.time_remaining = 1.0  # Even with 1 minute left
        game.state.ball_position = 50
        
        initial_time = game.state.time_remaining
        
        # Simulate out-of-bounds play
        game._use_time(30.0, out_of_bounds=True)
        
        # Should use full 30 seconds (third quarter doesn't have special timing)
        assert game.state.time_remaining == pytest.approx(initial_time - 0.5, abs=0.01)
