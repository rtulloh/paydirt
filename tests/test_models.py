"""
Tests for the core game models.
"""
import pytest
from paydirt.models import (
    Team, GameState, PlayResult, PlayOutcome
)


class TestTeam:
    """Tests for the Team model."""
    
    def test_team_creation_with_defaults(self):
        """Team should be created with default ratings of 5."""
        team = Team(name="Test Team", abbreviation="TST")
        
        assert team.name == "Test Team"
        assert team.abbreviation == "TST"
        assert team.rushing_offense == 5
        assert team.passing_offense == 5
        assert team.rushing_defense == 5
        assert team.passing_defense == 5
        assert team.special_teams == 5
        assert team.power_rating == 50
    
    def test_team_creation_with_custom_ratings(self):
        """Team should accept custom ratings."""
        team = Team(
            name="Good Team",
            abbreviation="GTM",
            rushing_offense=8,
            passing_offense=9,
            rushing_defense=7,
            passing_defense=6,
            special_teams=7,
            power_rating=85,
        )
        
        assert team.rushing_offense == 8
        assert team.passing_offense == 9
        assert team.power_rating == 85
    
    def test_team_stats_initialization(self):
        """Team should have zeroed stats on creation."""
        team = Team(name="Test", abbreviation="TST")
        
        assert team.stats.first_downs == 0
        assert team.stats.total_yards == 0
        assert team.stats.turnovers == 0
    
    def test_reset_stats(self):
        """reset_stats should zero out all statistics."""
        team = Team(name="Test", abbreviation="TST")
        team.stats.total_yards = 100
        team.stats.turnovers = 2
        
        team.reset_stats()
        
        assert team.stats.total_yards == 0
        assert team.stats.turnovers == 0


class TestGameState:
    """Tests for the GameState model."""
    
    @pytest.fixture
    def home_team(self):
        """Create a home team for testing."""
        return Team(name="Home Team", abbreviation="HOM")
    
    @pytest.fixture
    def away_team(self):
        """Create an away team for testing."""
        return Team(name="Away Team", abbreviation="AWY")
    
    @pytest.fixture
    def game_state(self, home_team, away_team):
        """Create a game state for testing."""
        return GameState(home_team=home_team, away_team=away_team)
    
    def test_initial_state(self, game_state, away_team):
        """Game should start with correct initial state."""
        assert game_state.home_score == 0
        assert game_state.away_score == 0
        assert game_state.quarter == 1
        assert game_state.time_remaining == 15.0
        assert game_state.down == 1
        assert game_state.yards_to_go == 10
        assert game_state.game_over is False
        # Away team receives opening kickoff
        assert game_state.possession == away_team
        assert game_state.is_home_possession is False
    
    def test_switch_possession(self, game_state, home_team, away_team):
        """switch_possession should change possession and flip field."""
        game_state.ball_position = 30  # Own 30
        
        game_state.switch_possession()
        
        assert game_state.possession == home_team
        assert game_state.is_home_possession is True
        assert game_state.ball_position == 70  # Opponent's 30 becomes own 70
        assert game_state.down == 1
        assert game_state.yards_to_go == 10
    
    def test_advance_ball_normal_gain(self, game_state):
        """advance_ball should update position and yards to go."""
        game_state.ball_position = 25
        game_state.yards_to_go = 10
        
        result = game_state.advance_ball(5)
        
        assert game_state.ball_position == 30
        assert game_state.yards_to_go == 5
        assert result is False  # No first down
    
    def test_advance_ball_first_down(self, game_state):
        """advance_ball should grant first down when yards_to_go reached."""
        game_state.ball_position = 25
        game_state.yards_to_go = 10
        
        result = game_state.advance_ball(12)
        
        assert game_state.ball_position == 37
        assert game_state.down == 1
        assert game_state.yards_to_go == 10
        assert result is True
    
    def test_advance_ball_touchdown(self, game_state):
        """advance_ball should detect touchdown when reaching end zone."""
        game_state.ball_position = 95
        
        result = game_state.advance_ball(10)
        
        assert game_state.ball_position == 100
        assert result is True
    
    def test_advance_ball_touchdown_from_99_does_not_set_zero_yards_to_go(self, game_state):
        """advance_ball should not set yards_to_go to 0 when scoring from opponent's 1."""
        game_state.ball_position = 99  # Opponent's 1-yard line
        game_state.yards_to_go = 1
        game_state.down = 1
        
        result = game_state.advance_ball(2)  # Gain 2 yards for touchdown
        
        assert game_state.ball_position == 100
        assert result is True
        # yards_to_go should remain at original value (1), not be set to 0
        assert game_state.yards_to_go == 1
    
    def test_qb_scramble_from_1_yard_line_displays_correctly(self, game_state):
        """QB scramble from opponent's 1-yard line should not show 'Goal @ 0' in display."""
        game_state.ball_position = 99  # Opponent's 1-yard line
        game_state.yards_to_go = 1
        game_state.down = 1
        
        # Simulate QB scramble gaining 2 yards (like the QT result)
        result = game_state.advance_ball(2)
        
        assert result is True
        assert game_state.ball_position == 100
        
        # yards_to_go should not be 0 after touchdown
        assert game_state.yards_to_go == 1
        
        # Verify display logic would not show "Goal @ 0"
        from paydirt.utils import yards_to_goal
        ytg = yards_to_goal(game_state.ball_position)
        # Display should not show "Goal @ 0" - it should check ytg > 0
        assert not (game_state.yards_to_go >= ytg and ytg > 0), \
            "Display should not show 'Goal @ 0'"
    
    def test_field_position_str_uses_team_context(self):
        """field_position_str should show position from possessing team's perspective."""
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.chart_loader import TeamChart, PeripheralData
        from unittest.mock import MagicMock
        
        # Create mock charts
        home_chart = TeamChart(
            peripheral=PeripheralData(
                year=1983, team_name="Home", team_nickname="Team",
                power_rating=50, short_name="HOM"
            ),
            offense=MagicMock(), defense=MagicMock(), special_teams=MagicMock()
        )
        away_chart = TeamChart(
            peripheral=PeripheralData(
                year=1983, team_name="Away", team_nickname="Team",
                power_rating=50, short_name="AWY"
            ),
            offense=MagicMock(), defense=MagicMock(), special_teams=MagicMock()
        )
        
        game = PaydirtGameEngine(home_chart, away_chart)
        
        # Home team punts from opponent's 44 -> ball at 92 (their own 8)
        game.state.ball_position = 92
        game.state.is_home_possession = True
        
        # Should show "own 8" because home team has possession at their own 8-yard line
        result = game.state.field_position_str()
        assert "8" in result, f"Expected 'own 8' or 'HOM 8', got '{result}'"
        
        # After switching possession (punt received), should show opponent's perspective
        game.state.switch_possession()
        
        # Now away team has ball at position 8 (their own 8)
        # Should show "own 8" or "AWY 8" because away team is now on offense
        result = game.state.field_position_str()
        assert "8" in result, f"Expected 'own 8' or 'AWY 8', got '{result}'"
    
    def test_next_down(self, game_state):
        """next_down should increment down counter."""
        game_state.down = 1
        
        game_state.next_down()
        assert game_state.down == 2
        
        game_state.next_down()
        assert game_state.down == 3
    
    def test_next_down_turnover_on_downs(self, game_state, home_team):
        """next_down should switch possession after 4th down."""
        game_state.down = 4
        game_state.ball_position = 50
        
        game_state.next_down()
        
        assert game_state.possession == home_team
        assert game_state.down == 1
    
    def test_score_touchdown(self, game_state):
        """score_touchdown should add 6 points to possessing team."""
        game_state.is_home_possession = True
        game_state.score_touchdown()
        assert game_state.home_score == 6
        assert game_state.away_score == 0
        
        game_state.is_home_possession = False
        game_state.score_touchdown()
        assert game_state.away_score == 6
    
    def test_score_field_goal(self, game_state):
        """score_field_goal should add 3 points to possessing team."""
        game_state.is_home_possession = True
        game_state.score_field_goal()
        assert game_state.home_score == 3
    
    def test_score_safety(self, game_state):
        """score_safety should add 2 points to defending team."""
        game_state.is_home_possession = True
        game_state.score_safety()
        assert game_state.away_score == 2  # Defense scores
    
    def test_use_time_within_quarter(self, game_state):
        """use_time should decrement time remaining."""
        game_state.time_remaining = 10.0
        
        game_state.use_time(60)  # 1 minute
        
        assert game_state.time_remaining == 9.0
        assert game_state.quarter == 1
    
    def test_use_time_end_of_quarter(self, game_state):
        """use_time should advance quarter when time expires."""
        game_state.time_remaining = 0.5
        game_state.quarter = 1
        
        game_state.use_time(60)  # 1 minute
        
        assert game_state.quarter == 2
        assert game_state.time_remaining == 15.0
    
    def test_use_time_end_of_game(self, game_state):
        """use_time should end game after 4th quarter with different scores."""
        game_state.quarter = 4
        game_state.time_remaining = 0.5
        game_state.home_score = 21
        game_state.away_score = 14
        
        game_state.use_time(60)
        
        assert game_state.game_over is True
    
    def test_field_position_description_own_territory(self, game_state):
        """get_field_position_description should show 'own' for first half."""
        game_state.ball_position = 25
        assert game_state.get_field_position_description() == "own 25"
    
    def test_field_position_description_opponent_territory(self, game_state):
        """get_field_position_description should show 'opponent's' for second half."""
        game_state.ball_position = 75
        assert game_state.get_field_position_description() == "opponent's 25"


class TestPlayOutcome:
    """Tests for PlayOutcome model."""
    
    def test_play_outcome_creation(self):
        """PlayOutcome should store all fields correctly."""
        outcome = PlayOutcome(
            result=PlayResult.GAIN,
            yards=8,
            description="Nice run",
            turnover=False,
            scoring=False,
        )
        
        assert outcome.result == PlayResult.GAIN
        assert outcome.yards == 8
        assert outcome.description == "Nice run"
        assert outcome.turnover is False
    
    def test_play_outcome_defaults(self):
        """PlayOutcome should have sensible defaults."""
        outcome = PlayOutcome(result=PlayResult.INCOMPLETE)
        
        assert outcome.yards == 0
        assert outcome.description == ""
        assert outcome.turnover is False
        assert outcome.scoring is False
