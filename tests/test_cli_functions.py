"""
Tests for cli.py module functions.

These tests cover the interactive CLI functions including:
- Screen clearing and header printing
- Scoreboard display
- Menu printing
- Play and defense selection
- Play result display
- Team selection
"""
from unittest.mock import patch, MagicMock
import io

import pytest

from paydirt.cli import (
    clear_screen,
    print_header,
    print_scoreboard,
    print_play_menu,
    print_defense_menu,
    get_play_choice,
    get_defense_choice,
    print_play_result,
    select_team,
    _ordinal,
)
from paydirt.models import PlayType, DefenseType


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
            assert 'Football Board Game Simulation' in output

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
        mock_game.get_game_status.return_value = {
            'quarter': 2,
            'time_remaining': '5:32',
            'score': {'away': {'team': 'Bears', 'score': 7}, 'home': {'team': 'Packers', 'score': 14}},
            'possession': 'Bears',
            'ball_position': 'CHI 35',
            'down': 2,
            'yards_to_go': 8
        }
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_scoreboard(mock_game)
            output = mock_stdout.getvalue()
            assert 'Q2' in output
            assert '5:32' in output

    def test_print_scoreboard_shows_scores(self):
        """Scoreboard should display both team scores."""
        mock_game = MagicMock()
        mock_game.get_game_status.return_value = {
            'quarter': 1,
            'time_remaining': '12:00',
            'score': {'away': {'team': 'Bears', 'score': 0}, 'home': {'team': 'Packers', 'score': 7}},
            'possession': 'Packers',
            'ball_position': 'GB 25',
            'down': 1,
            'yards_to_go': 10
        }
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_scoreboard(mock_game)
            output = mock_stdout.getvalue()
            assert 'Bears:' in output or 'Bears' in output
            assert 'Packers' in output
            assert '0' in output
            assert '7' in output

    def test_print_scoreboard_shows_down_and_distance(self):
        """Scoreboard should display down and yards to go."""
        mock_game = MagicMock()
        mock_game.get_game_status.return_value = {
            'quarter': 3,
            'time_remaining': '8:15',
            'score': {'away': {'team': 'Bears', 'score': 14}, 'home': {'team': 'Packers', 'score': 14}},
            'possession': 'Bears',
            'ball_position': 'CHI 40',
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
            assert 'Run Left' in output
            assert 'Run Middle' in output
            assert 'Run Right' in output
            assert 'Short Pass' in output
            assert 'Medium Pass' in output
            assert 'Long Pass' in output
            assert 'Screen Pass' in output
            assert 'Draw' in output
            assert 'Punt' in output
            assert 'Field Goal' in output

    def test_print_play_menu_has_numbers(self):
        """Menu should have numbered options."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_menu()
            output = mock_stdout.getvalue()
            assert '[1]' in output
            assert '[5]' in output
            assert '[10]' in output


class TestPrintDefenseMenu:
    """Tests for print_defense_menu function."""

    def test_print_defense_menu_shows_all_formations(self):
        """Menu should list all defensive formations."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_defense_menu()
            output = mock_stdout.getvalue()
            assert 'Normal' in output
            assert 'Prevent' in output
            assert 'Blitz' in output
            assert 'Goal Line' in output

    def test_print_defense_menu_has_numbers(self):
        """Menu should have numbered options."""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_defense_menu()
            output = mock_stdout.getvalue()
            assert '[1]' in output
            assert '[4]' in output


class TestGetPlayChoice:
    """Tests for get_play_choice function."""

    def test_get_play_choice_returns_play_type(self):
        """Valid choice should return PlayType."""
        with patch('builtins.input', return_value='1'):
            result = get_play_choice()
            assert result == PlayType.RUN_LEFT

    def test_get_play_choice_run_middle(self):
        """Choice 2 should return RUN_MIDDLE."""
        with patch('builtins.input', return_value='2'):
            result = get_play_choice()
            assert result == PlayType.RUN_MIDDLE

    def test_get_play_choice_field_goal(self):
        """Choice 10 should return FIELD_GOAL."""
        with patch('builtins.input', return_value='10'):
            result = get_play_choice()
            assert result == PlayType.FIELD_GOAL

    def test_get_play_choice_quit_returns_none(self):
        """Choice 0 should return None."""
        with patch('builtins.input', return_value='0'):
            result = get_play_choice()
            assert result is None

    def test_get_play_choice_invalid_then_valid(self):
        """Invalid choice should prompt again."""
        with patch('builtins.input', side_effect=['99', '5']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_play_choice()
                assert result == PlayType.MEDIUM_PASS


class TestGetDefenseChoice:
    """Tests for get_defense_choice function."""

    def test_get_defense_choice_returns_defense_type(self):
        """Valid choice should return DefenseType."""
        with patch('builtins.input', return_value='1'):
            result = get_defense_choice()
            assert result == DefenseType.NORMAL

    def test_get_defense_choice_blitz(self):
        """Choice 3 should return BLITZ."""
        with patch('builtins.input', return_value='3'):
            result = get_defense_choice()
            assert result == DefenseType.BLITZ

    def test_get_defense_choice_goal_line(self):
        """Choice 4 should return GOAL_LINE."""
        with patch('builtins.input', return_value='4'):
            result = get_defense_choice()
            assert result == DefenseType.GOAL_LINE

    def test_get_defense_choice_invalid_then_valid(self):
        """Invalid choice should prompt again."""
        with patch('builtins.input', side_effect=['0', '2']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_defense_choice()
                assert result == DefenseType.PREVENT


class TestPrintPlayResult:
    """Tests for print_play_result function."""

    def test_print_play_result_kickoff(self):
        """Kickoff result should display properly."""
        result = {
            'type': 'kickoff',
            'receiving_team': 'Bears',
            'return_yards': 25,
            'touchdown': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'KICKOFF' in output
            assert 'Bears' in output
            assert '25' in output

    def test_print_play_result_kickoff_touchdown(self):
        """Kickoff touchdown should display properly."""
        result = {
            'type': 'kickoff',
            'receiving_team': 'Bears',
            'return_yards': 95,
            'touchdown': True
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'TOUCHDOWN' in output

    def test_print_play_result_punt(self):
        """Punt result should display properly."""
        result = {
            'type': 'punt',
            'punt_distance': 45,
            'touchback': False,
            'ball_position_after': 'CHI 20'
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'PUNT' in output
            assert '45' in output
            assert 'CHI 20' in output

    def test_print_play_result_field_goal_good(self):
        """Successful field goal should display properly."""
        result = {
            'type': 'field_goal',
            'distance': 42,
            'success': True
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'FIELD GOAL' in output
            assert 'GOOD' in output

    def test_print_play_result_field_goal_miss(self):
        """Missed field goal should display properly."""
        result = {
            'type': 'field_goal',
            'distance': 55,
            'success': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'NO GOOD' in output

    def test_print_play_result_extra_point_good(self):
        """Successful extra point should display properly."""
        result = {
            'type': 'extra_point',
            'success': True
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'GOOD' in output

    def test_print_play_result_extra_point_missed(self):
        """Missed extra point should display properly."""
        result = {
            'type': 'extra_point',
            'success': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'MISSED' in output

    def test_print_play_result_two_point_success(self):
        """Successful two-point conversion should display properly."""
        result = {
            'type': 'two_point_conversion',
            'success': True
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'Two-point conversion' in output
            assert 'SUCCESSFUL' in output

    def test_print_play_result_two_point_failed(self):
        """Failed two-point conversion should display properly."""
        result = {
            'type': 'two_point_conversion',
            'success': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'FAILED' in output

    def test_print_play_result_regular_play_gain(self):
        """Regular play with gain should display properly."""
        result = {
            'play_type': 'run_middle',
            'dice_roll': '15',
            'description': 'Gain of 5 yards',
            'yards': 5,
            'touchdown': False,
            'turnover': False,
            'safety': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'Run Middle' in output or 'RUN MIDDLE' in output
            assert 'GAIN' in output
            assert '5' in output

    def test_print_play_result_regular_play_loss(self):
        """Regular play with loss should display properly."""
        result = {
            'play_type': 'sack',
            'dice_roll': '22',
            'description': 'Sack for loss',
            'yards': -7,
            'touchdown': False,
            'turnover': False,
            'safety': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'LOSS' in output
            assert '7' in output

    def test_print_play_result_touchdown(self):
        """Touchdown should be highlighted."""
        result = {
            'play_type': 'long_pass',
            'dice_roll': '12',
            'description': 'Complete for touchdown',
            'yards': 45,
            'touchdown': True,
            'turnover': False,
            'safety': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'TOUCHDOWN' in output

    def test_print_play_result_turnover(self):
        """Turnover should be highlighted."""
        result = {
            'play_type': 'short_pass',
            'dice_roll': '35',
            'description': 'Intercepted',
            'yards': 0,
            'touchdown': False,
            'turnover': True,
            'new_possession': 'Packers',
            'safety': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'TURNOVER' in output
            assert 'Packers' in output

    def test_print_play_result_safety(self):
        """Safety should be highlighted."""
        result = {
            'play_type': 'run_left',
            'dice_roll': '28',
            'description': 'Tackled in end zone',
            'yards': -3,
            'touchdown': False,
            'turnover': False,
            'safety': True
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'SAFETY' in output

    def test_print_play_result_with_score(self):
        """Result with score should display it."""
        result = {
            'play_type': 'run_middle',
            'dice_roll': '18',
            'description': 'Gain of 8 yards',
            'yards': 8,
            'touchdown': False,
            'turnover': False,
            'safety': False,
            'score': 'Bears 7, Packers 0'
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'Bears 7' in output or 'Score' in output


class TestSelectTeam:
    """Tests for select_team function."""

    def test_select_team_returns_team_abbr(self):
        """Should return team abbreviation for valid selection."""
        with patch('paydirt.cli.list_teams', return_value=[
            ('CHI', 'Chicago Bears', 85),
            ('GB', 'Green Bay Packers', 88),
            ('MIN', 'Minnesota Vikings', 82)
        ]):
            with patch('builtins.input', return_value='1'):
                result = select_team("Select team:")
                assert result == 'CHI'

    def test_select_team_second_option(self):
        """Should return second team when 2 is selected."""
        with patch('paydirt.cli.list_teams', return_value=[
            ('CHI', 'Chicago Bears', 85),
            ('GB', 'Green Bay Packers', 88),
            ('MIN', 'Minnesota Vikings', 82)
        ]):
            with patch('builtins.input', return_value='2'):
                result = select_team("Select team:")
                assert result == 'GB'

    def test_select_team_invalid_then_valid(self):
        """Should reprompt for invalid selection."""
        with patch('paydirt.cli.list_teams', return_value=[
            ('CHI', 'Chicago Bears', 85),
            ('GB', 'Green Bay Packers', 88)
        ]):
            with patch('builtins.input', side_effect=['99', '1']):
                with patch('sys.stdout', new_callable=io.StringIO):
                    result = select_team("Select team:")
                    assert result == 'CHI'

    def test_select_team_displays_prompt(self):
        """Should display the provided prompt."""
        with patch('paydirt.cli.list_teams', return_value=[('CHI', 'Chicago Bears', 85)]):
            with patch('builtins.input', return_value='1'):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    select_team("Choose your team:")
                    output = mock_stdout.getvalue()
                    assert 'Choose your team' in output

    def test_select_team_shows_team_info(self):
        """Should display team names and ratings."""
        with patch('paydirt.cli.list_teams', return_value=[
            ('CHI', 'Chicago Bears', 85),
            ('GB', 'Green Bay Packers', 88)
        ]):
            with patch('builtins.input', return_value='1'):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    select_team("Select:")
                    output = mock_stdout.getvalue()
                    assert 'Chicago Bears' in output
                    assert 'CHI' in output
                    assert '85' in output
                    assert 'Green Bay Packers' in output


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_play_choice_whitespace_input(self):
        """Should handle whitespace in input."""
        with patch('builtins.input', side_effect=['  5  ', '5']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_play_choice()
                assert result == PlayType.MEDIUM_PASS

    def test_get_defense_choice_whitespace_input(self):
        """Should handle whitespace in input."""
        with patch('builtins.input', side_effect=['  2  ', '2']):
            with patch('sys.stdout', new_callable=io.StringIO):
                result = get_defense_choice()
                assert result == DefenseType.PREVENT

    def test_select_team_non_numeric_input(self):
        """Should handle non-numeric input."""
        with patch('paydirt.cli.list_teams', return_value=[
            ('CHI', 'Chicago Bears', 85),
            ('GB', 'Green Bay Packers', 88)
        ]):
            with patch('builtins.input', side_effect=['abc', '1']):
                with patch('sys.stdout', new_callable=io.StringIO):
                    result = select_team("Select:")
                    assert result == 'CHI'

    def test_print_play_result_no_gain(self):
        """Play with zero yards should show no gain."""
        result = {
            'play_type': 'run_middle',
            'dice_roll': '20',
            'description': 'Stopped at line of scrimmage',
            'yards': 0,
            'touchdown': False,
            'turnover': False,
            'safety': False
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'No gain' in output

    def test_print_play_result_punt_touchback(self):
        """Punt touchback should be indicated."""
        result = {
            'type': 'punt',
            'punt_distance': 55,
            'touchback': True,
            'ball_position_after': 'Touchback'
        }
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print_play_result(result)
            output = mock_stdout.getvalue()
            assert 'Touchback' in output


class TestMainFunction:
    """Tests for main() entry point."""

    def test_main_exit_choice(self):
        """Choice 0 should exit cleanly."""
        from paydirt.cli import main
        with patch('builtins.input', return_value='0'):
            with patch('sys.stdout', new_callable=io.StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_main_invalid_choice(self):
        """Invalid choice should exit with error code."""
        from paydirt.cli import main
        with patch('builtins.input', return_value='99'):
            with patch('sys.stdout', new_callable=io.StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_main_shows_menu(self):
        """Main should display game mode menu."""
        from paydirt.cli import main
        with patch('builtins.input', return_value='0'):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with pytest.raises(SystemExit):
                    main()
                output = mock_stdout.getvalue()
                assert 'Interactive' in output or 'Simulated' in output
                assert 'Exit' in output or 'exit' in output


class TestPlaySimulatedGame:
    """Tests for play_simulated_game function."""

    def test_play_simulated_game_completes(self):
        """Simulated game should run and display results."""
        from paydirt.cli import play_simulated_game
        
        mock_team1 = MagicMock()
        mock_team1.name = 'Bears'
        mock_team2 = MagicMock()
        mock_team2.name = 'Packers'
        
        mock_game = MagicMock()
        mock_game.state.game_over = True  # End immediately
        mock_game.get_game_status.return_value = {
            'quarter': 4,
            'time_remaining': '0:00',
            'score': {'away': {'team': 'Bears', 'score': 14}, 'home': {'team': 'Packers', 'score': 7}},
            'possession': 'Bears',
            'ball_position': 'CHI 25',
            'down': 1,
            'yards_to_go': 10
        }
        mock_game.get_stats.return_value = {
            'away': {'team': 'Bears', 'total_yards': 250, 'rushing_yards': 100, 'passing_yards': 150, 'turnovers': 1},
            'home': {'team': 'Packers', 'total_yards': 200, 'rushing_yards': 80, 'passing_yards': 120, 'turnovers': 2}
        }
        
        with patch('paydirt.cli.list_teams', return_value=[('CHI', 'Bears', 85), ('GB', 'Packers', 88)]):
            with patch('paydirt.cli.get_team', side_effect=[mock_team1, mock_team2]):
                with patch('paydirt.cli.PaydirtGame', return_value=mock_game):
                    with patch('builtins.input', side_effect=['1', '2']):
                        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                            play_simulated_game()
                            output = mock_stdout.getvalue()
                            assert 'FINAL SCORE' in output
                            assert 'Bears' in output
                            assert 'Packers' in output

    def test_play_simulated_game_shows_statistics(self):
        """Simulated game should display team statistics."""
        from paydirt.cli import play_simulated_game
        
        mock_team1 = MagicMock()
        mock_team1.name = 'Bears'
        mock_team2 = MagicMock()
        mock_team2.name = 'Packers'
        
        mock_game = MagicMock()
        mock_game.state.game_over = True
        mock_game.get_game_status.return_value = {
            'quarter': 4,
            'time_remaining': '0:00',
            'score': {'away': {'team': 'Bears', 'score': 21}, 'home': {'team': 'Packers', 'score': 14}},
            'possession': 'Bears',
            'ball_position': 'CHI 25',
            'down': 1,
            'yards_to_go': 10
        }
        mock_game.get_stats.return_value = {
            'away': {'team': 'Bears', 'total_yards': 300, 'rushing_yards': 120, 'passing_yards': 180, 'turnovers': 0},
            'home': {'team': 'Packers', 'total_yards': 250, 'rushing_yards': 90, 'passing_yards': 160, 'turnovers': 1}
        }
        
        with patch('paydirt.cli.list_teams', return_value=[('CHI', 'Bears', 85), ('GB', 'Packers', 88)]):
            with patch('paydirt.cli.get_team', side_effect=[mock_team1, mock_team2]):
                with patch('paydirt.cli.PaydirtGame', return_value=mock_game):
                    with patch('builtins.input', side_effect=['1', '2']):
                        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                            play_simulated_game()
                            output = mock_stdout.getvalue()
                            assert 'Total Yards' in output or 'total_yards' in output
                            assert 'Rushing' in output or 'rushing_yards' in output
                            assert 'Passing' in output or 'passing_yards' in output
                            assert 'Turnovers' in output or 'turnovers' in output
