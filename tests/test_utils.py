"""
Tests for shared utility functions.
"""
from paydirt.utils import (
    ordinal_suffix, ordinal, format_down_and_distance, format_time,
    format_field_position, format_field_position_with_team, parse_field_position
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


class TestFormatFieldPositionWithTeam:
    """Tests for format_field_position_with_team function."""
    
    def test_own_territory(self):
        assert format_field_position_with_team(35, "GB", "CHI") == "GB 35"
    
    def test_opponent_territory(self):
        assert format_field_position_with_team(65, "GB", "CHI") == "CHI 35"
    
    def test_midfield(self):
        assert format_field_position_with_team(50, "GB", "CHI") == "50"
    
    def test_strips_year_suffix(self):
        """Should strip year suffix like '83 from team names."""
        assert format_field_position_with_team(35, "GB '83", "CHI '83") == "GB 35"
        assert format_field_position_with_team(65, "GB '83", "CHI '83") == "CHI 35"


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
