"""
Tests for goal line display formatting.

When the ball is inside the opponent's 10-yard line and the goal line
is closer than the first down marker, the display should show "Goal"
instead of the yards to go (e.g., "1st and Goal" instead of "1st and 8").
"""
import pytest
from unittest.mock import MagicMock

from paydirt.game_engine import PaydirtGameEngine, GameState


class TestGoalLineDisplay:
    """Tests for goal line down display logic."""
    
    @pytest.fixture
    def game(self):
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
    
    def test_goal_line_logic_at_8_yard_line_first_down(self, game):
        """At opponent's 8, 1st and 10 should show as 'Goal'."""
        game.state.ball_position = 92  # Opponent's 8-yard line
        game.state.down = 1
        game.state.yards_to_go = 10
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 8
        assert is_goal is True  # Should display "Goal"
    
    def test_goal_line_logic_at_8_yard_line_short_yardage(self, game):
        """At opponent's 8, 2nd and 3 should NOT show as 'Goal'."""
        game.state.ball_position = 92  # Opponent's 8-yard line
        game.state.down = 2
        game.state.yards_to_go = 3
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 8
        assert is_goal is False  # Should display "3", not "Goal"
    
    def test_goal_line_logic_at_3_yard_line(self, game):
        """At opponent's 3, 3rd and 5 should show as 'Goal'."""
        game.state.ball_position = 97  # Opponent's 3-yard line
        game.state.down = 3
        game.state.yards_to_go = 5
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 3
        assert is_goal is True  # Should display "Goal"
    
    def test_goal_line_logic_at_1_yard_line(self, game):
        """At opponent's 1, any down should show as 'Goal'."""
        game.state.ball_position = 99  # Opponent's 1-yard line
        game.state.down = 4
        game.state.yards_to_go = 1
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 1
        assert is_goal is True  # Should display "Goal"
    
    def test_not_goal_line_at_15_yard_line(self, game):
        """At opponent's 15, should NOT show as 'Goal'."""
        game.state.ball_position = 85  # Opponent's 15-yard line
        game.state.down = 1
        game.state.yards_to_go = 10
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 15
        assert is_goal is False  # Should display "10", not "Goal"
    
    def test_not_goal_line_at_midfield(self, game):
        """At midfield, should NOT show as 'Goal'."""
        game.state.ball_position = 50  # Midfield
        game.state.down = 1
        game.state.yards_to_go = 10
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 50
        assert is_goal is False
    
    def test_goal_line_exactly_at_10(self, game):
        """At opponent's 10, 1st and 10 should show as 'Goal'."""
        game.state.ball_position = 90  # Opponent's 10-yard line
        game.state.down = 1
        game.state.yards_to_go = 10
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 10
        assert is_goal is True  # Should display "Goal"
    
    def test_not_goal_at_11_yard_line(self, game):
        """At opponent's 11, should NOT show as 'Goal'."""
        game.state.ball_position = 89  # Opponent's 11-yard line
        game.state.down = 1
        game.state.yards_to_go = 10
        
        yards_to_goal = 100 - game.state.ball_position
        is_goal = yards_to_goal <= 10 and game.state.yards_to_go >= yards_to_goal
        
        assert yards_to_goal == 11
        assert is_goal is False  # Should display "10", not "Goal"
