"""
Tests for QB Sneak play per official Paydirt rules.

Official rules:
- QB Sneak is used to gain a single yard
- Only the box COLOR matters from Play #1 (Line Plunge):
  - Green boxes (positive yardage) = 1 yard gain
  - White/Yellow boxes (zero/small/penalty) = No gain
  - Red boxes (fumble) = Fumble at line of scrimmage
- Defense doesn't participate (no defensive dice roll)
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import (
    PlayType, DefenseType, ResultType, PlayResult, 
    resolve_qb_sneak
)


@pytest.fixture
def mock_offense_chart():
    """Create mock offense chart with various Line Plunge results."""
    return OffenseChart(
        line_plunge={
            10: "5",      # Green box - positive yardage
            11: "3",      # Green box - positive yardage
            12: "-2",     # White/Yellow box - negative
            13: "0",      # White/Yellow box - zero
            14: "F + 3",  # Red box - fumble
            15: "F - 1",  # Red box - fumble
            16: "OFF 10", # White/Yellow box - penalty
            17: "B",      # Green box - breakaway
            18: "B*",     # Green box - breakaway with modifier
            19: "INT 5",  # White/Yellow box - interception (treated as no gain)
            20: "QT",     # White/Yellow box - quick throw
        },
    )


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5"},
        kickoff={},
        kickoff_return={},
        punt={},
        punt_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_team_chart(mock_offense_chart, mock_special_teams):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
            fumble_recovered_range=(10, 27),
            fumble_lost_range=(28, 39),
        ),
        offense=mock_offense_chart,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestResolveQbSneak:
    """Tests for resolve_qb_sneak function."""
    
    def test_positive_yardage_is_1_yard_gain(self, mock_offense_chart):
        """Positive yardage (green box) should result in 1 yard gain."""
        result = resolve_qb_sneak(mock_offense_chart, 10)  # "5" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 1
        assert "1 yard" in result.description
    
    def test_negative_yardage_is_no_gain(self, mock_offense_chart):
        """Negative yardage (white/yellow box) should result in no gain."""
        result = resolve_qb_sneak(mock_offense_chart, 12)  # "-2" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 0
        assert "No gain" in result.description
    
    def test_zero_yardage_is_no_gain(self, mock_offense_chart):
        """Zero yardage (white/yellow box) should result in no gain."""
        result = resolve_qb_sneak(mock_offense_chart, 13)  # "0" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 0
    
    def test_fumble_result_is_fumble_at_los(self, mock_offense_chart):
        """Fumble result (red box) should be fumble at line of scrimmage."""
        result = resolve_qb_sneak(mock_offense_chart, 14)  # "F + 3" in chart
        
        assert result.result_type == ResultType.FUMBLE
        assert result.yards == 0  # Fumble at LOS
        assert "FUMBLE" in result.description
    
    def test_fumble_minus_is_fumble(self, mock_offense_chart):
        """F - X result should also be fumble."""
        result = resolve_qb_sneak(mock_offense_chart, 15)  # "F - 1" in chart
        
        assert result.result_type == ResultType.FUMBLE
        assert result.yards == 0
    
    def test_penalty_is_no_gain(self, mock_offense_chart):
        """Penalty result (white/yellow box) should be no gain."""
        result = resolve_qb_sneak(mock_offense_chart, 16)  # "OFF 10" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 0
    
    def test_breakaway_is_1_yard_gain(self, mock_offense_chart):
        """Breakaway result (green box) should be 1 yard gain."""
        result = resolve_qb_sneak(mock_offense_chart, 17)  # "B" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 1
    
    def test_breakaway_with_modifier_is_1_yard(self, mock_offense_chart):
        """Breakaway with modifier (B*) should be 1 yard gain."""
        result = resolve_qb_sneak(mock_offense_chart, 18)  # "B*" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 1
    
    def test_interception_is_no_gain(self, mock_offense_chart):
        """Interception result should be treated as no gain (not actual INT)."""
        result = resolve_qb_sneak(mock_offense_chart, 19)  # "INT 5" in chart
        
        assert result.result_type == ResultType.YARDS
        assert result.yards == 0


class TestQbSneakGameEngine:
    """Tests for QB Sneak in game engine."""
    
    def test_qb_sneak_1_yard_gain(self, game):
        """QB Sneak with green box should gain 1 yard."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 1
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # Will get "5" = 1 yard
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.yards_gained == 1
        assert game.state.ball_position == 51
    
    def test_qb_sneak_no_gain(self, game):
        """QB Sneak with white/yellow box should gain 0 yards."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 1
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W1+W1=12")  # Will get "-2" = 0 yards
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.yards_gained == 0
        assert game.state.ball_position == 50
    
    def test_qb_sneak_first_down(self, game):
        """QB Sneak should get first down if it gains needed yard."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 1
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # 1 yard gain
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.first_down is True
        assert game.state.down == 1
    
    def test_qb_sneak_fumble_recovered(self, game):
        """QB Sneak fumble recovered by offense should result in no gain."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First call: offensive dice for play (fumble)
            # Second call: recovery roll (15 = recovered)
            mock_dice.side_effect = [
                (14, "B1+W4+W0=14"),  # "F + 3" = fumble
                (15, "B1+W5+W0=15"),  # Recovery roll in range 10-27
            ]
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.turnover is False
        assert "RECOVERED" in outcome.description
    
    def test_qb_sneak_fumble_lost(self, game):
        """QB Sneak fumble lost should result in turnover."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First call: offensive dice for play (fumble)
            # Second call: recovery roll (30 = lost)
            mock_dice.side_effect = [
                (14, "B1+W4+W0=14"),  # "F + 3" = fumble
                (30, "B2+W5+W5=30"),  # Recovery roll in range 28-39 = lost
            ]
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        assert "LOST" in outcome.description
        assert game.state.is_home_possession is False
    
    def test_qb_sneak_fumble_lost_correct_field_position(self, game):
        """QB Sneak fumble lost should place ball at correct field position for defense.
        
        This tests the fix for a bug where ball position was incorrectly flipped twice
        after switch_possession() was called.
        """
        # Ball at offense's 16-yard line (84 yards from opponent's goal)
        game.state.ball_position = 16
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [
                (14, "B1+W4+W0=14"),  # Fumble
                (30, "B2+W5+W5=30"),  # Recovery roll = lost
            ]
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        # Defense recovers at the 16-yard line from offense's perspective
        # After switch_possession(), this becomes 100 - 16 = 84 from defense's perspective
        # Defense is now at their own 84-yard line (16 yards from scoring)
        assert game.state.ball_position == 84
        assert game.state.is_home_possession is False
    
    def test_qb_sneak_touchdown(self, game):
        """QB Sneak at goal line should score touchdown."""
        game.state.ball_position = 99  # 1 yard from goal
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # 1 yard gain
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6
    
    def test_qb_sneak_updates_rushing_stats(self, game):
        """QB Sneak should update rushing stats."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_yards = game.state.offense_stats.rushing_yards
        initial_total = game.state.offense_stats.total_yards
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # 1 yard gain
            
            outcome = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        assert game.state.offense_stats.rushing_yards == initial_yards + 1
        assert game.state.offense_stats.total_yards == initial_total + 1


class TestQbSneakDefenseNotParticipating:
    """Tests to verify defense doesn't participate in QB Sneak."""
    
    def test_defense_type_ignored(self, game):
        """Defense type should be ignored for QB Sneak."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            # Try with different defense types - result should be same
            outcome1 = game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        
        game.state.ball_position = 50  # Reset
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome2 = game.run_play(PlayType.QB_SNEAK, DefenseType.BLITZ)
        
        # Both should have same result since defense doesn't participate
        assert outcome1.yards_gained == outcome2.yards_gained
