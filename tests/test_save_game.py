"""
Tests for game save/load functionality.
"""
import os
import json
import tempfile
import pytest

from paydirt.save_game import save_game, load_game, get_save_info
from paydirt.game_engine import PaydirtGameEngine, ScoringPlay
from paydirt.chart_loader import (
    load_team_chart
)


@pytest.fixture
def game():
    """Create a game engine with real 2026 team charts (save/load needs valid paths)."""
    home_chart = load_team_chart("seasons/2026/Ironclads")
    away_chart = load_team_chart("seasons/2026/Thunderhawks")
    return PaydirtGameEngine(home_chart, away_chart)


@pytest.fixture
def temp_save_file():
    """Create a temporary save file path."""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


class TestSaveGame:
    """Tests for save_game function."""

    def test_save_creates_file(self, game, temp_save_file):
        """save_game should create a JSON file."""
        save_game(game, filepath=temp_save_file)
        assert os.path.exists(temp_save_file)

    def test_save_contains_required_fields(self, game, temp_save_file):
        """Saved file should contain all required fields."""
        save_game(game, filepath=temp_save_file)
        
        with open(temp_save_file, 'r') as f:
            data = json.load(f)
        
        required_fields = [
            'version', 'saved_at', 'away_team_path', 'home_team_path',
            'human_is_away', 'human_is_home', 'home_score', 'away_score',
            'quarter', 'time_remaining', 'is_home_possession', 'ball_position',
            'down', 'yards_to_go', 'game_over', 'home_timeouts', 'away_timeouts',
            'home_stats', 'away_stats', 'scoring_plays'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_save_preserves_game_state(self, game, temp_save_file):
        """Saved state should match game state."""
        # Modify game state
        game.state.home_score = 14
        game.state.away_score = 7
        game.state.quarter = 2
        game.state.time_remaining = 5.5
        game.state.ball_position = 65
        game.state.down = 3
        game.state.yards_to_go = 8
        game.state.home_timeouts = 2
        game.state.away_timeouts = 1
        
        save_game(game, filepath=temp_save_file)
        
        with open(temp_save_file, 'r') as f:
            data = json.load(f)
        
        assert data['home_score'] == 14
        assert data['away_score'] == 7
        assert data['quarter'] == 2
        assert data['time_remaining'] == 5.5
        assert data['ball_position'] == 65
        assert data['down'] == 3
        assert data['yards_to_go'] == 8
        assert data['home_timeouts'] == 2
        assert data['away_timeouts'] == 1


class TestLoadGame:
    """Tests for load_game function."""

    def test_load_restores_game_state(self, game, temp_save_file):
        """load_game should restore game state correctly."""
        # Modify and save
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.quarter = 3
        game.state.time_remaining = 8.25
        game.state.ball_position = 45
        game.state.down = 2
        game.state.yards_to_go = 6
        
        save_game(game, filepath=temp_save_file, human_is_home=True, human_is_away=False)
        
        # Load into new engine
        result = load_game(temp_save_file)
        assert result is not None
        
        loaded_game, human_is_away, human_is_home, _ = result
        
        assert loaded_game.state.home_score == 21
        assert loaded_game.state.away_score == 14
        assert loaded_game.state.quarter == 3
        assert loaded_game.state.time_remaining == 8.25
        assert loaded_game.state.ball_position == 45
        assert loaded_game.state.down == 2
        assert loaded_game.state.yards_to_go == 6
        assert human_is_home is True
        assert human_is_away is False

    def test_load_restores_scoring_plays(self, game, temp_save_file):
        """load_game should restore scoring plays with all fields."""
        # Add a scoring play
        game.state.scoring_plays.append(ScoringPlay(
            quarter=1,
            time_remaining=7.5,
            team="Redskins",
            is_home_team=True,
            play_type="TD",
            description="5 yard run",
            points=6
        ))
        game.state.scoring_plays.append(ScoringPlay(
            quarter=2,
            time_remaining=0.5,
            team="49ers",
            is_home_team=False,
            play_type="FG",
            description="42 yard field goal",
            points=3
        ))
        
        save_game(game, filepath=temp_save_file)
        
        result = load_game(temp_save_file)
        loaded_game, _, _, _ = result
        
        assert len(loaded_game.state.scoring_plays) == 2
        
        # Check first scoring play
        sp1 = loaded_game.state.scoring_plays[0]
        assert sp1.quarter == 1
        assert sp1.time_remaining == 7.5
        assert sp1.team == "Redskins"
        assert sp1.is_home_team is True
        assert sp1.play_type == "TD"
        assert sp1.description == "5 yard run"
        assert sp1.points == 6
        
        # Check second scoring play
        sp2 = loaded_game.state.scoring_plays[1]
        assert sp2.quarter == 2
        assert sp2.time_remaining == 0.5
        assert sp2.team == "49ers"
        assert sp2.is_home_team is False
        assert sp2.play_type == "FG"
        assert sp2.points == 3

    def test_load_nonexistent_file_returns_none(self):
        """load_game should return None for nonexistent file."""
        result = load_game("/nonexistent/path/save.json")
        assert result is None

    def test_load_restores_team_stats(self, game, temp_save_file):
        """load_game should restore team statistics."""
        game.state.home_stats.first_downs = 12
        game.state.home_stats.total_yards = 250
        game.state.home_stats.turnovers = 1
        game.state.away_stats.first_downs = 8
        game.state.away_stats.interceptions_thrown = 2
        
        save_game(game, filepath=temp_save_file)
        
        result = load_game(temp_save_file)
        loaded_game, _, _, _ = result
        
        assert loaded_game.state.home_stats.first_downs == 12
        assert loaded_game.state.home_stats.total_yards == 250
        assert loaded_game.state.home_stats.turnovers == 1
        assert loaded_game.state.away_stats.first_downs == 8
        assert loaded_game.state.away_stats.interceptions_thrown == 2


class TestGetSaveInfo:
    """Tests for get_save_info function."""

    def test_get_save_info_returns_summary(self, game, temp_save_file):
        """get_save_info should return summary without full load."""
        game.state.home_score = 17
        game.state.away_score = 10
        game.state.quarter = 4
        game.state.time_remaining = 2.0
        
        save_game(game, filepath=temp_save_file)
        
        info = get_save_info(temp_save_file)
        
        assert info is not None
        assert info['home_score'] == 17
        assert info['away_score'] == 10
        assert info['quarter'] == 4
        assert info['time_remaining'] == 2.0
        assert 'saved_at' in info

    def test_get_save_info_nonexistent_returns_none(self):
        """get_save_info should return None for nonexistent file."""
        info = get_save_info("/nonexistent/path/save.json")
        assert info is None
