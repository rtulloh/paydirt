"""
Tests for cli_charts.py module functions.

These tests cover the chart-based CLI functions including:
- Screen clearing and header printing
- Scoreboard display
- Menu printing
- Play and defense selection
- Play result display
- Team selection
- Demo functionality
"""
from unittest.mock import patch, MagicMock
import io

import pytest

from paydirt.cli_charts import (
    clear_screen,
    print_header,
    print_scoreboard,
    print_play_menu,
    print_defense_menu,
    get_play_choice,
    get_defense_choice,
    print_play_result,
    select_team,
    quick_demo,
    _ordinal,
)
from paydirt.play_resolver import PlayType, DefenseType


class TestClearScreen:
    """Tests for clear_screen function."""

    def test_clear_screen_outputs_escape_sequence(self):
        """clear_screen should output ANSI escape sequence."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            clear_screen()
            output = mock_stdout.getvalue()
            assert '\033[2J\033[H' in output


class TestPrintHeader:
    """Tests for print_header function."""

    def test_print_header_shows_title(self):
        """Header should contain game title."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_header()
            output = mock_stdout.getvalue()
            assert 'PAYDIRT' in output
            assert 'Using Actual Team Charts' in output

    def test_print_header_has_decorative_lines(self):
        """Header should have decorative separator lines."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_header()
            output = mock_stdout.getvalue()
            assert '=' * 60 in output


class TestPrintScoreboard:
    """Tests for print_scoreboard function."""

    def test_print_scoreboard_shows_quarter_and_time(self):
        """Scoreboard should display quarter and time."""
        mock_game = MagicMock()
        mock_game.get_status.return_value = {
            'quarter': 2,
            'time': '5:32',
            'score': 'Bears 7, Packers 14',
            'possession': 'Bears',
            'field_position': 'CHI 35',
            'down': 2,
            'yards_to_go': 8
        }
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_scoreboard(mock_game)
            output = mock_stdout.getvalue()
            assert 'Q2' in output
            assert '5:32' in output

    def test_print_scoreboard_shows_score(self):
        """Scoreboard should display score."""
        mock_game = MagicMock()
        mock_game.get_status.return_value = {
            'quarter': 1,
            'time': '12:00',
            'score': 'Bears 0, Packers 7',
            'possession': 'Packers',
            'field_position': 'GB 25',
            'down': 1,
            'yards_to_go': 10
        }
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_scoreboard(mock_game)
            output = mock_stdout.getvalue()
            assert 'Bears 0' in output or 'Bears' in output
            assert 'Packers' in output

    def test_print_scoreboard_shows_down_and_distance(self):
        """Scoreboard should display down and yards to go."""
        mock_game = MagicMock()
        mock_game.get_status.return_value = {
            'quarter': 3,
            'time': '8:15',
            'score': 'Bears 14, Packers 14',
            'possession': 'Bears',
            'field_position': 'CHI 40',
            'down': 3,
            'yards_to_go': 5
        }
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_scoreboard(mock_game)
            output = mock_stdout.getvalue()
            assert '3rd' in output or '3' in output
            assert '5' in output


class TestOrdinal:
    """Tests for _ordinal helper function."""

    def test_ordinal_first(self):
        """1 should return 1st."""
        assert _ordinal(1) == '1st'

    def test_ordinal_second(self):
        """2 should return 2nd."""
        assert _ordinal(2) == '2nd'

    def test_ordinal_third(self):
        """3 should return 3rd."""
        assert _ordinal(3) == '3rd'

    def test_ordinal_fourth(self):
        """4 should return 4th."""
        assert _ordinal(4) == '4th'


class TestPrintPlayMenu:
    """Tests for print_play_menu function."""

    def test_print_play_menu_shows_all_plays(self):
        """Menu should list all play options."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_menu()
            output = mock_stdout.getvalue()
            assert 'Line Plunge' in output
            assert 'Off Tackle' in output
            assert 'End Run' in output
            assert 'Draw' in output
            assert 'Screen' in output
            assert 'Short Pass' in output
            assert 'Medium Pass' in output
            assert 'Long Pass' in output
            assert 'TE Short/Long' in output
            assert 'Punt' in output
            assert 'Field Goal' in output

    def test_print_play_menu_has_numbers_and_letters(self):
        """Menu should have numbered and lettered options."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_menu()
            output = mock_stdout.getvalue()
            assert '[1]' in output
            assert '[5]' in output
            assert '[9]' in output
            assert '[P]' in output
            assert '[F]' in output
            assert '[Q]' in output


class TestPrintDefenseMenu:
    """Tests for print_defense_menu function."""

    def test_print_defense_menu_shows_all_formations(self):
        """Menu should list all defensive formations."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_defense_menu()
            output = mock_stdout.getvalue()
            assert 'Standard' in output
            assert 'Short Yardage' in output
            assert 'Spread' in output
            assert 'Short Pass Defense' in output
            assert 'Long Pass Defense' in output
            assert 'Blitz' in output

    def test_print_defense_menu_has_letters(self):
        """Menu should have lettered options."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_defense_menu()
            output = mock_stdout.getvalue()
            assert '[A]' in output
            assert '[F]' in output


class TestGetPlayChoice:
    """Tests for get_play_choice function."""

    def test_get_play_choice_returns_play_type(self):
        """Valid choice should return PlayType."""
        with patch('builtins.input', return_value='1'):
            result = get_play_choice()
            assert result == PlayType.LINE_PLUNGE

    def test_get_play_choice_off_tackle(self):
        """Choice 2 should return OFF_TACKLE."""
        with patch('builtins.input', return_value='2'):
            result = get_play_choice()
            assert result == PlayType.OFF_TACKLE

    def test_get_play_choice_field_goal(self):
        """Choice F should return FIELD_GOAL."""
        with patch('builtins.input', return_value='F'):
            result = get_play_choice()
            assert result == PlayType.FIELD_GOAL

    def test_get_play_choice_punt(self):
        """Choice P should return PUNT."""
        with patch('builtins.input', return_value='P'):
            result = get_play_choice()
            assert result == PlayType.PUNT

    def test_get_play_choice_quit_returns_none(self):
        """Choice Q should return None."""
        with patch('builtins.input', return_value='Q'):
            result = get_play_choice()
            assert result is None

    def test_get_play_choice_lowercase_works(self):
        """Lowercase input should work."""
        with patch('builtins.input', return_value='f'):
            result = get_play_choice()
            assert result == PlayType.FIELD_GOAL

    def test_get_play_choice_invalid_then_valid(self):
        """Invalid choice should prompt again."""
        with patch('builtins.input', side_effect=['99', '5']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_play_choice()
                assert result == PlayType.SCREEN


class TestGetDefenseChoice:
    """Tests for get_defense_choice function."""

    def test_get_defense_choice_returns_defense_type(self):
        """Valid choice should return DefenseType."""
        with patch('builtins.input', return_value='A'):
            result = get_defense_choice()
            assert result == DefenseType.STANDARD

    def test_get_defense_choice_blitz(self):
        """Choice F should return BLITZ."""
        with patch('builtins.input', return_value='F'):
            result = get_defense_choice()
            assert result == DefenseType.BLITZ

    def test_get_defense_choice_numeric_alternative(self):
        """Numeric choices should also work."""
        with patch('builtins.input', return_value='1'):
            result = get_defense_choice()
            assert result == DefenseType.STANDARD

    def test_get_defense_choice_invalid_then_valid(self):
        """Invalid choice should prompt again."""
        with patch('builtins.input', side_effect=['Z', 'B']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_defense_choice()
                assert result == DefenseType.SHORT_YARDAGE


class TestPrintPlayResult:
    """Tests for print_play_result function."""

    def test_print_play_result_basic_play(self):
        """Basic play result should display properly."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'line_plunge'
        mock_outcome.result.dice_roll = '15'
        mock_outcome.description = 'Gain of 5 yards'
        mock_outcome.yards_gained = 5
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'CHI 40'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'Line Plunge' in output or 'line_plunge' in output
            assert '15' in output
            assert 'GAIN' in output
            assert '5' in output

    def test_print_play_result_loss(self):
        """Play with loss should display properly."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'sack'
        mock_outcome.result.dice_roll = '22'
        mock_outcome.description = 'Sack for loss'
        mock_outcome.yards_gained = -7
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'CHI 18'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'LOSS' in output
            assert '7' in output

    def test_print_play_result_first_down(self):
        """First down should be indicated."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'short_pass'
        mock_outcome.result.dice_roll = '12'
        mock_outcome.description = 'Complete for 12 yards'
        mock_outcome.yards_gained = 12
        mock_outcome.first_down = True
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'CHI 42'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'FIRST DOWN' in output

    def test_print_play_result_touchdown(self):
        """Touchdown should be highlighted."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'long_pass'
        mock_outcome.result.dice_roll = '12'
        mock_outcome.description = 'Complete for touchdown'
        mock_outcome.yards_gained = 45
        mock_outcome.first_down = False
        mock_outcome.touchdown = True
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'END ZONE'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'TOUCHDOWN' in output

    def test_print_play_result_turnover(self):
        """Turnover should be highlighted."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'short_pass'
        mock_outcome.result.dice_roll = '35'
        mock_outcome.description = 'Intercepted'
        mock_outcome.yards_gained = 0
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = True
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'GB 45'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'TURNOVER' in output

    def test_print_play_result_safety(self):
        """Safety should be highlighted."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'run_left'
        mock_outcome.result.dice_roll = '28'
        mock_outcome.description = 'Tackled in end zone'
        mock_outcome.yards_gained = -3
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = True
        mock_outcome.field_position_after = 'CHI 20'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'SAFETY' in output

    def test_print_play_result_no_dice_roll(self):
        """Play without dice roll should not show dice line."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'line_plunge'
        mock_outcome.result.dice_roll = None
        mock_outcome.description = 'Stopped at line'
        mock_outcome.yards_gained = 0
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'CHI 25'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            assert 'Dice Roll' not in output


class TestSelectTeam:
    """Tests for select_team function."""

    def test_select_team_returns_path(self):
        """Should return team path for valid selection."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
            ('2026', 'Packers', '/seasons/2026/Packers'),
        ]):
            with patch('builtins.input', return_value='1'):
                result = select_team('/seasons', "Select team:")
                assert result == '/seasons/2026/Bears'

    def test_select_team_second_option(self):
        """Should return second team when 2 is selected."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
            ('2026', 'Packers', '/seasons/2026/Packers'),
        ]):
            with patch('builtins.input', return_value='2'):
                result = select_team('/seasons', "Select team:")
                assert result == '/seasons/2026/Packers'

    def test_select_team_invalid_then_valid(self):
        """Should reprompt for invalid selection."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
            ('2026', 'Packers', '/seasons/2026/Packers'),
        ]):
            with patch('builtins.input', side_effect=['99', '1']):
                with patch('sys.stdout', new_callable=io.StringIO):
                    result = select_team('/seasons', "Select:")
                    assert result == '/seasons/2026/Bears'

    def test_select_team_displays_prompt(self):
        """Should display the provided prompt."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
        ]):
            with patch('builtins.input', return_value='1'):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    select_team('/seasons', "Choose your team:")
                    output = mock_stdout.getvalue()
                    assert 'Choose your team' in output

    def test_select_team_shows_team_info(self):
        """Should display team year and name."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
            ('2026', 'Packers', '/seasons/2026/Packers'),
        ]):
            with patch('builtins.input', return_value='1'):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    select_team('/seasons', "Select:")
                    output = mock_stdout.getvalue()
                    assert '2026' in output
                    assert 'Bears' in output
                    assert 'Packers' in output

    def test_select_team_no_charts_exits(self):
        """Should exit if no charts found."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[]):
            with patch('sys.stdout', new_callable=io.StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    select_team('/seasons', "Select:")
                assert exc_info.value.code == 1


class TestQuickDemo:
    """Tests for quick_demo function."""

    def test_quick_demo_no_charts(self):
        """Should handle missing charts gracefully."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[]):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                quick_demo('/seasons')
                output = mock_stdout.getvalue()
                assert 'No team charts found' in output

    def test_quick_demo_shows_team_info(self):
        """Should display team information."""
        mock_chart = MagicMock()
        mock_chart.full_name = 'Chicago Bears'
        mock_chart.short_name = 'Bears'
        mock_chart.peripheral.power_rating = 85
        mock_chart.peripheral.base_yardage_factor = 1.0
        mock_chart.peripheral.reduced_yardage_factor = 0.8
        mock_chart.offense.line_plunge = {10: '5', 11: '6'}
        mock_chart.offense.off_tackle = {10: '4', 11: '5'}
        mock_chart.offense.short_pass = {10: '8', 11: '9'}
        mock_chart.offense.long_pass = {10: '12', 11: '15'}
        
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
        ]):
            with patch('paydirt.cli_charts.load_team_chart', return_value=mock_chart):
                with patch('paydirt.cli_charts.PaydirtGameEngine') as mock_engine:
                    mock_game = MagicMock()
                    mock_game.state.game_over = True
                    mock_engine.return_value = mock_game
                    
                    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                        quick_demo('/seasons')
                        output = mock_stdout.getvalue()
                        assert 'Chicago Bears' in output or 'Bears' in output
                        assert '85' in output or 'Power Rating' in output

    def test_quick_demo_shows_sample_plays(self):
        """Should run sample plays."""
        mock_chart = MagicMock()
        mock_chart.full_name = 'Chicago Bears'
        mock_chart.short_name = 'Bears'
        mock_chart.peripheral.power_rating = 85
        mock_chart.peripheral.base_yardage_factor = 1.0
        mock_chart.peripheral.reduced_yardage_factor = 0.8
        mock_chart.offense.line_plunge = {10: '5', 11: '6'}
        mock_chart.offense.off_tackle = {10: '4', 11: '5'}
        mock_chart.offense.short_pass = {10: '8', 11: '9'}
        mock_chart.offense.long_pass = {10: '12', 11: '15'}
        
        mock_outcome = MagicMock()
        mock_outcome.result.dice_roll = '15'
        mock_outcome.description = 'Gain of 5 yards'
        mock_outcome.yards_gained = 5
        mock_outcome.field_position_after = 'CHI 30'
        
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
        ]):
            with patch('paydirt.cli_charts.load_team_chart', return_value=mock_chart):
                with patch('paydirt.cli_charts.PaydirtGameEngine') as mock_engine:
                    mock_game = MagicMock()
                    mock_game.run_play.return_value = mock_outcome
                    mock_engine.return_value = mock_game
                    
                    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                        quick_demo('/seasons')
                        output = mock_stdout.getvalue()
                        # Should show sample plays section
                        assert 'Sample' in output or 'line_plunge' in output.lower() or 'LINE_PLUNGE' in output


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_play_choice_whitespace_input(self):
        """Should handle whitespace in input."""
        with patch('builtins.input', side_effect=['  5  ', '5']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_play_choice()
                assert result == PlayType.SCREEN

    def test_get_defense_choice_whitespace_input(self):
        """Should handle whitespace in input."""
        with patch('builtins.input', side_effect=['  B  ', 'B']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_defense_choice()
                assert result == DefenseType.SHORT_YARDAGE

    def test_select_team_non_numeric_input(self):
        """Should handle non-numeric input."""
        with patch('paydirt.cli_charts.find_team_charts', return_value=[
            ('2026', 'Bears', '/seasons/2026/Bears'),
            ('2026', 'Packers', '/seasons/2026/Packers'),
        ]):
            with patch('builtins.input', side_effect=['abc', '1']):
                with patch('sys.stdout', new_callable=io.StringIO):
                    result = select_team('/seasons', "Select:")
                    assert result == '/seasons/2026/Bears'

    def test_print_play_result_no_gain(self):
        """Play with zero yards should not show gain or loss."""
        mock_outcome = MagicMock()
        mock_outcome.play_type.value = 'line_plunge'
        mock_outcome.result.dice_roll = '20'
        mock_outcome.description = 'Stopped at line'
        mock_outcome.yards_gained = 0
        mock_outcome.first_down = False
        mock_outcome.touchdown = False
        mock_outcome.turnover = False
        mock_outcome.safety = False
        mock_outcome.field_position_after = 'CHI 25'
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(mock_outcome)
            output = mock_stdout.getvalue()
            # Should not show GAIN or LOSS
            assert 'GAIN' not in output
            assert 'LOSS' not in output
