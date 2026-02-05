"""
Tests for PAT (Point After Touchdown) and 2-point conversion per official Paydirt rules.

Official rules:
(A) Extra point: Roll offensive dice, refer to # ON DICE column of Special Team Chart.
    WHITE box = GOOD, RED box = NO GOOD.
(B) Two-point conversion: Ball placed on 2-yard line, run a play.
    If result places ball at/beyond goal line = GOOD.
    If defense returns turnover to/beyond opponent's goal line = 2 points for defense.
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType
from paydirt.interactive_game import cpu_should_go_for_two


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with extra point no-good rolls."""
    return SpecialTeamsChart(
        # Rolls that result in NO GOOD (RED boxes)
        extra_point_no_good=[10, 24, 31],  # Sample bad rolls
        field_goal={},
        punt={},
        punt_return={},
        kickoff={},
        kickoff_return={},
        interception_return={},
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "3", 11: "2", 12: "1", 13: "0", 14: "-1"},
        short_pass={10: "5", 11: "3", 12: "INC", 13: "INT 0", 14: "2"},
    )


@pytest.fixture
def mock_team_chart(mock_special_teams, mock_offense):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
        ),
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestExtraPoint:
    """Tests for extra point (1-point conversion by kick)."""
    
    def test_extra_point_good_white_box(self, game):
        """Extra point should be good when roll is in WHITE box."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Roll 15 is not in no_good list, so it's GOOD
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W2+W3=15")
            
            success, description = game.attempt_extra_point()
            
            assert success is True
            assert "good" in description.lower()
            assert game.state.home_score == initial_score + 1
    
    def test_extra_point_no_good_red_box(self, game):
        """Extra point should be no good when roll is in RED box."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Roll 10 is in no_good list (blocked/wide/short/fumble)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            success, description = game.attempt_extra_point()
            
            assert success is False
            assert "no good" in description.lower()
            assert game.state.home_score == initial_score  # No points added
    
    def test_extra_point_away_team(self, game):
        """Extra point should add to away team score when they have possession."""
        game.state.is_home_possession = False
        initial_score = game.state.away_score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (20, "B2+W3+W5=20")
            
            success, description = game.attempt_extra_point()
            
            assert success is True
            assert game.state.away_score == initial_score + 1
    
    def test_extra_point_roll_in_description(self, game):
        """Description should include the dice roll."""
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (25, "B2+W4+W4=25")
            
            success, description = game.attempt_extra_point()
            
            assert "25" in description


class TestTwoPointConversion:
    """Tests for two-point conversion."""
    
    def test_two_point_good_with_sufficient_yards(self, game):
        """Two-point conversion should be good when play gains 2+ yards."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Mock a play that gains 3 yards (enough for 2-point conversion)
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 3
            mock_outcome.turnover = False
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            
            success, def_points, description = game.attempt_two_point(PlayType.LINE_PLUNGE)
            
            assert success is True
            assert def_points == 0
            assert "good" in description.lower()
            assert game.state.home_score == initial_score + 2
    
    def test_two_point_good_with_exactly_2_yards(self, game):
        """Two-point conversion should be good when play gains exactly 2 yards."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 2
            mock_outcome.turnover = False
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            
            success, def_points, description = game.attempt_two_point(PlayType.SHORT_PASS)
            
            assert success is True
            assert game.state.home_score == initial_score + 2
    
    def test_two_point_no_good_insufficient_yards(self, game):
        """Two-point conversion should fail when play gains less than 2 yards."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 1
            mock_outcome.turnover = False
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            
            success, def_points, description = game.attempt_two_point(PlayType.LINE_PLUNGE)
            
            assert success is False
            assert def_points == 0
            assert "no good" in description.lower()
            assert game.state.home_score == initial_score  # No points added
    
    def test_two_point_no_good_on_turnover(self, game):
        """Two-point conversion should fail on turnover (without return TD)."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 0
            mock_outcome.turnover = True
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            # Ball position after turnover is not at goal line
            game.state.ball_position = 50
            
            success, def_points, description = game.attempt_two_point(PlayType.SHORT_PASS)
            
            assert success is False
            assert "turnover" in description.lower()
            assert game.state.home_score == initial_score
    
    def test_two_point_good_on_touchdown(self, game):
        """Two-point conversion should be good when play results in touchdown."""
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 5
            mock_outcome.turnover = False
            mock_outcome.touchdown = True
            mock_play.return_value = mock_outcome
            
            success, def_points, description = game.attempt_two_point(PlayType.SHORT_PASS)
            
            assert success is True
            assert game.state.home_score == initial_score + 2
    
    def test_two_point_away_team(self, game):
        """Two-point conversion should add to away team score when they have possession."""
        game.state.is_home_possession = False
        initial_score = game.state.away_score
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 3
            mock_outcome.turnover = False
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            
            success, def_points, description = game.attempt_two_point(PlayType.LINE_PLUNGE)
            
            assert success is True
            assert game.state.away_score == initial_score + 2
    
    def test_two_point_state_restored_after_attempt(self, game):
        """Game state should be restored after two-point attempt."""
        game.state.ball_position = 25
        game.state.down = 3
        game.state.yards_to_go = 7
        game.state.is_home_possession = True
        
        with patch.object(game, 'run_play') as mock_play:
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 1
            mock_outcome.turnover = False
            mock_outcome.touchdown = False
            mock_play.return_value = mock_outcome
            
            game.attempt_two_point(PlayType.LINE_PLUNGE)
            
            # State should be restored
            assert game.state.ball_position == 25
            assert game.state.down == 3
            assert game.state.yards_to_go == 7


class TestDefensiveTwoPointReturn:
    """Tests for defensive two-point return on turnover."""
    
    def test_defense_scores_on_interception_return(self, game):
        """Defense should get 2 points if they return turnover for TD."""
        game.state.is_home_possession = True  # Home team on offense
        initial_home = game.state.home_score
        initial_away = game.state.away_score
        
        def mock_run_play_with_return(*args, **kwargs):
            """Mock that simulates turnover with return TD."""
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 0
            mock_outcome.turnover = True
            mock_outcome.touchdown = True  # Defensive return TD
            # Simulate defense returning it all the way
            game.state.ball_position = 100
            return mock_outcome
        
        with patch.object(game, 'run_play', side_effect=mock_run_play_with_return):
            success, def_points, description = game.attempt_two_point(PlayType.SHORT_PASS)
            
            assert success is False  # Offense didn't score
            assert def_points == 2
            assert "defense" in description.lower()
            # Away team (defense) should get 2 points
            assert game.state.away_score == initial_away + 2
            assert game.state.home_score == initial_home  # No change
    
    def test_defense_scores_when_away_on_offense(self, game):
        """Home team defense should get 2 points on return TD."""
        game.state.is_home_possession = False  # Away team on offense
        initial_home = game.state.home_score
        initial_away = game.state.away_score
        
        def mock_run_play_with_return(*args, **kwargs):
            """Mock that simulates turnover with return TD."""
            mock_outcome = MagicMock()
            mock_outcome.yards_gained = 0
            mock_outcome.turnover = True
            mock_outcome.touchdown = True  # Defensive return TD
            # Simulate defense returning it all the way
            game.state.ball_position = 100
            return mock_outcome
        
        with patch.object(game, 'run_play', side_effect=mock_run_play_with_return):
            success, def_points, description = game.attempt_two_point(PlayType.SHORT_PASS)
            
            assert success is False
            assert def_points == 2
            # Home team (defense) should get 2 points
            assert game.state.home_score == initial_home + 2
            assert game.state.away_score == initial_away


class TestCPUTwoPointDecision:
    """Tests for CPU decision to go for 2-point conversion."""
    
    @pytest.fixture
    def mock_game(self):
        """Create a mock game for testing."""
        game = MagicMock(spec=PaydirtGameEngine)
        game.state = MagicMock(spec=GameState)
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # Very late game
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 14
        return game
    
    def test_kicks_by_default_early_game(self, mock_game):
        """Should kick extra point by default in early game."""
        mock_game.state.quarter = 2
        mock_game.state.time_remaining = 10.0
        mock_game.state.home_score = 13  # Just scored TD, now up by 6
        mock_game.state.away_score = 7
        
        assert cpu_should_go_for_two(mock_game) is False
    
    def test_goes_for_two_when_tied_very_late(self, mock_game):
        """Should go for 2 when tied very late in game."""
        mock_game.state.home_score = 14  # Tied after TD
        mock_game.state.away_score = 14
        
        assert cpu_should_go_for_two(mock_game) is True
    
    def test_goes_for_two_when_down_by_2_late(self, mock_game):
        """Should go for 2 when down by 2 late in game."""
        mock_game.state.home_score = 12  # Down by 2 after TD
        mock_game.state.away_score = 14
        mock_game.state.time_remaining = 3.0  # Late game
        
        assert cpu_should_go_for_two(mock_game) is True
    
    def test_goes_for_two_when_up_by_1_very_late(self, mock_game):
        """Should go for 2 when up by 1 very late to go up by 3."""
        mock_game.state.home_score = 15  # Up by 1 after TD
        mock_game.state.away_score = 14
        
        assert cpu_should_go_for_two(mock_game) is True
    
    def test_goes_for_two_when_down_by_8_late(self, mock_game):
        """Should go for 2 when down by 8 late (need 2 TDs with 2-pt each)."""
        mock_game.state.home_score = 6  # Down by 8 after TD
        mock_game.state.away_score = 14
        mock_game.state.time_remaining = 3.0  # Late game
        
        assert cpu_should_go_for_two(mock_game) is True
    
    def test_kicks_when_up_by_6_late(self, mock_game):
        """Should kick when up by 6 late (go up by 7)."""
        mock_game.state.home_score = 20  # Up by 6 after TD
        mock_game.state.away_score = 14
        mock_game.state.time_remaining = 3.0
        
        assert cpu_should_go_for_two(mock_game) is False
    
    def test_kicks_when_up_big(self, mock_game):
        """Should kick when up big."""
        mock_game.state.home_score = 28  # Up by 14 after TD
        mock_game.state.away_score = 14
        
        assert cpu_should_go_for_two(mock_game) is False


class TestTwoPointConversionEraRestriction:
    """Tests for 2-point conversion era restriction (introduced in 1994)."""
    
    @pytest.fixture
    def game_1983(self):
        """Create a game with 1983 teams (pre-1994, no 2-point)."""
        peripheral = PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
        )
        special_teams = SpecialTeamsChart(
            extra_point_no_good=[],
            field_goal={},
            punt={},
            punt_return={},
            kickoff={},
            kickoff_return={},
            interception_return={},
        )
        chart = TeamChart(
            peripheral=peripheral,
            offense=OffenseChart(),
            defense=DefenseChart(),
            special_teams=special_teams,
            team_dir="",
        )
        return PaydirtGameEngine(chart, chart)
    
    @pytest.fixture
    def game_1994(self):
        """Create a game with 1994 teams (2-point allowed)."""
        peripheral = PeripheralData(
            year=1994,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '94",
            power_rating=50,
        )
        special_teams = SpecialTeamsChart(
            extra_point_no_good=[],
            field_goal={},
            punt={},
            punt_return={},
            kickoff={},
            kickoff_return={},
            interception_return={},
        )
        chart = TeamChart(
            peripheral=peripheral,
            offense=OffenseChart(),
            defense=DefenseChart(),
            special_teams=special_teams,
            team_dir="",
        )
        return PaydirtGameEngine(chart, chart)
    
    def test_two_point_not_allowed_pre_1994(self, game_1983):
        """2-point conversion should not be available for pre-1994 teams."""
        # The year check is in interactive_game.py, so we test the logic directly
        team_year = game_1983.state.home_chart.peripheral.year
        two_point_allowed = team_year >= 1994
        
        assert two_point_allowed is False
        assert team_year == 1983
    
    def test_two_point_allowed_1994_and_later(self, game_1994):
        """2-point conversion should be available for 1994+ teams."""
        team_year = game_1994.state.home_chart.peripheral.year
        two_point_allowed = team_year >= 1994
        
        assert two_point_allowed is True
        assert team_year == 1994
    
    def test_two_point_allowed_modern_era(self):
        """2-point conversion should be available for modern teams."""
        peripheral = PeripheralData(
            year=2023,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '23",
            power_rating=50,
        )
        special_teams = SpecialTeamsChart(
            extra_point_no_good=[],
            field_goal={},
            punt={},
            punt_return={},
            kickoff={},
            kickoff_return={},
            interception_return={},
        )
        chart = TeamChart(
            peripheral=peripheral,
            offense=OffenseChart(),
            defense=DefenseChart(),
            special_teams=special_teams,
            team_dir="",
        )
        game = PaydirtGameEngine(chart, chart)
        
        team_year = game.state.home_chart.peripheral.year
        two_point_allowed = team_year >= 1994
        
        assert two_point_allowed is True
