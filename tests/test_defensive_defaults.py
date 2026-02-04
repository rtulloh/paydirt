"""
Tests for defensive play default suggestions.

The defensive default should consider both down and distance:
- 1st and 10: Standard (A) - balanced, offense could run or pass
- 2nd and 6+: Short Pass (D) - medium-long situation
- 3rd/4th and 8+: Long Pass (E) - expect deep pass
- Short yardage (≤2): Short Yardage (B) - expect run
"""
import pytest
from unittest.mock import MagicMock

from paydirt.game_engine import GameState


def get_defensive_default(down: int, yards_to_go: int) -> tuple[str, str]:
    """
    Replicate the defensive default logic from interactive_game.py.
    Returns (default_key, default_name).
    """
    if yards_to_go <= 2:
        return 'B', 'Short Yardage (B)'
    elif down >= 3 and yards_to_go >= 8:
        return 'E', 'Long Pass (E)'
    elif down >= 2 and yards_to_go >= 6:
        return 'D', 'Short Pass (D)'
    else:
        return 'A', 'Standard (A)'


class TestDefensiveDefaults:
    """Tests for defensive play default suggestions based on down and distance."""
    
    def test_first_and_10_is_standard(self):
        """1st and 10 should default to Standard (A), not Long Pass."""
        default_key, default_name = get_defensive_default(down=1, yards_to_go=10)
        assert default_key == 'A'
        assert 'Standard' in default_name
    
    def test_first_and_5_is_standard(self):
        """1st and 5 (after penalty) should default to Standard (A)."""
        default_key, default_name = get_defensive_default(down=1, yards_to_go=5)
        assert default_key == 'A'
    
    def test_second_and_10_is_short_pass(self):
        """2nd and 10 should default to Short Pass (D)."""
        default_key, default_name = get_defensive_default(down=2, yards_to_go=10)
        assert default_key == 'D'
        assert 'Short Pass' in default_name
    
    def test_second_and_6_is_short_pass(self):
        """2nd and 6 should default to Short Pass (D)."""
        default_key, default_name = get_defensive_default(down=2, yards_to_go=6)
        assert default_key == 'D'
    
    def test_second_and_5_is_standard(self):
        """2nd and 5 should default to Standard (A)."""
        default_key, default_name = get_defensive_default(down=2, yards_to_go=5)
        assert default_key == 'A'
    
    def test_third_and_long_is_long_pass(self):
        """3rd and 8+ should default to Long Pass (E)."""
        default_key, default_name = get_defensive_default(down=3, yards_to_go=8)
        assert default_key == 'E'
        assert 'Long Pass' in default_name
    
    def test_third_and_12_is_long_pass(self):
        """3rd and 12 should default to Long Pass (E)."""
        default_key, default_name = get_defensive_default(down=3, yards_to_go=12)
        assert default_key == 'E'
    
    def test_third_and_7_is_short_pass(self):
        """3rd and 7 should default to Short Pass (D)."""
        default_key, default_name = get_defensive_default(down=3, yards_to_go=7)
        assert default_key == 'D'
    
    def test_third_and_3_is_standard(self):
        """3rd and 3 should default to Standard (A)."""
        default_key, default_name = get_defensive_default(down=3, yards_to_go=3)
        assert default_key == 'A'
    
    def test_fourth_and_long_is_long_pass(self):
        """4th and 10 should default to Long Pass (E)."""
        default_key, default_name = get_defensive_default(down=4, yards_to_go=10)
        assert default_key == 'E'
    
    def test_fourth_and_1_is_short_yardage(self):
        """4th and 1 should default to Short Yardage (B)."""
        default_key, default_name = get_defensive_default(down=4, yards_to_go=1)
        assert default_key == 'B'
        assert 'Short Yardage' in default_name
    
    def test_fourth_and_2_is_short_yardage(self):
        """4th and 2 should default to Short Yardage (B)."""
        default_key, default_name = get_defensive_default(down=4, yards_to_go=2)
        assert default_key == 'B'
    
    def test_goal_line_short_yardage(self):
        """Goal line (1st and goal from 2) should default to Short Yardage (B)."""
        default_key, default_name = get_defensive_default(down=1, yards_to_go=2)
        assert default_key == 'B'
    
    def test_second_and_1_is_short_yardage(self):
        """2nd and 1 should default to Short Yardage (B)."""
        default_key, default_name = get_defensive_default(down=2, yards_to_go=1)
        assert default_key == 'B'


def get_situation_advice(down: int, yards_to_go: int, ball_position: int = 50) -> str:
    """
    Replicate the situation advice logic from interactive_game.py.
    Returns the situation advice string or empty string if no specific advice.
    """
    if yards_to_go <= 2:
        return "Short yardage - expect a run"
    elif down >= 2 and yards_to_go >= 8:
        # Long yardage only applies on 2nd down or later (1st and 10 is standard)
        return "Long yardage - expect a pass"
    elif down == 4 and ball_position >= 55:
        return "Field goal range - they may kick"
    elif down == 1:
        return "First down - balanced attack likely"
    return ""


class TestSituationAdvice:
    """Tests for situation advice text displayed to the user."""
    
    def test_first_and_10_is_not_long_yardage(self):
        """1st and 10 should NOT say 'Long yardage' - it's standard.
        
        Bug fix: Previously 1st and 10 incorrectly showed 'Long yardage - expect a pass'
        because the condition only checked yards_to_go >= 8, not the down.
        """
        advice = get_situation_advice(down=1, yards_to_go=10)
        assert "Long yardage" not in advice
        assert "First down" in advice or "balanced" in advice.lower()
    
    def test_first_and_15_is_still_first_down(self):
        """1st and 15 (after penalty) should still say 'First down'."""
        advice = get_situation_advice(down=1, yards_to_go=15)
        assert "Long yardage" not in advice
        assert "First down" in advice
    
    def test_second_and_10_is_long_yardage(self):
        """2nd and 10 should say 'Long yardage'."""
        advice = get_situation_advice(down=2, yards_to_go=10)
        assert "Long yardage" in advice
    
    def test_second_and_8_is_long_yardage(self):
        """2nd and 8 should say 'Long yardage'."""
        advice = get_situation_advice(down=2, yards_to_go=8)
        assert "Long yardage" in advice
    
    def test_second_and_7_is_not_long_yardage(self):
        """2nd and 7 should NOT say 'Long yardage'."""
        advice = get_situation_advice(down=2, yards_to_go=7)
        assert "Long yardage" not in advice
    
    def test_third_and_long_is_long_yardage(self):
        """3rd and 12 should say 'Long yardage'."""
        advice = get_situation_advice(down=3, yards_to_go=12)
        assert "Long yardage" in advice
    
    def test_short_yardage_advice(self):
        """Short yardage situations should say 'expect a run'."""
        advice = get_situation_advice(down=3, yards_to_go=2)
        assert "Short yardage" in advice
        assert "run" in advice.lower()
    
    def test_fourth_down_field_goal_range(self):
        """4th down in field goal range should mention they may kick."""
        advice = get_situation_advice(down=4, yards_to_go=5, ball_position=60)
        assert "kick" in advice.lower() or "Field goal" in advice
