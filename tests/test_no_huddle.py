"""
Tests for No Huddle Offense penalty handling per official Paydirt rules.

No Huddle Offense:
- Time benefit: Previous play counts as 20 seconds instead of 40 seconds
- Disadvantages:
  - OFF=S 10-11: Bad Snap (F-13 punt, F-7 FG, F-2 other)
  - DEF=S 10-14: Becomes OFF 5 (false start, 0 seconds, no rerolls)
"""
import pytest
from unittest.mock import patch

from paydirt.penalty_handler import (
    PenaltyType, PenaltyResult, NoHuddlePenaltyResult,
    roll_no_huddle_penalty_yardage
)


class TestNoHuddleOffensiveScrimmage:
    """Tests for OFF=S penalties in No Huddle."""
    
    def test_roll_10_11_is_bad_snap_normal_play(self):
        """Rolls 10-11 should be bad snap (F-2) on normal plays."""
        for roll in [10, 11]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B1+W{roll-10}+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S, "normal")
                
                assert result.is_bad_snap is True
                assert result.fumble_yards == -2
                assert "BAD SNAP" in result.description
    
    def test_roll_10_11_is_bad_snap_punt(self):
        """Rolls 10-11 should be bad snap (F-13) on punt attempts."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "B1+W0+W0=10")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S, "punt")
            
            assert result.is_bad_snap is True
            assert result.fumble_yards == -13
    
    def test_roll_10_11_is_bad_snap_field_goal(self):
        """Rolls 10-11 should be bad snap (F-7) on FG attempts."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(11, "B1+W1+W0=11")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S, "field_goal")
            
            assert result.is_bad_snap is True
            assert result.fumble_yards == -7
    
    def test_roll_12_29_is_5_yards(self):
        """Rolls 12-29 should be normal 5 yard penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(20, "B2+W0+W0=20")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S)
            
            assert result.is_bad_snap is False
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
    
    def test_roll_30_36_is_10_yards(self):
        """Rolls 30-36 should be 10 yard penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(33, "B3+W1+W2=33")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S)
            
            assert result.is_bad_snap is False
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 10
    
    def test_roll_37_39_is_15_yards(self):
        """Rolls 37-39 should be 15 yard penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(38, "B3+W4+W4=38")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_S)
            
            assert result.is_bad_snap is False
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 15


class TestNoHuddleDefensiveScrimmage:
    """Tests for DEF=S penalties in No Huddle."""
    
    def test_roll_10_14_is_false_start(self):
        """Rolls 10-14 should become false start (OFF 5)."""
        for roll in [10, 11, 12, 13, 14]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B1+W{roll-10}+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_S)
                
                assert result.is_false_start is True
                assert result.normal_penalty is None
                assert "FALSE START" in result.description
    
    def test_roll_15_24_is_def_5(self):
        """Rolls 15-24 should be normal DEF 5."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(20, "B2+W0+W0=20")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_S)
            
            assert result.is_false_start is False
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
            assert result.normal_penalty.automatic_first_down is False
    
    def test_roll_25_29_is_5y_yards(self):
        """Rolls 25-29 should be 5Y yards (mark from gain)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(27, "B2+W3+W4=27")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_S)
            
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
            assert result.normal_penalty.mark_from_end_of_gain is True
            assert result.normal_penalty.automatic_first_down is False
    
    def test_roll_30_35_is_5x_yards(self):
        """Rolls 30-35 should be 5X yards (auto first down)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(32, "B3+W1+W1=32")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_S)
            
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
            assert result.normal_penalty.automatic_first_down is True
            assert result.normal_penalty.mark_from_end_of_gain is True
    
    def test_roll_36_39_is_15_yards(self):
        """Rolls 36-39 should be 15 yards with auto first down."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(37, "B3+W3+W4=37")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_S)
            
            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 15
            assert result.normal_penalty.automatic_first_down is True
            assert result.normal_penalty.mark_from_end_of_gain is True


class TestNoHuddleReturnPenalties:
    """Tests for return penalties in No Huddle (same as normal)."""
    
    def test_off_r_returns_normal_penalty(self):
        """OFF=R should return normal penalty result."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(25, "B2+W2+W3=25")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_R)
            
            assert result.normal_penalty is not None
            assert result.is_bad_snap is False
            assert result.is_false_start is False
    
    def test_def_r_returns_normal_penalty(self):
        """DEF=R should return normal penalty result."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(25, "B2+W2+W3=25")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)
            
            assert result.normal_penalty is not None
            assert result.is_bad_snap is False
            assert result.is_false_start is False


class TestNoHuddleTimeSavings:
    """Tests for No Huddle time savings concept."""
    
    def test_no_huddle_concept(self):
        """
        No Huddle reduces previous play time from 40 to 20 seconds.
        This is a documentation test - actual implementation would be in game engine.
        """
        # Normal play: ~40 seconds
        # No Huddle: previous play counts as 20 seconds
        # The hurried play itself is timed as usual
        normal_play_time = 40
        no_huddle_previous_play_time = 20
        
        assert no_huddle_previous_play_time == normal_play_time // 2
