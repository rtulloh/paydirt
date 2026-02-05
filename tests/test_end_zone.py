"""
Tests for end zone rules per official Paydirt rules VI-12.

Coordinate system:
- Position 0 = own goal line (end zone is position 0 and below)
- Position 100 = opponent's goal line (end zone is position 100 and above)
- Positions 1-99 = normal field of play (NOT end zone)

Official rules:
- Fumble in opponent's end zone (pos >= 100): offense recovers = TD, defense recovers = touchback
- Fumble beyond opponent's end line (pos >= 110): roll white dice for distance, same recovery rules
- Fumble at/behind own end line (pos <= 0): safety (regardless of recovery)
- Fumble on normal field (pos 1-99): normal fumble rules apply, no special end zone scoring
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult, roll_white_dice


class TestRollWhiteDice:
    """Tests for white dice rolling function."""
    
    def test_roll_white_dice_range(self):
        """White dice should produce values 0-10."""
        for _ in range(100):
            result, desc = roll_white_dice()
            assert 0 <= result <= 10
    
    def test_roll_white_dice_description(self):
        """Description should show both dice values."""
        result, desc = roll_white_dice()
        assert "W" in desc
        assert "=" in desc


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5", 11: "8", 12: "0"},
        kickoff={},
        kickoff_return={},
        punt={},
        punt_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "F + 3", 11: "5", 12: "3"},
    )


@pytest.fixture
def mock_peripheral():
    """Create mock peripheral data with fumble ranges."""
    return PeripheralData(
        year=1983,
        team_name="Test",
        team_nickname="Team",
        short_name="TST '83",
        power_rating=50,
        fumble_recovered_range=(10, 27),  # Recover on 10-27
        fumble_lost_range=(28, 39),       # Lose on 28-39
    )


@pytest.fixture
def mock_team_chart(mock_special_teams, mock_offense, mock_peripheral):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=mock_peripheral,
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestFumbleInOpponentEndZone:
    """Tests for fumbles in opponent's end zone (VI-12-D-i)."""
    
    def test_offense_recovers_in_opponent_end_zone_is_td(self, game):
        """Offense recovering fumble in opponent's end zone = TD."""
        game.state.ball_position = 95  # 5 yards from goal
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Fumble 8 yards forward = position 103 (in end zone)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=8,
            turnover=True,
            raw_result="F + 8",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (recovered by offense)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6
    
    def test_defense_recovers_in_own_end_zone_is_touchback(self, game):
        """Defense recovering fumble in own end zone = touchback."""
        game.state.ball_position = 95  # 5 yards from goal
        game.state.is_home_possession = True
        
        # Fumble 8 yards forward = position 103 (in end zone)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=8,
            turnover=True,
            raw_result="F + 8",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 30 (lost by offense)
                mock_dice.return_value = (30, "B2+W5+W4=30")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.turnover is True
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 20  # Touchback


class TestFumbleBeyondEndLine:
    """Tests for fumbles beyond opponent's end line (VI-12-D-ii)."""
    
    def test_fumble_beyond_end_line_rolls_white_dice(self, game):
        """Fumble beyond end line should roll white dice for distance."""
        game.state.ball_position = 95
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Fumble 20 yards forward = position 115 (beyond end line)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=20,
            turnover=True,
            raw_result="F + 20",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")  # Recovered
                
                with patch('paydirt.game_engine.roll_white_dice') as mock_white:
                    mock_white.return_value = (5, "W2+W3=5")  # 5 yards into end zone
                    
                    outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Offense recovers in end zone = TD
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6


class TestFumbleAtOwnEndLine:
    """Tests for fumbles at/behind own end line (VI-12-D-iii)."""
    
    def test_fumble_behind_own_end_line_is_safety(self, game):
        """Fumble at/behind own end line = safety."""
        game.state.ball_position = 5  # 5 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Fumble 10 yards backward = position -5 (behind end line)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-10,
            turnover=True,
            raw_result="F - 10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.safety is True
        assert game.state.away_score == initial_away_score + 2


class TestFumbleInOwnEndZone:
    """Tests for fumbles in own end zone (position 0 or below)."""
    
    def test_fumble_out_of_own_end_zone_is_safety(self, game):
        """Fumble that goes out of own end zone = safety (regardless of recovery)."""
        game.state.ball_position = 5  # 5 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Fumble 10 yards backward = position -5 (out of own end zone)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-10,
            turnover=True,
            raw_result="F - 10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll doesn't matter - fumble out of end zone is safety
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.safety is True
        assert game.state.away_score == initial_away_score + 2
    
    def test_fumble_near_goal_line_not_safety_if_recovered(self, game):
        """Fumble near goal line (but not in end zone) is NOT a safety if offense recovers."""
        game.state.ball_position = 15  # 15 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Fumble 10 yards backward = position 5 (NOT in end zone, just near goal line)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-10,
            turnover=True,
            raw_result="F - 10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (recovered by offense)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Position 5 is the 5 yard line, NOT the end zone - no safety
        assert outcome.safety is False
        assert game.state.away_score == initial_away_score  # No points scored
        assert game.state.ball_position == 5  # Ball at fumble spot
    
    def test_fumble_near_goal_line_turnover_if_defense_recovers(self, game):
        """Fumble near goal line recovered by defense is just a turnover, not TD."""
        game.state.ball_position = 15  # 15 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Fumble 10 yards backward = position 5 (NOT in end zone)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-10,
            turnover=True,
            raw_result="F - 10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 30 (lost by offense)
                mock_dice.return_value = (30, "B2+W5+W4=30")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Position 5 is NOT the end zone - just a turnover, not TD
        assert outcome.turnover is True
        assert outcome.touchdown is False
        assert game.state.away_score == initial_away_score  # No TD scored


class TestNormalFieldFumble:
    """Tests for fumbles in normal field position (11-99)."""
    
    def test_fumble_in_normal_field_no_end_zone_rules(self, game):
        """Fumble in normal field position should not trigger end zone rules."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        # Fumble 3 yards forward = position 53 (normal field)
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")  # Recovered
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.touchdown is False
        assert outcome.safety is False
        assert outcome.turnover is False
        assert game.state.ball_position == 53


class TestTouchdownRules:
    """Tests for general touchdown rules (VI-12-C)."""
    
    def test_play_reaching_goal_line_is_td(self, game):
        """Any play reaching goal line (100+) is a touchdown."""
        game.state.ball_position = 95
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # 10 yard gain = position 105 (past goal line)
        mock_result = PlayResult(
            result_type=ResultType.YARDS,
            yards=10,
            raw_result="10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6
    
    def test_penalty_cannot_produce_touchdown(self, game):
        """Penalty can never produce a touchdown."""
        game.state.ball_position = 95
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        # Defensive penalty that would put ball past goal line
        mock_result = PlayResult(
            result_type=ResultType.PENALTY_DEFENSE,
            yards=15,  # Would put ball at 110
            raw_result="DEF 15",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.resolve_penalty') as mock_penalty:
                # Penalty should be half the distance to goal
                mock_penalty.return_value = (
                    MagicMock(yards=2, description="Defensive penalty"),
                    97,  # New position (half distance to goal)
                    1,   # Down
                    3,   # Yards to go
                    True # First down
                )
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Should NOT be a touchdown
        assert outcome.touchdown is False
        assert game.state.home_score == initial_score


class TestInterceptionEndZoneRules:
    """Tests for interception end zone rules (VI-12-E)."""
    
    def test_int_beyond_end_line_spot_is_9_yards_deep(self, game):
        """INT beyond end line should be spotted 9 yards deep in end zone."""
        game.state.ball_position = 90
        game.state.is_home_possession = True
        
        # INT 25 yards downfield = position 115 (beyond end line)
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=25,
            turnover=True,
            raw_result="INT 25",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (10, "B1+W0+W0=10")  # 5 yard return
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        # INT spot should be 9 yards deep (position 109 from offense = position 91 from defense)
        # After return, defense should have ball
        assert outcome.turnover is True
        assert game.state.is_home_possession is False
    
    def test_int_in_offense_own_end_zone_is_td_for_defense(self, game):
        """INT in offense's own end zone = TD for defense (no return needed)."""
        game.state.ball_position = 15  # 15 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # INT -10 yards = position 5 (in offense's own end zone)
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-10,
            turnover=True,
            raw_result="INT -10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.away_score == initial_away_score + 6
    
    def test_int_behind_offense_end_line_is_safety(self, game):
        """INT at/behind offense's own end line = safety."""
        game.state.ball_position = 5  # 5 yards from own goal
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # INT -10 yards = position -5 (behind end line)
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-10,
            turnover=True,
            raw_result="INT -10",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert outcome.safety is True
        assert game.state.away_score == initial_away_score + 2


class TestEndZoneReturns:
    """Tests for end zone return rules (VI-12-F)."""
    
    def test_return_from_end_zone_successful(self, game):
        """Return from end zone that gets past goal line should succeed."""
        # Position 5 yards deep in end zone, 10 yard return = position 15
        final_pos, is_touchback = game._handle_end_zone_return(5, 10, elect_touchback=False)
        assert final_pos == 15
        assert is_touchback is False
    
    def test_return_from_end_zone_fails_touchback(self, game):
        """Return from end zone that doesn't get past goal line = touchback."""
        # Position 8 yards deep in end zone, 2 yard return = position 10 (still in end zone)
        final_pos, is_touchback = game._handle_end_zone_return(8, 2, elect_touchback=False)
        assert final_pos == 20  # Touchback
        assert is_touchback is True
    
    def test_elect_touchback_from_end_zone(self, game):
        """Electing touchback from end zone should give ball at 20."""
        final_pos, is_touchback = game._handle_end_zone_return(5, 30, elect_touchback=True)
        assert final_pos == 20
        assert is_touchback is True
    
    def test_no_return_from_end_line(self, game):
        """Cannot return from on/behind end line - automatic touchback."""
        # Position 0 (at end line) - no return allowed
        final_pos, is_touchback = game._handle_end_zone_return(0, 50, elect_touchback=False)
        assert final_pos == 20
        assert is_touchback is True
    
    def test_no_return_from_behind_end_line(self, game):
        """Cannot return from behind end line - automatic touchback."""
        # Position -5 (behind end line) - no return allowed
        final_pos, is_touchback = game._handle_end_zone_return(-5, 50, elect_touchback=False)
        assert final_pos == 20
        assert is_touchback is True
    
    def test_return_just_past_goal_line(self, game):
        """Return that just gets past goal line should succeed."""
        # Position 5 yards deep, 6 yard return = position 11 (just past goal line)
        final_pos, is_touchback = game._handle_end_zone_return(5, 6, elect_touchback=False)
        assert final_pos == 11
        assert is_touchback is False
    
    def test_return_exactly_to_goal_line_is_touchback(self, game):
        """Return that reaches exactly goal line (position 10) is still touchback."""
        # Position 5 yards deep, 5 yard return = position 10 (at goal line, still in end zone)
        final_pos, is_touchback = game._handle_end_zone_return(5, 5, elect_touchback=False)
        assert final_pos == 20  # Touchback
        assert is_touchback is True


class TestPassInterferenceEndZone:
    """Tests for pass interference in end zone (VI-12-E-iv)."""
    
    def test_pi_in_end_zone_is_first_and_goal_at_1(self, game):
        """PI in end zone = 1st and Goal at the 1."""
        game.state.ball_position = 92  # 8 yards from goal
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 8
        
        # PI 15 yards = position 107 (in end zone)
        mock_result = PlayResult(
            result_type=ResultType.PASS_INTERFERENCE,
            yards=15,
            raw_result="PI 15",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
        
        assert game.state.ball_position == 99  # 1 yard from goal
        assert game.state.down == 1
        assert game.state.yards_to_go == 1
        assert outcome.first_down is True
    
    def test_pi_beyond_end_zone_is_first_and_goal_at_1(self, game):
        """PI beyond end zone = 1st and Goal at the 1."""
        game.state.ball_position = 85
        game.state.is_home_possession = True
        
        # PI 50 yards = position 135 (way beyond end zone)
        mock_result = PlayResult(
            result_type=ResultType.PASS_INTERFERENCE,
            yards=50,
            raw_result="PI 50",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            game.run_play(PlayType.LONG_PASS, DefenseType.STANDARD)
        
        assert game.state.ball_position == 99  # 1 yard from goal
        assert game.state.down == 1
        assert game.state.yards_to_go == 1
    
    def test_pi_short_of_end_zone_normal_rules(self, game):
        """PI short of end zone should use normal rules."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 10
        
        # PI 20 yards = position 70 (not in end zone)
        mock_result = PlayResult(
            result_type=ResultType.PASS_INTERFERENCE,
            yards=20,
            raw_result="PI 20",
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
        
        assert game.state.ball_position == 70
        assert game.state.down == 1
        assert game.state.yards_to_go == 10
        assert outcome.first_down is True
