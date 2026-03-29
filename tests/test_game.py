"""
Tests for the main game engine.
"""
import pytest
from unittest.mock import patch

from paydirt.models import Team, PlayType, DefenseType, PlayResult
from paydirt.game import PaydirtGame, simulate_drive


class TestPaydirtGame:
    """Tests for the PaydirtGame class."""
    
    @pytest.fixture
    def home_team(self):
        """Create a home team for testing."""
        return Team(
            name="Home Team",
            abbreviation="HOM",
            rushing_offense=6,
            passing_offense=7,
            rushing_defense=5,
            passing_defense=6,
            special_teams=6,
        )
    
    @pytest.fixture
    def away_team(self):
        """Create an away team for testing."""
        return Team(
            name="Away Team",
            abbreviation="AWY",
            rushing_offense=5,
            passing_offense=6,
            rushing_defense=6,
            passing_defense=5,
            special_teams=5,
        )
    
    @pytest.fixture
    def game(self, home_team, away_team):
        """Create a game instance for testing."""
        return PaydirtGame(home_team, away_team)
    
    def test_game_initialization(self, game, home_team, away_team):
        """Game should initialize with correct state."""
        assert game.home_team == home_team
        assert game.away_team == away_team
        assert game.state.home_score == 0
        assert game.state.away_score == 0
        assert game.state.quarter == 1
        assert len(game.play_history) == 0
    
    def test_kickoff(self, game):
        """Kickoff should set up possession and field position."""
        result = game.kickoff(receiving_team_is_home=False)
        
        assert result["type"] == "kickoff"
        assert "return_yards" in result
        assert result["receiving_team"] == game.away_team.name
        assert game.state.possession == game.away_team
        assert game.state.down == 1
        assert game.state.yards_to_go == 10
        assert len(game.play_history) == 1
    
    def test_kickoff_return_touchdown(self, game):
        """Kickoff return for touchdown should score when return >= 100 yards."""
        # The max return in the chart is 75 yards, so we need to test the logic
        # by checking that a 75-yard return does NOT score (ball at opponent's 25)
        with patch('paydirt.game.roll_dice', return_value=12):
            result = game.kickoff(receiving_team_is_home=False)
        
        # 75 yard return should put ball at own 75 (opponent's 25), not a TD
        assert result["return_yards"] == 75
        assert result.get("touchdown") is False
        assert game.state.ball_position == 75
    
    def test_run_play_basic(self, game):
        """Running a play should update game state."""
        game.kickoff(receiving_team_is_home=False)
        
        result = game.run_play(PlayType.RUN_MIDDLE, DefenseType.NORMAL)
        
        assert result["type"] == "play"
        assert result["play_type"] == "run_middle"
        assert "dice_roll" in result
        assert "yards" in result
        assert len(game.play_history) == 2
    
    def test_run_play_touchdown(self, game):
        """Play resulting in touchdown should score."""
        game.kickoff(receiving_team_is_home=False)
        game.state.ball_position = 95  # Close to end zone
        
        # Mock a big gain
        with patch('paydirt.game.resolve_play') as mock_resolve:
            from paydirt.models import PlayOutcome
            mock_resolve.return_value = (10, PlayOutcome(PlayResult.GAIN, 10, "Touchdown run"))
            
            result = game.run_play(PlayType.RUN_MIDDLE, DefenseType.NORMAL)
        
        assert result.get("touchdown") is True
        assert game.state.away_score == 6
    
    def test_run_play_turnover(self, game):
        """Turnover should switch possession."""
        game.kickoff(receiving_team_is_home=False)
        
        with patch('paydirt.game.resolve_play') as mock_resolve:
            from paydirt.models import PlayOutcome
            mock_resolve.return_value = (2, PlayOutcome(
                PlayResult.FUMBLE, -2, "Fumble!", turnover=True
            ))
            
            result = game.run_play(PlayType.RUN_MIDDLE, DefenseType.NORMAL)
        
        assert result.get("turnover") is True
        assert game.state.possession == game.home_team
    
    def test_punt(self, game):
        """Punt should switch possession and move ball."""
        game.kickoff(receiving_team_is_home=False)
        game.state.ball_position = 30
        
        result = game.run_play(PlayType.PUNT, DefenseType.NORMAL)
        
        assert result["type"] == "punt"
        assert "punt_distance" in result
        assert game.state.possession == game.home_team
    
    def test_field_goal_success(self, game):
        """Successful field goal should score 3 points."""
        game.kickoff(receiving_team_is_home=False)
        game.state.ball_position = 75  # Opponent's 25
        
        with patch('paydirt.game.resolve_field_goal', return_value=(10, True)):
            result = game.run_play(PlayType.FIELD_GOAL, DefenseType.NORMAL)
        
        assert result["type"] == "field_goal"
        assert result["success"] is True
        assert game.state.away_score == 3
    
    def test_field_goal_miss(self, game):
        """Missed field goal should give ball to other team."""
        game.kickoff(receiving_team_is_home=False)
        game.state.ball_position = 65
        
        with patch('paydirt.game.resolve_field_goal', return_value=(3, False)):
            result = game.run_play(PlayType.FIELD_GOAL, DefenseType.NORMAL)
        
        assert result["success"] is False
        assert game.state.possession == game.home_team
    
    def test_extra_point(self, game):
        """Extra point should add 1 point."""
        game.kickoff(receiving_team_is_home=False)
        game.state.away_score = 6  # After touchdown
        
        with patch('paydirt.game.resolve_extra_point', return_value=(8, True)):
            result = game.attempt_extra_point()
        
        assert result["success"] is True
        assert game.state.away_score == 7
    
    def test_two_point_conversion_success(self, game):
        """Successful two-point conversion should add 2 points."""
        game.kickoff(receiving_team_is_home=False)
        game.state.away_score = 6
        
        with patch('paydirt.game.resolve_two_point_conversion', return_value=(10, True)):
            result = game.attempt_two_point_conversion(PlayType.RUN_MIDDLE)
        
        assert result["success"] is True
        assert game.state.away_score == 8
    
    def test_get_game_status(self, game):
        """get_game_status should return current game state."""
        game.kickoff(receiving_team_is_home=False)
        
        status = game.get_game_status()
        
        assert "quarter" in status
        assert "time_remaining" in status
        assert "score" in status
        assert "possession" in status
        assert "ball_position" in status
        assert "down" in status
        assert "yards_to_go" in status
    
    def test_get_stats(self, game):
        """get_stats should return team statistics."""
        game.kickoff(receiving_team_is_home=False)
        
        stats = game.get_stats()
        
        assert "away" in stats
        assert "home" in stats
        assert stats["away"]["team"] == game.away_team.name
        assert "total_yards" in stats["away"]
        assert "turnovers" in stats["away"]
    
    def test_game_over_check(self, game):
        """Game should end after 4th quarter with different scores."""
        game.state.quarter = 4
        game.state.time_remaining = 0.0
        game.state.home_score = 21
        game.state.away_score = 14
        
        game.kickoff(receiving_team_is_home=False)
        
        # Time should run out - game over when Q4 time hits 0
        assert game.state.game_over is True
    
    def test_stats_tracking(self, game):
        """Stats should be tracked during plays."""
        game.kickoff(receiving_team_is_home=False)
        
        with patch('paydirt.game.resolve_play') as mock_resolve:
            from paydirt.models import PlayOutcome
            mock_resolve.return_value = (8, PlayOutcome(PlayResult.GAIN, 15, "Big run"))
            
            game.run_play(PlayType.RUN_MIDDLE, DefenseType.NORMAL)
        
        assert game.away_team.stats.total_yards == 15
        assert game.away_team.stats.rushing_yards == 15


class TestSimulateDrive:
    """Tests for the simulate_drive function."""
    
    @pytest.fixture
    def game(self):
        """Create a game for testing."""
        home = Team(name="Home", abbreviation="HOM")
        away = Team(name="Away", abbreviation="AWY")
        game = PaydirtGame(home, away)
        game.kickoff(receiving_team_is_home=False)
        return game
    
    def test_simulate_drive_returns_results(self, game):
        """simulate_drive should return list of play results."""
        results = simulate_drive(game, max_plays=5)
        
        assert isinstance(results, list)
        assert len(results) > 0
    
    def test_simulate_drive_stops_on_score(self, game):
        """simulate_drive should stop after a touchdown."""
        game.state.ball_position = 99  # Almost at goal line
        
        results = simulate_drive(game, max_plays=20)
        
        # Should have stopped relatively quickly
        assert len(results) <= 5
    
    def test_simulate_drive_respects_max_plays(self, game):
        """simulate_drive should not exceed max_plays."""
        results = simulate_drive(game, max_plays=3)
        
        assert len(results) <= 3
