"""
Tests for No Huddle Offense penalty handling per official Paydirt rules.

No Huddle Offense:
- Time benefit: Previous play counts as 20 seconds instead of 40 seconds
- Disadvantages:
  - OFF=S 10-11: Bad Snap (F-13 punt, F-7 FG, F-2 other)
  - DEF=S 10-14: Becomes OFF 5 (false start, 0 seconds, no rerolls)
"""
from unittest.mock import patch

from paydirt.penalty_handler import (
    PenaltyType, roll_no_huddle_penalty_yardage
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


class TestNoHuddleOffensiveReturn:
    """Tests for OFF=R penalties in No Huddle.
    
    OFF=R: 10† = 5 yards, 11-34 = 10 yards, 35-39 = 15 yards
    Same ranges as normal table.
    """

    def test_roll_10_is_5_yards(self):
        """Roll 10 should be 5 yards († prior to change of possession)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "B1+W0+W0=10")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_R)

            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
            assert result.normal_penalty.dice_roll == 10

    def test_roll_11_34_is_10_yards(self):
        """Rolls 11-34 should be 10 yards."""
        for roll in [11, 20, 34]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B2+W0+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_R)

                assert result.normal_penalty is not None
                assert result.normal_penalty.yards == 10
                assert result.normal_penalty.dice_roll == roll

    def test_roll_35_39_is_15_yards(self):
        """Rolls 35-39 should be 15 yards."""
        for roll in [35, 37, 39]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B3+W3+W4={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_R)

                assert result.normal_penalty is not None
                assert result.normal_penalty.yards == 15
                assert result.normal_penalty.dice_roll == roll

    def test_uses_single_dice_roll(self):
        """OFF=R should use the dice rolled once, not re-roll internally."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(25, "B2+W2+W3=25")) as mock_dice:
            result = roll_no_huddle_penalty_yardage(PenaltyType.OFFENSIVE_R)

            # Should only roll once (at the top of the function)
            assert mock_dice.call_count == 1
            assert result.normal_penalty.dice_roll == 25
            assert result.normal_penalty.yards == 10


class TestNoHuddleDefensiveReturn:
    """Tests for DEF=R penalties in No Huddle.
    
    DEF=R: -- (10), 5Y (11-16††), 5X (17-19**), 15 (20-39**††)
    Same ranges as normal table.
    """

    def test_roll_10_is_minimum_5_yards(self):
        """Roll 10 has no entry (--), should use minimum 5 yards."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "B1+W0+W0=10")):
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)

            assert result.normal_penalty is not None
            assert result.normal_penalty.yards == 5
            assert result.normal_penalty.dice_roll == 10

    def test_roll_11_16_is_5y_yards(self):
        """Rolls 11-16 should be 5Y yards (marked from end of gain)."""
        for roll in [11, 14, 16]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B1+W{roll-10}+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)

                assert result.normal_penalty.yards == 5
                assert result.normal_penalty.mark_from_end_of_gain is True
                assert result.normal_penalty.automatic_first_down is False
                assert result.normal_penalty.dice_roll == roll

    def test_roll_17_19_is_5x_yards(self):
        """Rolls 17-19 should be 5X yards (automatic first down)."""
        for roll in [17, 18, 19]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B1+W{roll-10}+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)

                assert result.normal_penalty.yards == 5
                assert result.normal_penalty.automatic_first_down is True
                assert result.normal_penalty.mark_from_end_of_gain is True
                assert result.normal_penalty.dice_roll == roll

    def test_roll_20_39_is_15_yards(self):
        """Rolls 20-39 should be 15 yards with auto first down."""
        for roll in [20, 30, 39]:
            with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"B3+W0+W0={roll}")):
                result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)

                assert result.normal_penalty.yards == 15
                assert result.normal_penalty.automatic_first_down is True
                assert result.normal_penalty.mark_from_end_of_gain is True
                assert result.normal_penalty.dice_roll == roll

    def test_uses_single_dice_roll(self):
        """DEF=R should use the dice rolled once, not re-roll internally."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(25, "B2+W2+W3=25")) as mock_dice:
            result = roll_no_huddle_penalty_yardage(PenaltyType.DEFENSIVE_R)

            # Should only roll once (at the top of the function)
            assert mock_dice.call_count == 1
            assert result.normal_penalty.dice_roll == 25
            assert result.normal_penalty.yards == 15
