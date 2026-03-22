"""
Tests for simulate_week.py.
"""
import pytest
from unittest.mock import MagicMock, patch

from paydirt.simulate_week import (
    find_team_chart_path,
    simulate_game,
    NFL_1983_WEEK_1_BALANCED,
    NFL_1972_WEEK_1,
)


class TestFindTeamChartPath:
    """Tests for find_team_chart_path()."""

    def test_exact_match(self):
        charts = [
            ("1983", "49ers", "/path/to/1983/49ers"),
            ("1983", "Bears", "/path/to/1983/Bears"),
        ]
        assert find_team_chart_path("49ers", charts) == "/path/to/1983/49ers"

    def test_case_insensitive(self):
        charts = [
            ("1983", "49ers", "/path/to/1983/49ers"),
        ]
        assert find_team_chart_path("49ERS", charts) == "/path/to/1983/49ers"
        assert find_team_chart_path("49ers", charts) == "/path/to/1983/49ers"

    def test_not_found(self):
        charts = [
            ("1983", "49ers", "/path/to/1983/49ers"),
        ]
        assert find_team_chart_path("Bears", charts) is None

    def test_empty_chart_list(self):
        assert find_team_chart_path("49ers", []) is None


class TestSimulateGame:
    """Tests for simulate_game()."""

    @pytest.fixture
    def mock_charts(self):
        home = MagicMock()
        home.peripheral.short_name = "SF '83"
        home.peripheral.full_name = "San Francisco 49ers"

        away = MagicMock()
        away.peripheral.short_name = "DAL '83"
        away.peripheral.full_name = "Dallas Cowboys"

        return home, away

    def test_simulate_game_returns_scores(self, mock_charts):
        home_chart, away_chart = mock_charts

        with patch('paydirt.simulate_week.PaydirtGameEngine') as MockGame, \
             patch('paydirt.simulate_week.ComputerAI'):

            mock_game = MagicMock()
            mock_game.season_rules.ai_behavior = None
            mock_game.state.game_over = True
            mock_game.state.home_score = 24
            mock_game.state.away_score = 17
            mock_game.state.is_home_possession = True
            MockGame.return_value = mock_game

            home_score, away_score = simulate_game(home_chart, away_chart, verbose=False)

            assert home_score == 24
            assert away_score == 17

    def test_simulate_game_creates_two_ais(self, mock_charts):
        home_chart, away_chart = mock_charts

        with patch('paydirt.simulate_week.PaydirtGameEngine') as MockGame, \
             patch('paydirt.simulate_week.ComputerAI') as MockAI:

            mock_game = MagicMock()
            mock_game.season_rules.ai_behavior = None
            mock_game.state.game_over = True
            mock_game.state.home_score = 0
            mock_game.state.away_score = 0
            mock_game.state.is_home_possession = True
            MockGame.return_value = mock_game

            simulate_game(home_chart, away_chart, verbose=False)

            assert MockAI.call_count == 2

    def test_simulate_game_calls_kickoff(self, mock_charts):
        home_chart, away_chart = mock_charts

        with patch('paydirt.simulate_week.PaydirtGameEngine') as MockGame, \
             patch('paydirt.simulate_week.ComputerAI'):

            mock_game = MagicMock()
            mock_game.season_rules.ai_behavior = None
            mock_game.state.game_over = True
            mock_game.state.home_score = 0
            mock_game.state.away_score = 0
            mock_game.state.is_home_possession = True
            MockGame.return_value = mock_game

            simulate_game(home_chart, away_chart, verbose=False)

            mock_game.kickoff.assert_called_once()

    def test_simulate_game_verbose_output(self, mock_charts, capsys):
        home_chart, away_chart = mock_charts

        with patch('paydirt.simulate_week.PaydirtGameEngine') as MockGame, \
             patch('paydirt.simulate_week.ComputerAI'):

            mock_game = MagicMock()
            mock_game.season_rules.ai_behavior = None
            mock_game.state.game_over = True
            mock_game.state.home_score = 21
            mock_game.state.away_score = 14
            mock_game.state.is_home_possession = True
            MockGame.return_value = mock_game

            simulate_game(home_chart, away_chart, verbose=True)

            captured = capsys.readouterr()
            assert "DAL '83" in captured.out or "SF '83" in captured.out


class TestSchedules:
    """Tests for the hardcoded NFL schedules."""

    def test_1983_balanced_schedule_has_14_games(self):
        assert len(NFL_1983_WEEK_1_BALANCED) == 14

    def test_1983_balanced_schedule_each_team_plays_once(self):
        teams_in_schedule = set()
        for away, home in NFL_1983_WEEK_1_BALANCED:
            teams_in_schedule.add(away)
            teams_in_schedule.add(home)
        assert len(teams_in_schedule) == 28

    def test_1972_schedule_has_13_games(self):
        assert len(NFL_1972_WEEK_1) == 13

    def test_1972_schedule_each_team_plays_once(self):
        teams_in_schedule = set()
        for away, home in NFL_1972_WEEK_1:
            teams_in_schedule.add(away)
            teams_in_schedule.add(home)
        assert len(teams_in_schedule) == 26
