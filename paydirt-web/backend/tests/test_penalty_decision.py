"""Tests for penalty decision state calculation."""

import pytest
import sys
from pathlib import Path

# Add parent directories to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent.parent))

from paydirt.play_resolver import PlayResult, ResultType


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


class TestPuntPenaltyDecision:
    """Tests for punt penalty decision with penalty_index parameter."""

    def test_punt_penalty_keep_return_gives_possession(self):
        """
        When receiving team selects 'keep return + penalty yards', they should
        get possession with first down, not another punt.
        
        This tests the fix for the bug where penalty_index was not being passed
        to apply_punt_penalty_decision, causing all decisions to default to
        'replay punt' (index 0).
        """
        from unittest.mock import MagicMock
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.game_state import PlayOutcome
        from paydirt.models import PlayType, DefenseType
        from paydirt.play_resolver import PlayResult, ResultType, PenaltyChoice, PenaltyOption

        # Create mock charts
        home_chart = MagicMock()
        home_chart.peripheral.team_name = "Home"
        home_chart.peripheral.short_name = "HOM"
        away_chart = MagicMock()
        away_chart.peripheral.team_name = "Away"
        away_chart.peripheral.short_name = "AWY"

        engine = PaydirtGameEngine(home_chart, away_chart)
        
        # Set up pending punt state (simulating a punt that happened)
        engine._pending_punt_state = {
            'ball_position': 50,
            'final_position': 35,  # Punt returned to own 35
            'punt_yards': 35,
            'return_yards': 15,
            'punt_penalty_yards': 5,
            'is_offensive_penalty': True,  # Kicking team committed foul
            'field_pos_before': "MIDFIELD",
            'ytg_before': 10,
        }
        
        # Create outcome with penalty choice
        penalty_options = [
            PenaltyOption(
                penalty_type="OFF 5X",
                raw_result="REPLAY_PUNT",
                yards=5,
                description="Replay punt from own 30",
                auto_first_down=False
            ),
            PenaltyOption(
                penalty_type="OFF 5",
                raw_result="KEEP_RETURN",
                yards=5,
                description="Keep return + 5 yards to own 40",
                auto_first_down=True
            ),
        ]
        
        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.NORMAL,
            result=PlayResult(ResultType.YARDS, 35, "Punt 35 yards, returned 15 yards"),
            yards_gained=35,
            pending_penalty_decision=True,
            penalty_choice=PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 35, "Punt 35 yards"),
                penalty_options=penalty_options,
                offended_team="defense",
                offsetting=False,
                is_pass_interference=False,
                reroll_log=[]
            ),
            field_position_before="MIDFIELD",
            field_position_after="OWN 35",
            description="Punt 35 yards, returned 15 yards to own 35"
        )
        
        # Test with penalty_index=1 (keep return option)
        # This simulates what routes.py should do when user selects option [3]
        result = engine.apply_punt_penalty_decision(
            outcome, 
            accept_penalty=False,  # Decline penalty, keep play result
            penalty_index=1  # Keep return + yards option
        )
        
        # Verify possession switched to receiving team
        assert engine.state.is_home_possession == True  # Home was receiving
        assert engine.state.down == 1
        assert engine.state.yards_to_go == 10
        
        # Verify ball position is at return position + penalty yards
        # final_position (35) + penalty_yards (5) = 40
        # But we need to account for which team's perspective
        # The receiving team (home) should have ball at their 40
        assert engine.state.ball_position == 40
        
        # Verify it's NOT a punt (should be first down, not 4th down)
        assert engine.state.down == 1
        # Team abbreviation is HOM (from mock), not SF
        assert result.description == "Receiving team keeps result + 5 yards to HOM 40."
        
    def test_punt_penalty_replay_punt_keeps_punting(self):
        """
        When receiving team selects 'replay punt', the kicking team should
        re-punt from a new position (LOS - penalty yards).
        """
        from unittest.mock import MagicMock
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.game_state import PlayOutcome
        from paydirt.models import PlayType, DefenseType
        from paydirt.play_resolver import PlayResult, ResultType, PenaltyChoice, PenaltyOption

        home_chart = MagicMock()
        home_chart.peripheral.team_name = "Home"
        home_chart.peripheral.short_name = "HOM"
        away_chart = MagicMock()
        away_chart.peripheral.team_name = "Away"
        away_chart.peripheral.short_name = "AWY"

        engine = PaydirtGameEngine(home_chart, away_chart)
        
        # Set the current game state ball position (where the punt occurred)
        engine.state.ball_position = 45  # Kicking team at their 45
        engine.state.is_home_possession = True  # Home is kicking (offense)
        
        engine._pending_punt_state = {
            'ball_position': 45,  # Kicking team at 45
            'final_position': 20,
            'punt_yards': 25,
            'return_yards': 10,
            'punt_penalty_yards': 5,
            'is_offensive_penalty': True,
            'field_pos_before': "OWN 45",
            'ytg_before': 10,
        }
        
        penalty_options = [
            PenaltyOption(
                penalty_type="OFF 5",
                raw_result="REPLAY_PUNT",
                yards=5,
                description="Replay punt from own 40",
                auto_first_down=False
            ),
            PenaltyOption(
                penalty_type="OFF 5",
                raw_result="KEEP_RETURN",
                yards=5,
                description="Keep return + 5 yards",
                auto_first_down=True
            ),
        ]
        
        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.NORMAL,
            result=PlayResult(ResultType.YARDS, 25, "Punt 25 yards"),
            yards_gained=25,
            pending_penalty_decision=True,
            penalty_choice=PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 25, "Punt 25 yards"),
                penalty_options=penalty_options,
                offended_team="defense",
                offsetting=False,
                is_pass_interference=False,
                reroll_log=[]
            ),
            field_position_before="OPP 45",
            field_position_after="OWN 20",
            description="Punt 25 yards"
        )
        
        # Test with penalty_index=0 (replay punt option)
        result = engine.apply_punt_penalty_decision(
            outcome, 
            accept_penalty=False,
            penalty_index=0  # Replay punt option
        )
        
        # Verify ball moved back by penalty yards for kicking team
        # Original position 45 - 5 = 40
        assert engine.state.ball_position == 40
        assert engine.state.down == 4  # Still 4th down
        assert engine.state.yards_to_go == 15  # 10 + 5 penalty yards
        
        # Verify it says "punt replayed"
        assert "Punt replayed" in result.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
