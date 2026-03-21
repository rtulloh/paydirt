"""
Tests for the ResultFormatter class.
"""
import pytest
from unittest.mock import MagicMock

from paydirt.result_formatter import ResultFormatter
from paydirt.play_resolver import PlayType, ResultType


class TestResultFormatterFumbleCommentary:
    """Tests for ResultFormatter fumble commentary handling."""
    
    @pytest.fixture
    def formatter(self):
        """Create a ResultFormatter for testing."""
        offense_roster = {
            'qb': ['Joe Montana'],
            'rb': ['Roger Craig'],
            'wr': ['Jerry Rice'],
            'te': ['Russ Francis'],
            'ol': [],
            'dl': [],
            'lb': [],
            'db': [],
            'k': [],
            'p': [],
            'kr': []
        }
        defense_roster = {
            'qb': [],
            'rb': [],
            'wr': [],
            'te': [],
            'ol': [],
            'dl': ['Fred Dean'],
            'lb': ['Keena Turner'],
            'db': ['Ronnie Lott'],
            'k': [],
            'p': [],
            'kr': []
        }
        return ResultFormatter("SF '83", "DAL '83", offense_roster, defense_roster)
    
    def _create_mock_outcome(self, result_type, yards, fumble_recovered=None, **kwargs):
        """Create a mock PlayOutcome for testing."""
        outcome = MagicMock()
        outcome.play_type = PlayType.LINE_PLUNGE
        outcome.yards_gained = yards
        outcome.first_down = False
        outcome.touchdown = False
        outcome.turnover = result_type == ResultType.FUMBLE
        outcome.safety = False
        
        # Create mock result
        result = MagicMock()
        result.result_type = result_type
        outcome.result = result
        
        # Set fumble_recovered if provided
        if fumble_recovered is not None:
            result.fumble_recovered = fumble_recovered
        
        for key, value in kwargs.items():
            setattr(outcome, key, value)
        
        return outcome
    
    def test_fumble_uses_empty_commentary(self, formatter):
        """Fumbles should use empty commentary - core engine's description is authoritative."""
        outcome = self._create_mock_outcome(
            ResultType.FUMBLE, 
            yards=2,
            fumble_recovered=True
        )
        
        formatted = formatter.format(outcome)
        
        # Fumble commentary should be empty - let the description speak for itself
        assert formatted.commentary == "", \
            f"Fumble commentary should be empty, got: {formatted.commentary}"
        # is_fumble flag should still be set for UI purposes
        assert formatted.is_fumble is True
    
    def test_fumble_defense_recovery(self, formatter):
        """Fumbles with defense recovery should still have empty commentary."""
        outcome = self._create_mock_outcome(
            ResultType.FUMBLE, 
            yards=-2,
            fumble_recovered=False
        )
        
        formatted = formatter.format(outcome)
        
        # Commentary should be empty
        assert formatted.commentary == "", \
            f"Fumble commentary should be empty, got: {formatted.commentary}"
        # is_fumble flag should be set
        assert formatted.is_fumble is True
    
    def test_non_fumble_plays_not_affected(self, formatter):
        """Non-fumble plays should not be affected by the empty commentary rule."""
        outcome = self._create_mock_outcome(
            ResultType.YARDS, 
            yards=5
        )
        
        formatted = formatter.format(outcome)
        
        # Should not mention fumble
        assert "fumble" not in formatted.commentary.lower()
        # Should have normal gain commentary
        assert "5" in formatted.commentary or "gain" in formatted.commentary.lower()
    
    def test_interception_uses_empty_commentary(self, formatter):
        """Interceptions should use empty commentary - core engine's description is authoritative."""
        outcome = self._create_mock_outcome(
            ResultType.INTERCEPTION, 
            yards=0
        )
        
        formatted = formatter.format(outcome)
        
        # Interception commentary should be empty
        assert formatted.commentary == "", \
            f"Interception commentary should be empty, got: {formatted.commentary}"
        # is_interception flag should still be set
        assert formatted.is_interception is True


class TestResultFormatterSpecialTeams:
    """Tests for ResultFormatter special teams play handling."""
    
    @pytest.fixture
    def formatter(self):
        """Create a ResultFormatter for testing."""
        offense_roster = {
            'qb': ['Joe Montana'],
            'rb': ['Roger Craig'],
            'wr': ['Jerry Rice'],
            'te': ['Russ Francis'],
            'ol': [],
            'dl': [],
            'lb': [],
            'db': [],
            'k': [],
            'p': ['Mike Horan'],
            'kr': []
        }
        defense_roster = {
            'qb': [],
            'rb': [],
            'wr': [],
            'te': [],
            'ol': [],
            'dl': ['Fred Dean'],
            'lb': ['Keena Turner'],
            'db': ['Ronnie Lott'],
            'k': [],
            'p': [],
            'kr': ['Mike Wilson']
        }
        return ResultFormatter("SF '83", "DAL '83", offense_roster, defense_roster)
    
    def _create_mock_outcome(self, play_type, result_type, yards, **kwargs):
        """Create a mock PlayOutcome for testing."""
        outcome = MagicMock()
        outcome.play_type = play_type
        outcome.yards_gained = yards
        outcome.first_down = False
        outcome.touchdown = False
        outcome.turnover = False
        outcome.safety = False
        outcome.pending_penalty_decision = False
        
        result = MagicMock()
        result.result_type = result_type
        outcome.result = result
        
        for key, value in kwargs.items():
            setattr(outcome, key, value)
        
        return outcome
    
    def test_punt_headline_shows_punt_distance(self, formatter):
        """Punt should show 'Punt X yards' not 'Gain of X'."""
        outcome = self._create_mock_outcome(
            PlayType.PUNT,
            ResultType.YARDS,
            yards=40
        )
        
        formatted = formatter.format(outcome)
        
        assert formatted.headline == "Punt 40 yards", \
            f"Punt headline should be 'Punt 40 yards', got: {formatted.headline}"
    
    def test_punt_commentary_is_empty(self, formatter):
        """Punt should not have run/pass commentary with player names."""
        outcome = self._create_mock_outcome(
            PlayType.PUNT,
            ResultType.YARDS,
            yards=40
        )
        
        formatted = formatter.format(outcome)
        
        # Should not contain RB player name from roster
        assert "Roger Craig" not in formatted.commentary, \
            f"Punt commentary should not mention RB, got: {formatted.commentary}"
        # Should be empty - let description speak for itself
        assert formatted.commentary == "", \
            f"Punt commentary should be empty, got: {formatted.commentary}"
    
    def test_punt_short_headline(self, formatter):
        """Short punt should still show 'Punt X yards'."""
        outcome = self._create_mock_outcome(
            PlayType.PUNT,
            ResultType.YARDS,
            yards=35
        )
        
        formatted = formatter.format(outcome)
        
        assert formatted.headline == "Punt 35 yards"
    
    def test_field_goal_headline(self, formatter):
        """Field goal should show appropriate headline."""
        outcome = self._create_mock_outcome(
            PlayType.FIELD_GOAL,
            ResultType.YARDS,
            yards=42
        )
        
        formatted = formatter.format(outcome)
        
        assert "Field goal" in formatted.headline, \
            f"FG headline should mention field goal, got: {formatted.headline}"
        assert "42" in formatted.headline, \
            f"FG headline should include distance, got: {formatted.headline}"
    
    def test_field_goal_commentary_is_empty(self, formatter):
        """Field goal should not have misleading commentary."""
        outcome = self._create_mock_outcome(
            PlayType.FIELD_GOAL,
            ResultType.YARDS,
            yards=42
        )
        
        formatted = formatter.format(outcome)
        
        assert formatted.commentary == "", \
            f"FG commentary should be empty, got: {formatted.commentary}"
    
    def test_kickoff_headline(self, formatter):
        """Kickoff should show appropriate headline."""
        outcome = self._create_mock_outcome(
            PlayType.KICKOFF,
            ResultType.YARDS,
            yards=65
        )
        
        formatted = formatter.format(outcome)
        
        assert "Kickoff" in formatted.headline, \
            f"Kickoff headline should mention kickoff, got: {formatted.headline}"
        assert "65" in formatted.headline, \
            f"Kickoff headline should include distance, got: {formatted.headline}"
    
    def test_kickoff_commentary_is_empty(self, formatter):
        """Kickoff should not have misleading commentary."""
        outcome = self._create_mock_outcome(
            PlayType.KICKOFF,
            ResultType.YARDS,
            yards=65
        )
        
        formatted = formatter.format(outcome)
        
        assert formatted.commentary == "", \
            f"Kickoff commentary should be empty, got: {formatted.commentary}"
    
    def test_regular_play_still_says_gain(self, formatter):
        """Regular plays should still say 'Gain of X'."""
        outcome = self._create_mock_outcome(
            PlayType.LINE_PLUNGE,
            ResultType.YARDS,
            yards=5
        )
        
        formatted = formatter.format(outcome)
        
        assert formatted.headline == "Gain of 5", \
            f"Regular play should say 'Gain of 5', got: {formatted.headline}"
