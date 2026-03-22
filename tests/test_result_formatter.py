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


class TestResultFormatterHeadlines:
    """Tests for _get_headline() branches."""

    @pytest.fixture
    def formatter(self):
        return ResultFormatter("SF '83", "DAL '83")

    def _mock_outcome(self, result_type, yards=0, touchdown=False, turnover=False,
                      safety=False, pending_penalty=False, play_type=PlayType.LINE_PLUNGE,
                      **kwargs):
        outcome = MagicMock()
        outcome.play_type = play_type
        outcome.yards_gained = yards
        outcome.touchdown = touchdown
        outcome.turnover = turnover
        outcome.safety = safety
        outcome.pending_penalty_decision = pending_penalty
        outcome.penalty_choice = None
        result = MagicMock()
        result.result_type = result_type
        outcome.result = result
        for k, v in kwargs.items():
            setattr(outcome, k, v)
        return outcome

    def test_headline_touchdown(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, touchdown=True)
        assert formatter.format(outcome).headline == "TOUCHDOWN!"

    def test_headline_interception(self, formatter):
        outcome = self._mock_outcome(ResultType.INTERCEPTION, turnover=True)
        assert formatter.format(outcome).headline == "INTERCEPTED!"

    def test_headline_fumble(self, formatter):
        outcome = self._mock_outcome(ResultType.FUMBLE, turnover=True)
        assert formatter.format(outcome).headline == "FUMBLE!"

    def test_headline_safety(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, safety=True)
        assert formatter.format(outcome).headline == "SAFETY!"

    def test_headline_sack(self, formatter):
        outcome = self._mock_outcome(ResultType.SACK, yards=-8)
        assert formatter.format(outcome).headline == "SACKED for 8!"

    def test_headline_sack_positive_yards(self, formatter):
        outcome = self._mock_outcome(ResultType.SACK, yards=0)
        assert formatter.format(outcome).headline == "SACKED for 0!"

    def test_headline_breakaway_gain(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=25)
        assert formatter.format(outcome).headline == "BREAKAWAY! +25"

    def test_headline_breakaway_zero_yards(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=0)
        assert formatter.format(outcome).headline == "Stuffed (0)"

    def test_headline_breakaway_negative(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=-3)
        assert formatter.format(outcome).headline == "Stuffed (-3)"

    def test_headline_incomplete(self, formatter):
        outcome = self._mock_outcome(ResultType.INCOMPLETE)
        assert formatter.format(outcome).headline == "Incomplete"

    def test_headline_penalty_offense(self, formatter):
        outcome = self._mock_outcome(ResultType.PENALTY_OFFENSE, yards=-5)
        assert formatter.format(outcome).headline == "OFFENSIVE PENALTY (5 yds)"

    def test_headline_penalty_defense(self, formatter):
        outcome = self._mock_outcome(ResultType.PENALTY_DEFENSE, yards=5)
        assert formatter.format(outcome).headline == "DEFENSIVE PENALTY! +5 yds"

    def test_headline_pass_interference(self, formatter):
        outcome = self._mock_outcome(ResultType.PASS_INTERFERENCE, yards=15)
        assert formatter.format(outcome).headline == "PASS INTERFERENCE! +15 yds"

    def test_headline_special_teams_punt(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=40, play_type=PlayType.PUNT)
        assert formatter.format(outcome).headline == "Punt 40 yards"

    def test_headline_special_teams_field_goal(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=37, play_type=PlayType.FIELD_GOAL)
        assert formatter.format(outcome).headline == "Field goal attempt (37 yards)"

    def test_headline_special_teams_kickoff(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=65, play_type=PlayType.KICKOFF)
        assert formatter.format(outcome).headline == "Kickoff 65 yards"

    def test_headline_gain(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=7)
        assert formatter.format(outcome).headline == "Gain of 7"

    def test_headline_loss(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=-3)
        assert formatter.format(outcome).headline == "Loss of 3"

    def test_headline_no_gain(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=0)
        assert formatter.format(outcome).headline == "No gain"

    def test_headline_pending_penalty(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, pending_penalty=True)
        assert formatter.format(outcome).headline == "PENALTY ON THE PLAY!"

    def test_headline_int_in_result_type(self, formatter):
        result = MagicMock()
        result.result_type = "INTERCEPTION_RETURN"
        outcome = MagicMock()
        outcome.play_type = PlayType.MEDIUM_PASS
        outcome.yards_gained = 0
        outcome.touchdown = False
        outcome.turnover = True
        outcome.safety = False
        outcome.pending_penalty_decision = False
        outcome.penalty_choice = None
        outcome.result = result
        assert formatter.format(outcome).headline == "INTERCEPTED!"


class TestResultFormatterBigPlayInfo:
    """Tests for _get_big_play_info() branches."""

    @pytest.fixture
    def formatter(self):
        return ResultFormatter("SF '83", "DAL '83")

    def _mock_outcome(self, result_type, yards=0, touchdown=False, turnover=False,
                      safety=False, first_down=False, **kwargs):
        outcome = MagicMock()
        outcome.play_type = PlayType.LINE_PLUNGE
        outcome.yards_gained = yards
        outcome.touchdown = touchdown
        outcome.turnover = turnover
        outcome.safety = safety
        outcome.first_down = first_down
        outcome.pending_penalty_decision = False
        outcome.penalty_choice = None
        result = MagicMock()
        result.result_type = result_type
        outcome.result = result
        for k, v in kwargs.items():
            setattr(outcome, k, v)
        return outcome

    def test_big_play_touchdown(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, touchdown=True)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 3 and btype == "touchdown"

    def test_big_play_interception(self, formatter):
        result = MagicMock()
        result.result_type = "INT"
        outcome = MagicMock()
        outcome.touchdown = False
        outcome.turnover = True
        outcome.safety = False
        outcome.yards_gained = 0
        outcome.first_down = False
        outcome.result = result
        factor, btype = formatter._get_big_play_info(outcome, result)
        assert factor == 3 and btype == "interception"

    def test_big_play_fumble(self, formatter):
        outcome = self._mock_outcome(ResultType.FUMBLE, turnover=True)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 3 and btype == "fumble"

    def test_big_play_safety(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, safety=True)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 3 and btype == "safety"

    def test_big_play_sack(self, formatter):
        outcome = self._mock_outcome(ResultType.SACK, yards=-5)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "sack"

    def test_big_play_pass_interference(self, formatter):
        outcome = self._mock_outcome(ResultType.PASS_INTERFERENCE, yards=15)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "pass_interference"

    def test_big_play_breakaway_explosive(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=25)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "explosive"

    def test_big_play_breakaway_normal(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=15)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "breakaway"

    def test_big_play_breakaway_stuff(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY, yards=-2)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "stuff"

    def test_big_play_explosive_20_plus(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=22)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "explosive"

    def test_big_play_big_10_plus(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=12)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 2 and btype == "big_play"

    def test_big_play_first_down(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=5, first_down=True)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 1 and btype == "first_down"

    def test_big_play_positive_5_plus(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=7, first_down=False)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 1 and btype == "positive"

    def test_big_play_tackle_for_loss(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=-3)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 1 and btype == "tackle_for_loss"

    def test_big_play_normal(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=3, first_down=False)
        factor, btype = formatter._get_big_play_info(outcome, outcome.result)
        assert factor == 0 and btype == "normal"


class TestResultFormatterFlags:
    """Tests for _get_flags() branches."""

    @pytest.fixture
    def formatter(self):
        return ResultFormatter("SF '83", "DAL '83")

    def _mock_outcome(self, result_type, yards=0, first_down=False, touchdown=False,
                      turnover=False, safety=False):
        outcome = MagicMock()
        outcome.play_type = PlayType.LINE_PLUNGE
        outcome.yards_gained = yards
        outcome.first_down = first_down
        outcome.touchdown = touchdown
        outcome.turnover = turnover
        outcome.safety = safety
        outcome.pending_penalty_decision = False
        outcome.penalty_choice = None
        result = MagicMock()
        result.result_type = result_type
        outcome.result = result
        return outcome

    def test_flags_stuffed(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=-2)
        flags = formatter._get_flags(outcome, outcome.result, -2)
        assert flags['is_stuffed'] is True

    def test_flags_not_stuffed_on_incomplete(self, formatter):
        outcome = self._mock_outcome(ResultType.INCOMPLETE, yards=0)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_stuffed'] is False

    def test_flags_big_play(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=12)
        flags = formatter._get_flags(outcome, outcome.result, 12)
        assert flags['is_big_play'] is True

    def test_flags_explosive(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, yards=25)
        flags = formatter._get_flags(outcome, outcome.result, 25)
        assert flags['is_explosive'] is True

    def test_flags_turnover(self, formatter):
        outcome = self._mock_outcome(ResultType.FUMBLE, turnover=True)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_turnover'] is True

    def test_flags_interception(self, formatter):
        result = MagicMock()
        result.result_type = "INTERCEPTION_RETURN"
        outcome = MagicMock()
        outcome.yards_gained = 0
        outcome.turnover = True
        outcome.first_down = False
        outcome.touchdown = False
        outcome.safety = False
        outcome.result = result
        flags = formatter._get_flags(outcome, result, 0)
        assert flags['is_interception'] is True

    def test_flags_fumble(self, formatter):
        outcome = self._mock_outcome(ResultType.FUMBLE)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_fumble'] is True

    def test_flags_touchdown(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, touchdown=True)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_touchdown'] is True

    def test_flags_first_down(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, first_down=True)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_first_down'] is True

    def test_flags_safety(self, formatter):
        outcome = self._mock_outcome(ResultType.YARDS, safety=True)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_safety'] is True

    def test_flags_sack(self, formatter):
        outcome = self._mock_outcome(ResultType.SACK)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_sack'] is True

    def test_flags_breakaway(self, formatter):
        outcome = self._mock_outcome(ResultType.BREAKAWAY)
        flags = formatter._get_flags(outcome, outcome.result, 0)
        assert flags['is_breakaway'] is True


class TestResultFormatterPenaltyInfo:
    """Tests for _get_penalty_info() branches."""

    @pytest.fixture
    def formatter(self):
        return ResultFormatter("SF '83", "DAL '83")

    def test_penalty_info_no_penalty(self, formatter):
        outcome = MagicMock()
        outcome.penalty_choice = None
        outcome.pending_penalty_decision = False
        info = formatter._get_penalty_info(outcome)
        assert info['pending'] is False
        assert info['description'] == ''
        assert info['options'] == []
        assert info['offended_team'] == ''

    def test_penalty_info_offense_offended_filters_def(self, formatter):
        penalty_opt = MagicMock()
        penalty_opt.penalty_type = "DEF"
        penalty_opt.description = "Defensive holding"
        penalty_opt.raw_result = "DEF 5"
        penalty_opt.yards = 5
        penalty_opt.auto_first_down = False
        penalty_opt.is_pass_interference = False
        penalty_choice = MagicMock()
        penalty_choice.penalty_options = [penalty_opt]
        penalty_choice.offended_team = "offense"
        penalty_choice.play_result = None
        penalty_choice.offsetting = False
        penalty_choice.is_pass_interference = False
        outcome = MagicMock()
        outcome.penalty_choice = penalty_choice
        outcome.pending_penalty_decision = True
        info = formatter._get_penalty_info(outcome)
        assert info['pending'] is True
        assert len(info['options']) == 1
        assert info['options'][0]['type'] == "DEF"

    def test_penalty_info_defense_offended_filters_off(self, formatter):
        penalty_opt = MagicMock()
        penalty_opt.penalty_type = "OFF"
        penalty_opt.description = "False start"
        penalty_opt.raw_result = "OFF 5"
        penalty_opt.yards = 5
        penalty_opt.auto_first_down = False
        penalty_opt.is_pass_interference = False
        penalty_choice = MagicMock()
        penalty_choice.penalty_options = [penalty_opt]
        penalty_choice.offended_team = "defense"
        penalty_choice.play_result = None
        penalty_choice.offsetting = False
        penalty_choice.is_pass_interference = False
        outcome = MagicMock()
        outcome.penalty_choice = penalty_choice
        outcome.pending_penalty_decision = True
        info = formatter._get_penalty_info(outcome)
        assert info['pending'] is True
        assert len(info['options']) == 1
        assert info['options'][0]['type'] == "OFF"

    def test_penalty_info_pi_filtered_for_offense(self, formatter):
        pi_opt = MagicMock()
        pi_opt.penalty_type = "PI"
        pi_opt.description = "Pass interference"
        pi_opt.raw_result = "PI 15"
        pi_opt.yards = 15
        pi_opt.auto_first_down = True
        pi_opt.is_pass_interference = True
        penalty_choice = MagicMock()
        penalty_choice.penalty_options = [pi_opt]
        penalty_choice.offended_team = "offense"
        penalty_choice.play_result = None
        penalty_choice.offsetting = False
        penalty_choice.is_pass_interference = True
        outcome = MagicMock()
        outcome.penalty_choice = penalty_choice
        outcome.pending_penalty_decision = True
        info = formatter._get_penalty_info(outcome)
        assert len(info['options']) == 1
        assert info['options'][0]['type'] == "PI"

    def test_penalty_info_with_play_result(self, formatter):
        play_res = MagicMock()
        play_res.yards = 5
        play_res.description = "Gain of 5"
        play_res.raw_result = "5"
        play_res.turnover = False
        play_res.touchdown = False
        penalty_opt = MagicMock()
        penalty_opt.penalty_type = "DEF"
        penalty_opt.description = "Defensive holding"
        penalty_opt.raw_result = "DEF 5"
        penalty_opt.yards = 5
        penalty_opt.auto_first_down = False
        penalty_opt.is_pass_interference = False
        penalty_choice = MagicMock()
        penalty_choice.penalty_options = [penalty_opt]
        penalty_choice.offended_team = "offense"
        penalty_choice.play_result = play_res
        penalty_choice.offsetting = False
        penalty_choice.is_pass_interference = False
        outcome = MagicMock()
        outcome.penalty_choice = penalty_choice
        outcome.pending_penalty_decision = True
        info = formatter._get_penalty_info(outcome)
        assert info['play_result_description'] == "Gain of 5"

    def test_penalty_info_description_from_first_option(self, formatter):
        opt1 = MagicMock()
        opt1.description = "First penalty option"
        opt2 = MagicMock()
        opt2.description = "Second penalty option"
        penalty_choice = MagicMock()
        penalty_choice.penalty_options = [opt1, opt2]
        penalty_choice.offended_team = "offense"
        penalty_choice.play_result = None
        penalty_choice.offsetting = False
        penalty_choice.is_pass_interference = False
        outcome = MagicMock()
        outcome.penalty_choice = penalty_choice
        outcome.pending_penalty_decision = True
        info = formatter._get_penalty_info(outcome)
        assert info['description'] == "First penalty option"


class TestFormatPlayResult:
    """Tests for format_play_result() convenience function."""

    def test_format_play_result_basic(self):
        from paydirt.result_formatter import format_play_result
        outcome = MagicMock()
        outcome.play_type = PlayType.LINE_PLUNGE
        outcome.yards_gained = 4
        outcome.touchdown = False
        outcome.turnover = False
        outcome.safety = False
        outcome.first_down = False
        outcome.pending_penalty_decision = False
        outcome.penalty_choice = None
        result = MagicMock()
        result.result_type = ResultType.YARDS
        outcome.result = result
        formatted = format_play_result(outcome, "SF '83", "DAL '83")
        assert formatted.headline == "Gain of 4"
        assert formatted.yards == 4
        assert formatted.is_gain is True
