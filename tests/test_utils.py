"""
Tests for shared utility functions.
"""
from paydirt.utils import ordinal_suffix, ordinal, format_down_and_distance, format_time


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
