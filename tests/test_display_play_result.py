"""
Tests for display_play_result function to ensure correct team is shown on offense.

Bug fix: On 4th down failure (turnover on downs), the display was showing the wrong
team on offense because possession had already switched before display_play_result
was called.
"""
import pytest
from unittest.mock import MagicMock, patch
from io import StringIO

from paydirt.game_engine import GameState, PlayOutcome
from paydirt.play_resolver import PlayType, DefenseType, PlayResult, ResultType
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


def create_mock_chart(short_name: str, full_name: str) -> TeamChart:
    """Create a mock team chart for testing."""
    peripheral = PeripheralData(
        year=1983,
        team_name=full_name.split()[-1],  # e.g., "Giants" from "New York Giants"
        team_nickname=full_name.split()[-1],
        power_rating=50,
        short_name=short_name
    )
    return TeamChart(
        peripheral=peripheral,
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(),
        team_dir=""
    )


class TestDisplayPlayResultTeamIdentification:
    """Tests to ensure display_play_result shows the correct team on offense."""
    
    def test_offense_was_home_parameter_used_when_provided(self):
        """When offense_was_home is explicitly passed, it should be used."""
        # This tests the fix for the turnover on downs bug
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        
        # Create mock charts
        home_chart = create_mock_chart("Wash 83", "Washington Redskins")
        away_chart = create_mock_chart("NYG '83", "New York Giants")
        
        # Create game
        game = PaydirtGameEngine(home_chart, away_chart)
        
        # Simulate: Home team (Wash) was on offense, but possession has now switched
        # (e.g., turnover on downs after 4th down failure)
        game.state.is_home_possession = False  # Now away team has ball
        
        # Create an incomplete pass outcome (no turnover flag, but possession changed)
        result = PlayResult(
            result_type=ResultType.INCOMPLETE,
            yards=0,
            description="Incomplete pass",
            dice_roll=25,
            raw_result="INC"
        )
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=0,
            turnover=False,  # Not marked as turnover, but possession switched via next_down()
            description="Incomplete pass - turnover on downs"
        )
        
        # Capture stdout to verify correct team is shown
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Pass offense_was_home=True to indicate home team was on offense
            display_play_result(game, outcome, PlayType.MEDIUM_PASS, DefenseType.STANDARD, 
                              home_chart, offense_was_home=True)
            output = mock_stdout.getvalue()
        
        # Should show Wash 83 (home) on offense, not NYG '83 (away)
        assert "Wash 83" in output, f"Expected 'Wash 83' in output but got: {output}"
        # The play header should show the home team on offense
        assert "Wash 83 Medium Pass" in output or "THE PLAY: Wash 83" in output, \
            f"Expected home team on offense in play header but got: {output}"
    
    def test_away_team_on_offense_with_explicit_parameter(self):
        """When away team was on offense, display should show away team."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        
        home_chart = create_mock_chart("Wash 83", "Washington Redskins")
        away_chart = create_mock_chart("NYG '83", "New York Giants")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        
        # Away team was on offense, now home has ball (turnover on downs)
        game.state.is_home_possession = True
        
        result = PlayResult(
            result_type=ResultType.INCOMPLETE,
            yards=0,
            description="Incomplete pass",
            dice_roll=25,
            raw_result="INC"
        )
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=0,
            turnover=False,
            description="Incomplete pass - turnover on downs"
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Pass offense_was_home=False to indicate away team was on offense
            display_play_result(game, outcome, PlayType.MEDIUM_PASS, DefenseType.STANDARD,
                              home_chart, offense_was_home=False)
            output = mock_stdout.getvalue()
        
        # Should show NYG '83 (away) on offense
        assert "NYG '83" in output, f"Expected 'NYG '83' in output but got: {output}"
