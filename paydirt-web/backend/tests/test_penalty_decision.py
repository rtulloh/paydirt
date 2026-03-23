"""Tests for penalty decision state calculation."""

import pytest
import sys
from pathlib import Path

from paydirt.play_resolver import PlayResult, ResultType

# Add parent directories to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent.parent))


def _calculate_post_play_state(
    ball_position: int,
    down: int,
    yards_to_go: int,
    play_result,
) -> dict:
    """
    Calculate the post-play down/distance/position for a pending penalty decision.
    
    When a penalty occurs, the engine state is NOT updated. This function calculates
    what the state WOULD BE if the offended team accepts the play result (declines penalty).
    """
    yards_gained = play_result.yards if hasattr(play_result, 'yards') else 0
    turnover = play_result.turnover if hasattr(play_result, 'turnover') else False
    
    # Calculate new ball position
    new_ball_position = ball_position + yards_gained
    if new_ball_position > 100:
        new_ball_position = 100
    elif new_ball_position < 0:
        new_ball_position = 0
    
    # Check for first down (yards >= yards_to_go)
    if yards_gained >= yards_to_go:
        return {
            "new_ball_position": new_ball_position,
            "new_down": 1,
            "new_yards_to_go": min(10, 100 - new_ball_position),
            "turnover": turnover,
        }
    else:
        return {
            "new_ball_position": new_ball_position,
            "new_down": down + 1,
            "new_yards_to_go": yards_to_go - yards_gained,
            "turnover": turnover,
        }


class TestCalculatePostPlayState:
    """Test _calculate_post_play_state helper function."""
    
    def _create_play_result(self, yards=0, turnover=False, touchdown=False):
        """Create a mock PlayResult object."""
        return PlayResult(
            result_type=ResultType.YARDS,
            yards=yards,
            turnover=turnover,
            touchdown=touchdown,
        )
    
    def test_first_down_when_yards_exceed_yards_to_go(self):
        """When yards gained >= yards to go, should result in first down."""
        play_result = self._create_play_result(yards=6)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["new_down"] == 1
        assert result["new_yards_to_go"] == 10
        assert result["new_ball_position"] == 56
        assert result["turnover"] is False
    
    def test_first_down_when_yards_equal_yards_to_go(self):
        """When yards gained == yards to go, should result in first down."""
        play_result = self._create_play_result(yards=5)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["new_down"] == 1
        assert result["new_yards_to_go"] == 10
        assert result["new_ball_position"] == 55
        assert result["turnover"] is False
    
    def test_not_first_down_when_yards_less_than_yards_to_go(self):
        """When yards gained < yards to go, should advance to next down."""
        play_result = self._create_play_result(yards=3)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["new_down"] == 3
        assert result["new_yards_to_go"] == 2  # 5 - 3 = 2
        assert result["new_ball_position"] == 53
        assert result["turnover"] is False
    
    def test_first_down_from_third_down(self):
        """First down from 3rd down when yards gained >= yards to go."""
        play_result = self._create_play_result(yards=8)
        
        result = _calculate_post_play_state(
            ball_position=30,
            down=3,
            yards_to_go=7,
            play_result=play_result,
        )
        
        assert result["new_down"] == 1
        assert result["new_yards_to_go"] == 10
        assert result["new_ball_position"] == 38
    
    def test_fourth_down_calculation(self):
        """4th down calculation - should still calculate correctly for display."""
        play_result = self._create_play_result(yards=2)
        
        result = _calculate_post_play_state(
            ball_position=40,
            down=4,
            yards_to_go=3,
            play_result=play_result,
        )
        
        # 4th down + 2 < 3 yards to go = would be 5th down (turnover on downs)
        assert result["new_down"] == 5
        assert result["new_yards_to_go"] == 1
        assert result["new_ball_position"] == 42
    
    def test_yards_to_go_caps_at_10(self):
        """Yards to go should cap at 10 when ball is close to goal."""
        play_result = self._create_play_result(yards=5)
        
        result = _calculate_post_play_state(
            ball_position=90,  # 10 yards from goal
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["new_down"] == 1
        assert result["new_yards_to_go"] == 5  # min(10, 100-95) = 5
        assert result["new_ball_position"] == 95
    
    def test_touchdown_ball_position(self):
        """When play results in TD, ball should be at 100."""
        play_result = self._create_play_result(yards=15, touchdown=True)
        
        result = _calculate_post_play_state(
            ball_position=90,
            down=2,
            yards_to_go=10,
            play_result=play_result,
        )
        
        assert result["new_ball_position"] == 100  # Capped at 100
    
    def test_negative_yards(self):
        """When play loses yards, should handle correctly."""
        play_result = self._create_play_result(yards=-3)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["new_down"] == 3
        assert result["new_yards_to_go"] == 8  # 5 - (-3) = 8
        assert result["new_ball_position"] == 47  # 50 + (-3) = 47
    
    def test_zero_yards_gained(self):
        """When no yards gained, should advance down."""
        play_result = self._create_play_result(yards=0)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=1,
            yards_to_go=10,
            play_result=play_result,
        )
        
        assert result["new_down"] == 2
        assert result["new_yards_to_go"] == 10
        assert result["new_ball_position"] == 50
    
    def test_turnover_preserved(self):
        """Turnover flag should be preserved."""
        play_result = self._create_play_result(yards=5, turnover=True)
        
        result = _calculate_post_play_state(
            ball_position=50,
            down=2,
            yards_to_go=5,
            play_result=play_result,
        )
        
        assert result["turnover"] is True
        assert result["new_ball_position"] == 55


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
