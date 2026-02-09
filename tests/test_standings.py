"""
Tests for season and standings tracking.
"""
import pytest
import tempfile
import shutil

from paydirt.standings import (
    GameResult, TeamRecord, Season, StandingsManager,
    normalize_team_name, add_game_result
)


class TestGameResult:
    """Tests for GameResult dataclass."""
    
    def test_home_win(self):
        """Home team wins when home_score > away_score."""
        game = GameResult(week=1, home_team="Redskins", home_score=21,
                         away_team="Giants", away_score=13)
        assert game.winner == "Redskins"
        assert game.loser == "Giants"
        assert game.is_tie is False
    
    def test_away_win(self):
        """Away team wins when away_score > home_score."""
        game = GameResult(week=1, home_team="Redskins", home_score=13,
                         away_team="Giants", away_score=21)
        assert game.winner == "Giants"
        assert game.loser == "Redskins"
        assert game.is_tie is False
    
    def test_tie(self):
        """Tie when scores are equal."""
        game = GameResult(week=1, home_team="Redskins", home_score=17,
                         away_team="Giants", away_score=17)
        assert game.winner is None
        assert game.loser is None
        assert game.is_tie is True


class TestTeamRecord:
    """Tests for TeamRecord dataclass."""
    
    def test_initial_record(self):
        """New team record should be 0-0."""
        rec = TeamRecord(team="Redskins")
        assert rec.wins == 0
        assert rec.losses == 0
        assert rec.ties == 0
        assert rec.games_played == 0
        assert rec.win_pct == 0.0
    
    def test_win_percentage(self):
        """Win percentage calculation."""
        rec = TeamRecord(team="Redskins", wins=10, losses=6, ties=0)
        assert rec.games_played == 16
        assert rec.win_pct == 10 / 16
    
    def test_win_percentage_with_ties(self):
        """Ties count as half a win in percentage."""
        rec = TeamRecord(team="Redskins", wins=9, losses=5, ties=2)
        assert rec.games_played == 16
        # (9 + 0.5*2) / 16 = 10/16 = 0.625
        assert rec.win_pct == 0.625
    
    def test_point_differential(self):
        """Point differential calculation."""
        rec = TeamRecord(team="Redskins", points_for=350, points_against=280)
        assert rec.point_diff == 70
    
    def test_record_string(self):
        """Record string formatting."""
        rec = TeamRecord(team="Redskins", wins=10, losses=6, ties=0)
        assert rec.record_str == "10-6"
        
        rec_tie = TeamRecord(team="Giants", wins=9, losses=5, ties=2)
        assert rec_tie.record_str == "9-5-2"


class TestSeason:
    """Tests for Season class."""
    
    def test_1983_divisions(self):
        """1983 season should have correct division structure."""
        season = Season(year=1983)
        
        # Check AFC East
        assert "Bills" in season.divisions["AFC"]["East"]
        assert "Dolphins" in season.divisions["AFC"]["East"]
        
        # Check NFC East
        assert "Redskins" in season.divisions["NFC"]["East"]
        assert "Cowboys" in season.divisions["NFC"]["East"]
        assert "Giants" in season.divisions["NFC"]["East"]
    
    def test_get_team_division(self):
        """Should return correct conference and division."""
        season = Season(year=1983)
        
        assert season.get_team_division("Redskins") == ("NFC", "East")
        assert season.get_team_division("Dolphins") == ("AFC", "East")
        assert season.get_team_division("Bears") == ("NFC", "Central")
        assert season.get_team_division("Raiders") == ("AFC", "West")
    
    def test_get_team_conference(self):
        """Should return correct conference."""
        season = Season(year=1983)
        
        assert season.get_team_conference("Redskins") == "NFC"
        assert season.get_team_conference("Dolphins") == "AFC"
    
    def test_add_game(self):
        """Adding a game should update the games list."""
        season = Season(year=1983)
        
        game = season.add_game("Redskins", 21, "Giants", 13)
        
        assert len(season.games) == 1
        assert game.home_team == "Redskins"
        assert game.away_team == "Giants"
        assert game.week == 1
    
    def test_add_multiple_games_auto_week(self):
        """Week numbers should auto-increment when not specified."""
        season = Season(year=1983)
        
        game1 = season.add_game("Redskins", 21, "Giants", 13)
        game2 = season.add_game("Cowboys", 28, "Eagles", 14)
        
        assert game1.week == 1
        assert game2.week == 2
    
    def test_add_game_with_explicit_week(self):
        """Week number should be used when explicitly specified."""
        season = Season(year=1983)
        
        # Add games with explicit week numbers
        game1 = season.add_game("Redskins", 21, "Giants", 13, week=5)
        game2 = season.add_game("Cowboys", 28, "Eagles", 14, week=5)
        game3 = season.add_game("Bears", 17, "Packers", 10, week=5)
        
        assert game1.week == 5
        assert game2.week == 5
        assert game3.week == 5
    
    def test_add_game_week_zero_auto_assigns(self):
        """Week=0 should auto-assign based on game count."""
        season = Season(year=1983)
        
        # Add some games first
        season.add_game("Redskins", 21, "Giants", 13, week=1)
        season.add_game("Cowboys", 28, "Eagles", 14, week=1)
        
        # Add with week=0 (should auto-assign to 3)
        game3 = season.add_game("Bears", 17, "Packers", 10, week=0)
        
        assert game3.week == 3
    
    def test_standings_single_game(self):
        """Standings after one game."""
        season = Season(year=1983)
        season.add_game("Redskins", 21, "Giants", 13)
        
        standings = season.get_standings()
        
        # Redskins won
        assert standings["Redskins"].wins == 1
        assert standings["Redskins"].losses == 0
        assert standings["Redskins"].points_for == 21
        assert standings["Redskins"].points_against == 13
        
        # Giants lost
        assert standings["Giants"].wins == 0
        assert standings["Giants"].losses == 1
        assert standings["Giants"].points_for == 13
        assert standings["Giants"].points_against == 21
    
    def test_division_record(self):
        """Division games should update division record."""
        season = Season(year=1983)
        # Redskins vs Giants is a division game (both NFC East)
        season.add_game("Redskins", 21, "Giants", 13)
        
        standings = season.get_standings()
        
        assert standings["Redskins"].division_wins == 1
        assert standings["Redskins"].division_losses == 0
        assert standings["Giants"].division_wins == 0
        assert standings["Giants"].division_losses == 1
    
    def test_non_division_game(self):
        """Non-division games should not update division record."""
        season = Season(year=1983)
        # Redskins vs Dolphins is not a division game
        season.add_game("Redskins", 21, "Dolphins", 13)
        
        standings = season.get_standings()
        
        assert standings["Redskins"].division_wins == 0
        assert standings["Redskins"].wins == 1
    
    def test_conference_record(self):
        """Conference games should update conference record."""
        season = Season(year=1983)
        # Redskins vs Bears is a conference game (both NFC)
        season.add_game("Redskins", 21, "Bears", 13)
        
        standings = season.get_standings()
        
        assert standings["Redskins"].conference_wins == 1
        assert standings["Bears"].conference_losses == 1


class TestStandingsManager:
    """Tests for StandingsManager persistence."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)
    
    def test_save_and_load_season(self, temp_dir):
        """Season should persist correctly."""
        manager = StandingsManager(data_dir=temp_dir)
        
        # Create and save a season
        season = Season(year=1983)
        season.add_game("Redskins", 21, "Giants", 13)
        season.add_game("Cowboys", 28, "Eagles", 14)
        manager.save_season(season)
        
        # Load it back
        loaded = manager.load_season(1983)
        
        assert loaded.year == 1983
        assert len(loaded.games) == 2
        assert loaded.games[0].home_team == "Redskins"
        assert loaded.games[1].home_team == "Cowboys"
    
    def test_load_nonexistent_season(self, temp_dir):
        """Loading a nonexistent season should return empty season."""
        manager = StandingsManager(data_dir=temp_dir)
        
        season = manager.load_season(1999)
        
        assert season.year == 1999
        assert len(season.games) == 0
    
    def test_list_seasons(self, temp_dir):
        """Should list all seasons with data."""
        manager = StandingsManager(data_dir=temp_dir)
        
        # Create some seasons
        s1 = Season(year=1983)
        s1.add_game("Redskins", 21, "Giants", 13)
        manager.save_season(s1)
        
        s2 = Season(year=1984)
        s2.add_game("Bears", 24, "Packers", 10)
        manager.save_season(s2)
        
        seasons = manager.list_seasons()
        
        assert 1983 in seasons
        assert 1984 in seasons


class TestAddGameResult:
    """Tests for add_game_result helper function and week parameter."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)
    
    def test_add_game_result_with_explicit_week(self, temp_dir):
        """add_game_result should use explicit week when provided."""
        from pathlib import Path
        manager = StandingsManager(data_dir=Path(temp_dir))
        
        # Add games with explicit week
        season = manager.load_season(1983)
        game1 = season.add_game("Redskins", 21, "Giants", 13, week=1)
        game2 = season.add_game("Cowboys", 28, "Eagles", 14, week=1)
        manager.save_season(season)
        
        # Verify weeks are correct
        loaded = manager.load_season(1983)
        assert loaded.games[0].week == 1
        assert loaded.games[1].week == 1
    
    def test_add_game_result_week_persists_after_reload(self, temp_dir):
        """Week number should persist correctly after save/load."""
        from pathlib import Path
        manager = StandingsManager(data_dir=Path(temp_dir))
        
        # Add games with explicit week numbers
        season = manager.load_season(1983)
        season.add_game("Redskins", 21, "Giants", 13, week=5)
        season.add_game("Cowboys", 28, "Eagles", 14, week=5)
        season.add_game("Bears", 17, "Packers", 10, week=6)
        manager.save_season(season)
        
        # Reload and verify
        loaded = manager.load_season(1983)
        assert len(loaded.games) == 3
        assert loaded.games[0].week == 5
        assert loaded.games[1].week == 5
        assert loaded.games[2].week == 6
    
    def test_multiple_games_same_week(self, temp_dir):
        """Multiple games can be recorded for the same week."""
        from pathlib import Path
        manager = StandingsManager(data_dir=Path(temp_dir))
        
        # Add 5 games all in week 1
        season = manager.load_season(1983)
        season.add_game("Redskins", 21, "Giants", 13, week=1)
        season.add_game("Cowboys", 28, "Eagles", 14, week=1)
        season.add_game("Bears", 17, "Packers", 10, week=1)
        season.add_game("49ers", 24, "Rams", 17, week=1)
        season.add_game("Dolphins", 31, "Bills", 14, week=1)
        manager.save_season(season)
        
        # Reload and verify all are week 1
        loaded = manager.load_season(1983)
        assert len(loaded.games) == 5
        for game in loaded.games:
            assert game.week == 1


class TestNormalizeTeamName:
    """Tests for team name normalization."""
    
    def test_exact_match(self):
        """Exact team name should match."""
        season = Season(year=1983)
        assert normalize_team_name("Redskins", season) == "Redskins"
        assert normalize_team_name("Giants", season) == "Giants"
    
    def test_case_insensitive(self):
        """Team names should match case-insensitively."""
        season = Season(year=1983)
        assert normalize_team_name("redskins", season) == "Redskins"
        assert normalize_team_name("GIANTS", season) == "Giants"
    
    def test_partial_match(self):
        """Partial team names should match."""
        season = Season(year=1983)
        assert normalize_team_name("49", season) == "49ers"
    
    def test_unknown_team(self):
        """Unknown team should return None."""
        season = Season(year=1983)
        assert normalize_team_name("Unknown", season) is None
