"""
Tests for shared utility functions.
"""
from paydirt.utils import (
    ordinal_suffix, ordinal, format_down_and_distance, format_time,
    format_field_position, format_field_position_with_team, parse_field_position,
    format_dice_roll, format_play_dice_line,
    clamp_ball_position, yards_to_goal, fg_distance
)


class TestOrdinalSuffix:
    """Tests for ordinal_suffix function."""
    
    def test_first(self):
        assert ordinal_suffix(1) == "st"
    
    def test_second(self):
        assert ordinal_suffix(2) == "nd"
    
    def test_third(self):
        assert ordinal_suffix(3) == "rd"
    
    def test_fourth(self):
        assert ordinal_suffix(4) == "th"
    
    def test_eleventh(self):
        """11th, 12th, 13th are special cases."""
        assert ordinal_suffix(11) == "th"
        assert ordinal_suffix(12) == "th"
        assert ordinal_suffix(13) == "th"
    
    def test_twenty_first(self):
        assert ordinal_suffix(21) == "st"
    
    def test_twenty_second(self):
        assert ordinal_suffix(22) == "nd"


class TestOrdinal:
    """Tests for ordinal function."""
    
    def test_first(self):
        assert ordinal(1) == "1st"
    
    def test_second(self):
        assert ordinal(2) == "2nd"
    
    def test_third(self):
        assert ordinal(3) == "3rd"
    
    def test_fourth(self):
        assert ordinal(4) == "4th"


class TestFormatDownAndDistance:
    """Tests for format_down_and_distance function."""
    
    def test_first_and_ten(self):
        assert format_down_and_distance(1, 10) == "1st & 10"
    
    def test_third_and_five(self):
        assert format_down_and_distance(3, 5) == "3rd & 5"
    
    def test_fourth_and_goal(self):
        """Should show 'Goal' when yards_to_goal <= 10 and >= yards_to_go."""
        assert format_down_and_distance(4, 3, yards_to_goal=3) == "4th & Goal"
    
    def test_first_and_goal(self):
        assert format_down_and_distance(1, 10, yards_to_goal=8) == "1st & Goal"
    
    def test_not_goal_when_far(self):
        """Should not show 'Goal' when yards_to_goal > 10."""
        assert format_down_and_distance(1, 10, yards_to_goal=15) == "1st & 10"


class TestFormatTime:
    """Tests for format_time function."""
    
    def test_full_minutes(self):
        assert format_time(5.0) == "5:00"
    
    def test_half_minute(self):
        assert format_time(2.5) == "2:30"
    
    def test_quarter_minute(self):
        assert format_time(1.25) == "1:15"
    
    def test_zero(self):
        assert format_time(0.0) == "0:00"
    
    def test_seconds_only(self):
        assert format_time(0.75) == "0:45"


class TestFormatFieldPosition:
    """Tests for format_field_position function."""
    
    def test_own_territory(self):
        assert format_field_position(35) == "own 35"
    
    def test_own_one_yard_line(self):
        assert format_field_position(1) == "own 1"
    
    def test_midfield(self):
        assert format_field_position(50) == "midfield"
    
    def test_opponent_territory(self):
        assert format_field_position(65) == "opponent's 35"
    
    def test_opponent_one_yard_line(self):
        assert format_field_position(99) == "opponent's 1"
    
    def test_short_style_own(self):
        assert format_field_position(35, style="short") == "own 35"
    
    def test_short_style_opponent(self):
        assert format_field_position(65, style="short") == "opp 35"
    
    def test_short_style_midfield(self):
        assert format_field_position(50, style="short") == "midfield"
    
    def test_position_zero_displays_as_one(self):
        """Position 0 (own goal line) should display as own 1."""
        assert format_field_position(0) == "own 1"
    
    def test_position_100_is_end_zone(self):
        """Position 100 (opponent's end zone) should display as opponent's 1."""
        assert format_field_position(100) == "opponent's 1"
    
    def test_position_zero_short_style(self):
        """Position 0 in short style should display as own 1."""
        assert format_field_position(0, style="short") == "own 1"
    
    def test_position_100_short_style(self):
        """Position 100 in short style should display as opp 1."""
        assert format_field_position(100, style="short") == "opp 1"


class TestFormatFieldPositionWithTeam:
    """Tests for format_field_position_with_team function."""
    
    def test_own_territory(self):
        assert format_field_position_with_team(35, "GB", "CHI") == "GB 35"
    
    def test_opponent_territory(self):
        assert format_field_position_with_team(65, "GB", "CHI") == "CHI 35"
    
    def test_midfield(self):
        assert format_field_position_with_team(50, "GB", "CHI") == "midfield"
    
    def test_strips_year_suffix(self):
        """Should strip year suffix like '83 from team names."""
        assert format_field_position_with_team(35, "GB '83", "CHI '83") == "GB 35"
        assert format_field_position_with_team(65, "GB '83", "CHI '83") == "CHI 35"
    
    def test_position_zero_is_own_one(self):
        """Position 0 (own goal line) should display as offense team 1."""
        assert format_field_position_with_team(0, "GB", "CHI") == "GB 1"
    
    def test_position_100_is_end_zone(self):
        """Position 100 (opponent's end zone) should display as defense team 1."""
        assert format_field_position_with_team(100, "GB", "CHI") == "CHI 1"


class TestParseFieldPosition:
    """Tests for parse_field_position function."""
    
    def test_own_territory(self):
        assert parse_field_position("own 35") == 35
    
    def test_opponent_territory_verbose(self):
        assert parse_field_position("opponent's 20") == 80
    
    def test_opponent_territory_short(self):
        assert parse_field_position("opp 20") == 80
    
    def test_midfield_word(self):
        assert parse_field_position("midfield") == 50
    
    def test_midfield_number(self):
        assert parse_field_position("50") == 50
    
    def test_case_insensitive(self):
        assert parse_field_position("OWN 35") == 35
        assert parse_field_position("MIDFIELD") == 50
    
    def test_plain_number(self):
        # Lines 277-278 - parse plain number as own territory
        assert parse_field_position("35") == 35
        assert parse_field_position("20") == 20
    
    def test_unrecognized_format_fallback(self):
        # Lines 279-284 - unrecognized format falls back to 50
        assert parse_field_position("GB 35") == 50  # Team-specific not supported
        assert parse_field_position("invalid") == 50
        assert parse_field_position("foo bar") == 50


class TestFormatDiceRoll:
    """Tests for format_dice_roll function."""
    
    def test_standard_with_prefix_and_result(self):
        assert format_dice_roll(28, result="+5", prefix="O") == 'O:28→"+5"'
    
    def test_standard_with_dice_desc(self):
        assert format_dice_roll(28, "B2+W5+W3=28", "+5", "O") == 'O:B2+W5+W3=28→"+5"'
    
    def test_standard_no_prefix(self):
        assert format_dice_roll(28, result="+5") == '28→"+5"'
    
    def test_standard_no_result(self):
        assert format_dice_roll(28, prefix="R") == "R:28"
    
    def test_verbose_style(self):
        assert format_dice_roll(28, result="+5", style="verbose") == 'Roll: 28 → "+5"'
    
    def test_verbose_with_dice_desc(self):
        assert format_dice_roll(28, "B2+W5+W3=28", "+5", style="verbose") == 'Roll: B2+W5+W3=28 → "+5"'
    
    def test_verbose_no_result(self):
        assert format_dice_roll(28, style="verbose") == "Roll: 28"
    
    def test_standard_no_prefix_no_result(self):
        # Line 200 - no prefix, no result, just returns the roll as string
        assert format_dice_roll(28) == "28"
    
    def test_standard_with_dice_desc_no_prefix_no_result(self):
        # With dice_desc but no prefix or result
        assert format_dice_roll(28, dice_desc="B2+W5+W3=28") == "B2+W5+W3=28"


class TestFormatPlayDiceLine:
    """Tests for format_play_dice_line function."""
    
    def test_basic_format(self):
        result = format_play_dice_line(28, "+5", "12", "A")
        assert result == '(O:28→"+5" | D:12→"A")'
    
    def test_with_priority(self):
        result = format_play_dice_line(28, "+5", "12", "A", priority="O-HI")
        assert result == '(O:28→"+5" | D:12→"A" | O-HI)'
    
    def test_with_extra_info(self):
        result = format_play_dice_line(28, "F+5", "12", "A", priority="O-HI", extra_info="F@33")
        assert result == '(O:28→"F+5" | D:12→"A" | O-HI | F@33)'
    
    def test_with_dice_descriptions(self):
        result = format_play_dice_line(28, "+5", "12", "A", 
                                       off_dice_desc="B2+W5+W3=28", 
                                       def_dice_desc="R1+G2=12")
        assert result == '(O:B2+W5+W3=28→"+5" | D:R1+G2=12→"A")'


class TestClampBallPosition:
    """Tests for clamp_ball_position function."""
    
    def test_valid_position_unchanged(self):
        assert clamp_ball_position(50) == 50
        assert clamp_ball_position(1) == 1
        assert clamp_ball_position(99) == 99
    
    def test_zero_clamped_to_one(self):
        assert clamp_ball_position(0) == 1
    
    def test_hundred_clamped_to_99(self):
        assert clamp_ball_position(100) == 99
    
    def test_negative_clamped_to_one(self):
        assert clamp_ball_position(-5) == 1
        assert clamp_ball_position(-100) == 1
    
    def test_over_hundred_clamped_to_99(self):
        assert clamp_ball_position(105) == 99
        assert clamp_ball_position(200) == 99


class TestYardsToGoal:
    """Tests for yards_to_goal function."""
    
    def test_own_20(self):
        assert yards_to_goal(20) == 80
    
    def test_opponent_20(self):
        assert yards_to_goal(80) == 20
    
    def test_midfield(self):
        assert yards_to_goal(50) == 50
    
    def test_goal_line(self):
        assert yards_to_goal(99) == 1
    
    def test_own_1(self):
        assert yards_to_goal(1) == 99


class TestFgDistance:
    """Tests for fg_distance function."""
    
    def test_opponent_20(self):
        # At opponent's 20 (position 80), FG is 20 + 17 = 37 yards
        assert fg_distance(80) == 37
    
    def test_midfield(self):
        # At midfield (position 50), FG is 50 + 17 = 67 yards
        assert fg_distance(50) == 67
    
    def test_opponent_3(self):
        # At opponent's 3 (position 97), FG is 3 + 17 = 20 yards
        assert fg_distance(97) == 20
    
    def test_own_20(self):
        # At own 20 (position 20), FG is 80 + 17 = 97 yards (unrealistic but correct math)
        assert fg_distance(20) == 97
