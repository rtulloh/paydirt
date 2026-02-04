"""
Tests for the teams module.
"""
import pytest
from paydirt.teams import get_team, list_teams, get_sample_teams
from paydirt.models import Team


class TestGetSampleTeams:
    """Tests for get_sample_teams function."""
    
    def test_returns_dict_of_teams(self):
        """get_sample_teams should return a dictionary of Team objects."""
        teams = get_sample_teams()
        
        assert isinstance(teams, dict)
        assert len(teams) > 0
        
        for abbr, team in teams.items():
            assert isinstance(abbr, str)
            assert isinstance(team, Team)
    
    def test_teams_have_valid_ratings(self):
        """All teams should have ratings between 1 and 10."""
        teams = get_sample_teams()
        
        for abbr, team in teams.items():
            assert 1 <= team.rushing_offense <= 10, f"{abbr} rushing_offense out of range"
            assert 1 <= team.passing_offense <= 10, f"{abbr} passing_offense out of range"
            assert 1 <= team.rushing_defense <= 10, f"{abbr} rushing_defense out of range"
            assert 1 <= team.passing_defense <= 10, f"{abbr} passing_defense out of range"
            assert 1 <= team.special_teams <= 10, f"{abbr} special_teams out of range"
    
    def test_teams_have_abbreviations(self):
        """All teams should have matching abbreviations."""
        teams = get_sample_teams()
        
        for abbr, team in teams.items():
            assert team.abbreviation == abbr


class TestGetTeam:
    """Tests for get_team function."""
    
    def test_get_existing_team(self):
        """get_team should return the correct team."""
        team = get_team("KC")
        
        assert team.name == "Kansas City Chiefs"
        assert team.abbreviation == "KC"
    
    def test_get_team_case_insensitive(self):
        """get_team should be case insensitive."""
        team_upper = get_team("KC")
        team_lower = get_team("kc")
        
        assert team_upper.name == team_lower.name
    
    def test_get_nonexistent_team_raises(self):
        """get_team should raise ValueError for unknown teams."""
        with pytest.raises(ValueError) as exc_info:
            get_team("XXX")
        
        assert "Unknown team" in str(exc_info.value)
        assert "XXX" in str(exc_info.value)


class TestListTeams:
    """Tests for list_teams function."""
    
    def test_returns_list_of_tuples(self):
        """list_teams should return list of (abbr, name, rating) tuples."""
        teams = list_teams()
        
        assert isinstance(teams, list)
        assert len(teams) > 0
        
        for item in teams:
            assert isinstance(item, tuple)
            assert len(item) == 3
            abbr, name, rating = item
            assert isinstance(abbr, str)
            assert isinstance(name, str)
            assert isinstance(rating, int)
    
    def test_sorted_by_power_rating(self):
        """list_teams should be sorted by power rating descending."""
        teams = list_teams()
        
        ratings = [rating for _, _, rating in teams]
        assert ratings == sorted(ratings, reverse=True)
    
    def test_contains_expected_teams(self):
        """list_teams should contain well-known teams."""
        teams = list_teams()
        abbrs = [abbr for abbr, _, _ in teams]
        
        assert "KC" in abbrs
        assert "SF" in abbrs
        assert "DAL" in abbrs
