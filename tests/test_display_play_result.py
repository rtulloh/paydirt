"""
Tests for display_play_result function to ensure correct team is shown on offense.

Bug fix: On 4th down failure (turnover on downs), the display was showing the wrong
team on offense because possession had already switched before display_play_result
was called.
"""
from io import StringIO
from unittest.mock import patch

import pytest

import paydirt.interactive_game as ig
from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.game_engine import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType


@pytest.fixture(autouse=True)
def reset_compact_mode():
    """Reset COMPACT_MODE to default before and after each test."""
    ig.COMPACT_MODE = False
    yield
    ig.COMPACT_MODE = False


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


class TestCompactPuntFumbleTrace:
    """Compact punt traces must show the chart result that caused a fumble."""

    def test_punt_return_fumble_shows_raw_return_cell_without_recovery_roll(self):
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

        home_chart = create_mock_chart("HOM", "Home Team")
        away_chart = create_mock_chart("AWY", "Away Team")
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            raw_result="31",
            dice_roll=19,
            punt_return_dice=11,
            punt_return_result="F",
            fumble_recovered=True,
            fumble_resolved=True,
        )
        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=result,
            description="Punt 31 yards, FUMBLE on the return! Recovered by HOM at HOM 46; 1st and 10.",
        )

        ig.COMPACT_MODE = True
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            display_play_result(
                game, outcome, PlayType.PUNT, DefenseType.STANDARD, home_chart,
                offense_was_home=True,
            )

        output = mock_stdout.getvalue()
        assert 'P:19→"31" | R:11→"F" | return' in output
        assert 'R:11→""' not in output
        assert "Ret:" not in output


class TestCompactOrdinaryFumbleTrace:
    """Compact fumble traces show only chart facts the engine actually resolved."""

    def test_defensive_recovery_shows_defensive_row_without_fake_return_roll(self):
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result
        from paydirt.play_events import EventType, PlayEvent, PlayTransaction

        home_chart = create_mock_chart("HOM", "Home Team")
        away_chart = create_mock_chart("AWY", "Away Team")
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            raw_result="F + 19",
            dice_roll=32,
            defense_modifier="",
            defense_dice="R2+G1=3",
            fumble_recovery_roll=33,
            fumble_spot=75,
            fumble_recovered=False,
            fumble_resolved=True,
        )
        transaction = PlayTransaction(is_complete=True, turnover=True, yards_gained=19)
        transaction.add_event(PlayEvent(event_type=EventType.FUMBLE, description="Fumble", spot=75))
        transaction.add_event(
            PlayEvent(event_type=EventType.FUMBLE_RECOVERY, description="Defense recovered", dice_roll=33)
        )
        outcome = PlayOutcome(
            play_type=PlayType.LINE_PLUNGE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=19,
            turnover=True,
            description="FUMBLE! Defense recovers at HOM 25.",
            transaction=transaction,
        )

        ig.COMPACT_MODE = True
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            display_play_result(
                game, outcome, PlayType.LINE_PLUNGE, DefenseType.STANDARD, away_chart,
                offense_was_home=False,
            )

        output = mock_stdout.getvalue()
        assert 'D:3→""' in output
        assert 'R:33→"lost"' in output
        assert "Ret:" not in output
    """Tests to ensure display_play_result shows the correct team on offense."""
    
    def test_offense_was_home_parameter_used_when_provided(self):
        """When offense_was_home is explicitly passed, it should be used."""
        # This tests the fix for the turnover on downs bug
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result
        
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
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result
        
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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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
        result.int_spot = 50  # INT at own 50

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
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

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


class TestFumbleReturnDiceDisplay:
    """Tests for fumble return dice roll display in technical details line.
    
    Bug fix: Fumble return was showing Ret:99 but missing the dice roll.
    Should show Ret:XX→YY format (e.g., Ret:38→99) to match INT return format.
    """
    
    def test_fumble_return_td_shows_dice_roll(self):
        """Fumble returned for TD should show the return dice roll (e.g., Ret:38→99)."""
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result
        from paydirt.play_events import EventType, PlayEvent, PlayTransaction

        home_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        # ATL recovers fumble and returns it for TD - ATL is away team
        game.state.is_home_possession = False
        game.state.ball_position = 97  # ATL at SF 1

        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-1,
            description="FUMBLE - Loss! Returned for TD!",
            dice_roll=16,
            raw_result="F"
        )
        result.fumble_return_yards = 99
        result.fumble_return_dice = 38
        result.fumble_spot = 1
        result.fumble_recovered = False

        outcome = PlayOutcome(
            play_type=PlayType.LINE_PLUNGE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=-1,
            turnover=True,
            touchdown=True,
            description="FUMBLE - Loss! RETURNED FOR TD!"
        )

        # Create transaction with fumble return event (like real game engine does)
        txn = PlayTransaction(
            events=[],
            is_complete=True,
            turnover=True,
            touchdown=True,
            yards_gained=-1,
            possession_team="ATL '83"
        )
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE,
            description="Fumble",
            yards=-1,
            spot=1,
            dice_roll=16,
            dice_desc="F",
            chart_result="F",
            acting_team="ATL '83"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RECOVERY,
            description="Defense recovered",
            yards=-1,
            dice_roll=38,
            dice_desc="lost",
            chart_result="lost",
            acting_team="ATL '83"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RETURN,
            description="Returned for TOUCHDOWN!",
            yards=99,
            dice_roll=38,
            dice_desc="38",
            chart_result="99",
            acting_team="ATL '83"
        ))
        outcome.transaction = txn

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.LINE_PLUNGE, DefenseType.STANDARD,
                                    away_chart, offense_was_home=False)
                output = mock_stdout.getvalue()

            # Should show "Ret:38→99" format (dice roll followed by yards)
            assert "Ret:38→99" in output, f"Expected 'Ret:38→99' in output: {output}"
            assert "SCOOP AND SCORE" in output, f"Expected 'SCOOP AND SCORE' in output: {output}"
            assert "FUMBLE" in output, f"Expected 'FUMBLE' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact


class TestPuntReturnFumbleDisplay:
    """Tests for punt return fumble display showing dice rolls."""
    
    def test_punt_return_fumble_shows_dice_rolls(self):
        """Punt return fumble should show both punt and return dice rolls."""
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False  # Away (ATL) is on offense
        game.state.ball_position = 30

        # Create a punt return fumble outcome
        result = PlayResult(
            result_type=ResultType.YARDS,
            yards=40,
            description="Punt 40 yards, FUMBLE on the return! Recovered at opponent's 30",
            dice_roll=17,
            raw_result="40"
        )
        result.punt_return_dice = 10  # Return dice that caused fumble

        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=40,
            turnover=False,  # Kicking team recovers
            description="Punt 40 yards, FUMBLE on the return! Recovered at opponent's 30"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.PUNT, DefenseType.STANDARD,
                                    away_chart, offense_was_home=False)
                output = mock_stdout.getvalue()

            # Should show both punt dice and return dice
            assert "P:17" in output, f"Expected 'P:17' in output: {output}"
            assert "R:10" in output, f"Expected 'R:10' in output: {output}"
            assert "FUMBLE" in output, f"Expected 'FUMBLE' in output: {output}"
            assert "recovers" in output.lower(), f"Expected 'recovers' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact
    
    def test_punt_return_fumble_no_dice_when_not_set(self):
        """Punt return fumble without return dice set should not show dice breakdown."""
        import paydirt.interactive_game as ig
        from paydirt.game_engine import PaydirtGameEngine
        from paydirt.interactive_game import display_play_result

        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = False
        game.state.ball_position = 30

        # Create a punt return fumble outcome WITHOUT punt_return_dice set
        result = PlayResult(
            result_type=ResultType.YARDS,
            yards=40,
            description="Punt 40 yards, FUMBLE on the return! Recovered at opponent's 30",
            dice_roll=17,
            raw_result="40"
        )
        # Note: punt_return_dice is NOT set

        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=40,
            turnover=False,
            description="Punt 40 yards, FUMBLE on the return! Recovered at opponent's 30"
        )

        original_compact = ig.COMPACT_MODE
        ig.COMPACT_MODE = True

        try:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                display_play_result(game, outcome, PlayType.PUNT, DefenseType.STANDARD,
                                    away_chart, offense_was_home=False)
                output = mock_stdout.getvalue()

            # Should NOT show the dice breakdown format
            assert "P:" not in output, f"Did not expect 'P:' in output: {output}"
            assert "R:" not in output, f"Did not expect 'R:' in output: {output}"
            # But should still show FUMBLE
            assert "FUMBLE" in output, f"Expected 'FUMBLE' in output: {output}"
        finally:
            ig.COMPACT_MODE = original_compact


class TestCompactDisplayInterceptionTouchback:
    """End-zone interceptions must not be presented as a gained pass or return."""

    def test_end_zone_interception_shows_touchback_not_return(self) -> None:
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("GB '83", "Green Bay Packers")
        from paydirt.game_engine import PaydirtGameEngine

        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.ball_position = 20
        result = PlayResult(
            result_type=ResultType.INTERCEPTION, yards=13, dice_roll=30,
            raw_result="INT 13", description="Interception in end zone - TOUCHBACK",
        )
        result.int_spot = 20
        result.int_return_yards = 0
        result.int_return_dice = 0
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS, defense_type=DefenseType.SHORT_PASS,
            result=result, yards_gained=0, turnover=True,
            description=result.description,
        )
        ig.COMPACT_MODE = True
        with patch("sys.stdout", new_callable=StringIO) as captured:
            ig.display_play_result(game, outcome, PlayType.MEDIUM_PASS,
                                   DefenseType.SHORT_PASS, away_chart,
                                   offense_was_home=False)
        output = captured.getvalue()
        assert "INTERCEPTED in end zone - TOUCHBACK" in output
        assert "Returned" not in output
        assert "+13" not in output
        assert 'O:30→"INT 13"' in output  # Labeled trace, not gained yardage.


class TestCompactFieldGoalDisplay:
    """Field-goal display retains original attempt metadata after a penalty decision."""

    def test_penalty_decision_miss_uses_original_attempt_distance(self) -> None:
        from paydirt.game_engine import PaydirtGameEngine

        home_chart = create_mock_chart("NO '83", "New Orleans Saints")
        away_chart = create_mock_chart("MIA '83", "Miami Dolphins")
        game = PaydirtGameEngine(home_chart, away_chart)
        result = PlayResult(
            result_type=ResultType.YARDS, yards=21, dice_roll=23,
            raw_result="21", description="Field goal NO GOOD",
        )
        outcome = PlayOutcome(
            play_type=PlayType.FIELD_GOAL, defense_type=DefenseType.STANDARD,
            result=result, field_goal_made=False, description="Field goal NO GOOD",
        )
        outcome._fg_distance_to_goal = 30
        outcome._fg_statistical_distance = 47
        ig.COMPACT_MODE = True

        with patch("sys.stdout", new_callable=StringIO) as captured:
            ig.display_play_result(
                game, outcome, PlayType.FIELD_GOAL, DefenseType.STANDARD,
                home_chart, offense_was_home=True,
            )

        output = captured.getvalue()
        assert "FG 47 yards: NO GOOD" in output
        assert "Needed: 30 yds" in output


class TestCompactPuntPenaltyTrace:
    """Compact punt output shows the complete return-penalty resolution."""

    def test_punt_penalty_includes_return_reroll_and_enforcement(self) -> None:
        from paydirt.game_engine import PaydirtGameEngine

        home_chart = create_mock_chart("NO '83", "New Orleans Saints")
        away_chart = create_mock_chart("MIA '83", "Miami Dolphins")
        game = PaydirtGameEngine(home_chart, away_chart)
        result = PlayResult(
            result_type=ResultType.YARDS, yards=44, dice_roll=16,
            raw_result="44", punt_return_dice=28,
        )
        outcome = PlayOutcome(
            play_type=PlayType.PUNT, defense_type=DefenseType.STANDARD,
            result=result,
            description="Punt 44 yards. Penalty on return: OFF 15; return reroll 28 → 60 yards; enforced 15 yards",
        )
        ig.COMPACT_MODE = True

        with patch("sys.stdout", new_callable=StringIO) as captured:
            ig.display_play_result(
                game, outcome, PlayType.PUNT, DefenseType.STANDARD,
                home_chart, offense_was_home=True,
            )

        assert 'R:28→"60"' in captured.getvalue()
        assert "enforced 15 yards" in captured.getvalue()
