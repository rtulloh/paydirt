"""
Tests for display_play_result function to ensure correct team is shown on offense.

Bug fix: On 4th down failure (turnover on downs), the display was showing the wrong
team on offense because possession had already switched before display_play_result
was called.
"""
from unittest.mock import patch
from io import StringIO

from paydirt.game_engine import PlayOutcome
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


class TestCompactDisplayTouchdown:
    """Tests to ensure compact display correctly shows touchdowns."""

    def test_touchdown_not_shown_as_no_gain(self):
        """TD with yards_gained=0 should show 'TOUCHDOWN!' not 'No gain'."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True

        # Create a TD outcome with yards_gained=0 (as happens with direct TD results)
        result = PlayResult(
            result_type=ResultType.TOUCHDOWN,
            yards=0,
            description="TOUCHDOWN! [Off: B1+W5+W5=19, Def: R2+G0=2]",
            dice_roll=19,
            raw_result="TD",
            defense_modifier=""
        )
        outcome = PlayOutcome(
            play_type=PlayType.LONG_PASS,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=0,
            touchdown=True,
            description="TOUCHDOWN! [Off: B1+W5+W5=19, Def: R2+G0=2]"
        )

        # Enable compact mode for this test
        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.LONG_PASS, DefenseType.STANDARD,
                                    home_chart, offense_was_home=True)
                output = mock_stdout.getvalue()

            # Should show TOUCHDOWN, not "No gain"
            assert "No gain" not in output, f"TD should not show 'No gain': {output}"
            assert "TOUCHDOWN" in output, f"Expected 'TOUCHDOWN' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact

    def test_touchdown_via_outcome_flag_not_result_type(self):
        """TD via outcome.touchdown=True (not result_type) should also show correctly."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True

        # Create outcome where result_type is YARDS but touchdown=True
        # (e.g., a long run that scores)
        result = PlayResult(
            result_type=ResultType.YARDS,
            yards=45,
            description="Offense result: 45 [Off: B3+W5+W5=38, Def: R1+G0=1]",
            dice_roll=38,
            raw_result="45",
            defense_modifier=""
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=45,
            touchdown=True,  # TD via flag, not result_type
            description="Offense result: 45 [Off: B3+W5+W5=38, Def: R1+G0=1]"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.OFF_TACKLE, DefenseType.STANDARD,
                                    home_chart, offense_was_home=True)
                output = mock_stdout.getvalue()

            assert "No gain" not in output, f"TD should not show 'No gain': {output}"
            assert "TOUCHDOWN" in output, f"Expected 'TOUCHDOWN' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact


class TestCompactDisplayTurnoverReturns:
    """Tests for turnover return yardage and red zone alerts in compact display."""

    def test_fumble_return_shows_yardage(self):
        """Fumble with return yardage should show the return distance."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False  # ATL now has ball after fumble recovery
        game.state.ball_position = 99  # ATL at CHI 1 yard line (red zone)

        # Create a fumble outcome with return yardage
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-2,
            description="FUMBLE! Defense recovers!",
            dice_roll=39,
            raw_result="F"
        )
        result.fumble_return_yards = 29  # Returned 29 yards
        result.fumble_spot = 70
        result.fumble_recovered = False

        outcome = PlayOutcome(
            play_type=PlayType.DRAW,
            defense_type=DefenseType.LONG_PASS,
            result=result,
            yards_gained=-2,
            turnover=True,
            description="FUMBLE! Defense recovers!"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.DRAW, DefenseType.LONG_PASS,
                                    home_chart, offense_was_home=True)
                output = mock_stdout.getvalue()

            # Should show return yardage
            assert "Returned 29 yds" in output, f"Expected return yardage in output: {output}"
            # Should show red zone alert (ball at 99 = goal line)
            assert "GOAL LINE" in output or "RED ZONE" in output, f"Expected red zone alert: {output}"
        finally:
            ig.COMPACT_MODE = original_compact

    def test_fumble_return_td_shows_scoop_and_score(self):
        """Fumble returned for TD should show SCOOP AND SCORE."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False
        game.state.ball_position = 97

        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-2,
            description="FUMBLE! Returned for TD!",
            dice_roll=39,
            raw_result="F"
        )
        result.fumble_return_yards = 50

        outcome = PlayOutcome(
            play_type=PlayType.DRAW,
            defense_type=DefenseType.LONG_PASS,
            result=result,
            yards_gained=-2,
            turnover=True,
            touchdown=True,
            description="FUMBLE! Returned for TD!"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.DRAW, DefenseType.LONG_PASS,
                                    home_chart, offense_was_home=True)
                output = mock_stdout.getvalue()

            assert "SCOOP AND SCORE" in output, f"Expected 'SCOOP AND SCORE' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact

    def test_interception_return_shows_yardage(self):
        """Interception with return yardage should show the return distance."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False
        game.state.ball_position = 85  # In red zone

        result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=0,
            description="INTERCEPTED!",
            dice_roll=25,
            raw_result="INT"
        )
        result.int_return_yards = 35
        result.int_return_dice = 14

        outcome = PlayOutcome(
            play_type=PlayType.LONG_PASS,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=0,
            turnover=True,
            description="INTERCEPTED!"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.LONG_PASS, DefenseType.STANDARD,
                                    home_chart, offense_was_home=True)
                output = mock_stdout.getvalue()

            assert "Returned 35 yds" in output, f"Expected return yardage in output: {output}"
            assert "RED ZONE" in output, f"Expected red zone alert: {output}"
        finally:
            ig.COMPACT_MODE = original_compact

    def test_fumble_touchback_shows_touchback(self):
        """Fumble in end zone recovered by defense should show TOUCHBACK."""
        from paydirt.interactive_game import display_play_result
        from paydirt.game_engine import PaydirtGameEngine
        import paydirt.interactive_game as ig

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        # CHI now has ball at own 20 after touchback
        game.state.is_home_possession = True
        game.state.ball_position = 20

        # Create a fumble outcome with touchback description
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,
            description="Fumble recovered by defense in end zone - TOUCHBACK",
            dice_roll=13,
            raw_result="F"
        )

        outcome = PlayOutcome(
            play_type=PlayType.SHORT_PASS,
            defense_type=DefenseType.SHORT_PASS,
            result=result,
            yards_gained=0,
            turnover=True,
            description="Fumble recovered by defense in end zone - TOUCHBACK"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.SHORT_PASS,
                                    away_chart, offense_was_home=False)
                output = mock_stdout.getvalue()

            # Should show TOUCHBACK
            assert "TOUCHBACK" in output, f"Expected 'TOUCHBACK' in output: {output}"
            assert "FUMBLE" in output, f"Expected 'FUMBLE' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact
