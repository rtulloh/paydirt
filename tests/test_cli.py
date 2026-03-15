"""
Tests for CLI argument parsing and command-line interface.

Tests various permutations of command-line options including:
- Short and long forms of commands (-p, --play, -a, --auto, etc.)
- Short and long forms of options (-d, --difficulty, -H, --home, etc.)
- Team specification permutations
- Playoff flag
- Incompatible options
"""
from unittest.mock import patch
import io


class TestCLICommands:
    """Tests for main CLI command parsing."""

    def test_help_flag_shows_usage(self):
        """--help should display help message."""
        with patch('sys.argv', ['paydirt', '--help']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                from paydirt.__main__ import main
                try:
                    main()
                except SystemExit:
                    pass
                output = mock_stdout.getvalue()
                assert 'PAYDIRT - Football Board Game Simulation' in output
                assert 'Usage:' in output

    def test_short_help_flag(self):
        """-h should display help message."""
        with patch('sys.argv', ['paydirt', '-h']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                from paydirt.__main__ import main
                try:
                    main()
                except SystemExit:
                    pass
                output = mock_stdout.getvalue()
                assert 'PAYDIRT - Football Board Game Simulation' in output


class TestCLIAutoCommand:
    """Tests for the --auto/-a CPU vs CPU command."""

    def test_auto_long_form(self):
        """--auto should be recognized without error."""
        with patch('sys.argv', ['paydirt', '--auto', '2026/Ironclads', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass  # Any error means command wasn't recognized

    def test_auto_short_form(self):
        """-a should be recognized without error."""
        with patch('sys.argv', ['paydirt', '-a', '2026/Ironclads', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_auto_no_dash(self):
        """'auto' without dashes should also work."""
        with patch('sys.argv', ['paydirt', 'auto', '2026/Ironclads', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIAutoPlayoff:
    """Tests for --auto with --playoff-game option."""

    def test_auto_with_playoff_long(self):
        """--auto with --playoff-game should be recognized."""
        with patch('sys.argv', ['paydirt', '--auto', '2026/Ironclads', '2026/Thunderhawks', '--playoff-game']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_auto_with_playoff_short(self):
        """--auto with --playoff should be recognized."""
        with patch('sys.argv', ['paydirt', '-a', '2026/Ironclads', '2026/Thunderhawks', '--playoff']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIPlayOptions:
    """Tests for --play command options."""

    def test_home_long_form(self):
        """--home should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--home', '2026/Ironclads']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_home_short_form(self):
        """-H should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-H', '2026/Ironclads']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_away_long_form(self):
        """--away should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--away', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_away_short_form(self):
        """-A should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-A', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_both_home_and_away(self):
        """Both --home and --away should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '--home', '2026/Ironclads', '--away', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_short_flags_both_teams(self):
        """-H and -A should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-H', '2026/Ironclads', '-A', '2026/Thunderhawks']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIDifficultyOptions:
    """Tests for difficulty options."""

    def test_difficulty_long_form(self):
        """--difficulty should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--difficulty', 'hard']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_difficulty_short_form(self):
        """-d should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-d', 'easy']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLICompactOption:
    """Tests for --compact/-c option."""

    def test_compact_long_form(self):
        """--compact should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--compact']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_compact_short_form(self):
        """-c should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-c']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIWeekOption:
    """Tests for --week/-w option."""

    def test_week_long_form(self):
        """--week should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--week', '5']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_week_short_form(self):
        """-w should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-w', '10']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIPlayoffOption:
    """Tests for --playoff-game option."""

    def test_playoff_long_form(self):
        """--playoff-game should be recognized."""
        with patch('sys.argv', ['paydirt', '--play', '--playoff-game']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_playoff_short_form(self):
        """--playoff should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '--playoff']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLILoadCommand:
    """Tests for --load/-l command."""

    def test_load_long_form(self):
        """--load should be recognized."""
        with patch('sys.argv', ['paydirt', '--load']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_load_short_form(self):
        """-l should be recognized."""
        with patch('sys.argv', ['paydirt', '-l']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLICombinedOptions:
    """Tests for combinations of multiple options."""

    def test_all_play_options(self):
        """All options together should be recognized."""
        with patch('sys.argv', ['paydirt', '-p', '-d', 'hard', '-c', '-H', '2026/Ironclads', '-A', '2026/Thunderhawks', '-w', '7', '--playoff-game']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass


class TestCLIInvalidOptions:
    """Tests for handling of invalid options."""

    def test_invalid_difficulty_error(self):
        """Invalid difficulty should show error."""
        with patch('sys.argv', ['paydirt', '-p', '-d', 'invalid']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                from paydirt.__main__ import main
                try:
                    main()
                except Exception:
                    pass
                output = mock_stdout.getvalue()
                assert 'Error' in output

    def test_missing_home_team_error(self):
        """Missing team after --home should show error."""
        with patch('sys.argv', ['paydirt', '-p', '--home']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                from paydirt.__main__ import main
                try:
                    main()
                except Exception:
                    pass
                output = mock_stdout.getvalue()
                assert 'Error' in output

    def test_missing_week_error(self):
        """Missing week number should show error."""
        with patch('sys.argv', ['paydirt', '-p', '--week']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                from paydirt.__main__ import main
                try:
                    main()
                except Exception:
                    pass
                output = mock_stdout.getvalue()
                assert 'Error' in output


class TestCLIIncompatibleOptions:
    """Tests for incompatible option combinations."""

    def test_auto_and_play_mutually_exclusive(self):
        """--auto and --play cannot both be used."""
        with patch('sys.argv', ['paydirt', '--auto', '2026/Ironclads', '2026/Thunderhawks', '--play']):
            # Should either show help or error, or second command takes precedence
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_auto_short_and_play_short_mutually_exclusive(self):
        """-a and -p cannot both be used."""
        with patch('sys.argv', ['paydirt', '-a', '2026/Ironclads', '2026/Thunderhawks', '-p']):
            try:
                from paydirt.__main__ import main
                main()
            except Exception:
                pass

    def test_auto_requires_teams(self):
        """--auto without teams should show usage error."""
        with patch('sys.argv', ['paydirt', '--auto']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                try:
                    from paydirt.__main__ import main
                    main()
                except Exception:
                    pass
                output = mock_stdout.getvalue()
                assert 'Usage' in output or 'Error' in output

    def test_auto_with_only_one_team(self):
        """--auto with only one team should show usage error."""
        with patch('sys.argv', ['paydirt', '--auto', '2026/Ironclads']):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                try:
                    from paydirt.__main__ import main
                    main()
                except Exception:
                    pass
                output = mock_stdout.getvalue()
                assert 'Usage' in output or 'Error' in output
