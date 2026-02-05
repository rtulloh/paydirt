"""
Tests for variable yardage entries per official Paydirt rules.

Variable yardage symbols:
- DS: Direct Sum of the three dice (1-13 range)
- X: 40 minus the normal offensive total (1-30 range)
- T1: The normal offensive total (10-39)
- T2: Total of two consecutive offensive dice rolls (20-78)
- T3: Total of three consecutive offensive dice rolls (30-117)

Negative versions (-DS, -X, -T1, etc.) return negative yardage.
"""
from unittest.mock import patch

from paydirt.play_resolver import (
    resolve_variable_yardage, is_variable_yardage, parse_result_string,
    roll_offensive_dice_detailed, ResultType
)


class TestIsVariableYardage:
    """Tests for is_variable_yardage function."""
    
    def test_ds_is_variable(self):
        """DS should be recognized as variable yardage."""
        assert is_variable_yardage("DS") is True
        assert is_variable_yardage("ds") is True
        assert is_variable_yardage("-DS") is True
        assert is_variable_yardage("DS-") is True
    
    def test_x_is_variable(self):
        """X should be recognized as variable yardage."""
        assert is_variable_yardage("X") is True
        assert is_variable_yardage("x") is True
        assert is_variable_yardage("-X") is True
    
    def test_t1_is_variable(self):
        """T1 should be recognized as variable yardage."""
        assert is_variable_yardage("T1") is True
        assert is_variable_yardage("t1") is True
        assert is_variable_yardage("-T1") is True
    
    def test_t2_is_variable(self):
        """T2 should be recognized as variable yardage."""
        assert is_variable_yardage("T2") is True
        assert is_variable_yardage("-T2") is True
    
    def test_t3_is_variable(self):
        """T3 should be recognized as variable yardage."""
        assert is_variable_yardage("T3") is True
        assert is_variable_yardage("-T3") is True
    
    def test_regular_numbers_not_variable(self):
        """Regular numbers should not be variable yardage."""
        assert is_variable_yardage("5") is False
        assert is_variable_yardage("-3") is False
        assert is_variable_yardage("15") is False
    
    def test_empty_not_variable(self):
        """Empty strings should not be variable yardage."""
        assert is_variable_yardage("") is False
        assert is_variable_yardage(None) is False


class TestResolveVariableYardage:
    """Tests for resolve_variable_yardage function."""
    
    def test_ds_returns_direct_sum(self):
        """DS should return sum of all three dice values."""
        with patch('paydirt.play_resolver.roll_offensive_dice_detailed') as mock_roll:
            # Black=2, White1=3, White2=4 -> DS = 2+3+4 = 9
            mock_roll.return_value = (27, 2, 3, 4, 9, "B2+W3+W4=27 (DS=9)")
            
            yards, desc = resolve_variable_yardage("DS")
            
            assert yards == 9
            assert "DS=9" in desc
    
    def test_x_returns_40_minus_total(self):
        """X should return 40 minus the normal offensive total."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.return_value = (25, "B2+W2+W3=25")
            
            yards, desc = resolve_variable_yardage("X")
            
            assert yards == 15  # 40 - 25 = 15
            assert "X=40-25=15" in desc
    
    def test_t1_returns_offensive_total(self):
        """T1 should return the normal offensive total."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.return_value = (33, "B3+W1+W2=33")
            
            yards, desc = resolve_variable_yardage("T1")
            
            assert yards == 33
            assert "T1=33" in desc
    
    def test_t2_returns_sum_of_two_rolls(self):
        """T2 should return sum of two consecutive rolls."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.side_effect = [
                (20, "B2+W0+W0=20"),
                (15, "B1+W2+W3=15"),
            ]
            
            yards, desc = resolve_variable_yardage("T2")
            
            assert yards == 35  # 20 + 15
            assert "T2=20+15=35" in desc
    
    def test_t3_returns_sum_of_three_rolls(self):
        """T3 should return sum of three consecutive rolls."""
        with patch('paydirt.play_resolver.roll_chart_dice') as mock_roll:
            mock_roll.side_effect = [
                (20, "B2+W0+W0=20"),
                (15, "B1+W2+W3=15"),
                (30, "B3+W0+W0=30"),
            ]
            
            yards, desc = resolve_variable_yardage("T3")
            
            assert yards == 65  # 20 + 15 + 30
            assert "T3=20+15+30=65" in desc
    
    def test_negative_ds(self):
        """Negative DS should return negative yardage."""
        with patch('paydirt.play_resolver.roll_offensive_dice_detailed') as mock_roll:
            mock_roll.return_value = (27, 2, 3, 4, 9, "B2+W3+W4=27 (DS=9)")
            
            yards, desc = resolve_variable_yardage("-DS")
            
            assert yards == -9
            assert "-DS" in desc or "DS=9" in desc
    
    def test_negative_suffix_format(self):
        """DS- format (suffix negative) should also work."""
        with patch('paydirt.play_resolver.roll_offensive_dice_detailed') as mock_roll:
            mock_roll.return_value = (27, 2, 3, 4, 9, "B2+W3+W4=27 (DS=9)")
            
            yards, desc = resolve_variable_yardage("DS-")
            
            assert yards == -9


class TestRollOffensiveDiceDetailed:
    """Tests for roll_offensive_dice_detailed function."""
    
    def test_returns_all_components(self):
        """Should return total, black, white1, white2, direct_sum, desc."""
        total, black, white1, white2, direct_sum, desc = roll_offensive_dice_detailed()
        
        # Verify ranges
        assert 10 <= total <= 39
        assert black in [1, 2, 3]
        assert 0 <= white1 <= 5
        assert 0 <= white2 <= 5
        assert direct_sum == black + white1 + white2
        assert 1 <= direct_sum <= 13  # 1+0+0 to 3+5+5
    
    def test_total_calculation(self):
        """Total should be black*10 + min(white1+white2, 9)."""
        for _ in range(20):
            total, black, white1, white2, direct_sum, desc = roll_offensive_dice_detailed()
            expected_total = (black * 10) + min(white1 + white2, 9)
            assert total == expected_total


class TestParseResultStringVariableYardage:
    """Tests for parse_result_string with variable yardage."""
    
    def test_parse_ds_result(self):
        """DS result should be parsed and resolved."""
        with patch('paydirt.play_resolver.resolve_variable_yardage') as mock_resolve:
            mock_resolve.return_value = (8, "DS=8")
            
            result = parse_result_string("DS")
            
            assert result.result_type == ResultType.YARDS
            assert result.yards == 8
    
    def test_parse_t1_result(self):
        """T1 result should be parsed and resolved."""
        with patch('paydirt.play_resolver.resolve_variable_yardage') as mock_resolve:
            mock_resolve.return_value = (25, "T1=25")
            
            result = parse_result_string("T1")
            
            assert result.result_type == ResultType.YARDS
            assert result.yards == 25
    
    def test_parse_negative_variable(self):
        """Negative variable yardage should be parsed correctly."""
        with patch('paydirt.play_resolver.resolve_variable_yardage') as mock_resolve:
            mock_resolve.return_value = (-10, "-X=10")
            
            result = parse_result_string("-X")
            
            assert result.result_type == ResultType.YARDS
            assert result.yards == -10
    
    def test_parse_variable_with_out_of_bounds(self):
        """Variable yardage with out-of-bounds marker should work."""
        with patch('paydirt.play_resolver.resolve_variable_yardage') as mock_resolve:
            mock_resolve.return_value = (30, "T1=30")
            
            result = parse_result_string("T1*")
            
            assert result.result_type == ResultType.YARDS
            assert result.yards == 30
            assert result.out_of_bounds is True


class TestVariableYardageRanges:
    """Tests to verify variable yardage ranges are correct."""
    
    def test_ds_range(self):
        """DS should be in range 1-13."""
        for _ in range(50):
            yards, desc = resolve_variable_yardage("DS")
            assert 1 <= yards <= 13, f"DS={yards} out of range 1-13"
    
    def test_x_range(self):
        """X should be in range 1-30 (40-39 to 40-10)."""
        for _ in range(50):
            yards, desc = resolve_variable_yardage("X")
            assert 1 <= yards <= 30, f"X={yards} out of range 1-30"
    
    def test_t1_range(self):
        """T1 should be in range 10-39."""
        for _ in range(50):
            yards, desc = resolve_variable_yardage("T1")
            assert 10 <= yards <= 39, f"T1={yards} out of range 10-39"
    
    def test_t2_range(self):
        """T2 should be in range 20-78."""
        for _ in range(50):
            yards, desc = resolve_variable_yardage("T2")
            assert 20 <= yards <= 78, f"T2={yards} out of range 20-78"
    
    def test_t3_range(self):
        """T3 should be in range 30-117."""
        for _ in range(50):
            yards, desc = resolve_variable_yardage("T3")
            assert 30 <= yards <= 117, f"T3={yards} out of range 30-117"
