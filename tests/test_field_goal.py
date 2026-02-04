"""
Tests for field goal handling per official Paydirt rules.

Official rules:
- Roll offensive dice, consult Field Goal column on kicking team's Special Team Chart
- If yardage shown EQUALS or EXCEEDS distance from LOS to goal line, FG is GOOD
- On miss, defense gets ball at their 20 OR spot of hold (7 yards back) - whichever
  is to their advantage
- Chart yardages are distance from LOS to goal line, NOT the statistical length
  (which is 17 yards greater: 10 yards end zone + 7 yards to spot of hold)
"""
import pytest
from unittest.mock import patch
from dataclasses import field

from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with various field goal results."""
    return SpecialTeamsChart(
        field_goal={
            10: "45",      # Can make up to 45 yards (62 yard statistical)
            11: "35",      # Can make up to 35 yards (52 yard statistical)
            12: "25",      # Can make up to 25 yards (42 yard statistical)
            13: "15",      # Can make up to 15 yards (32 yard statistical)
            14: "BK -8",   # Blocked kick
            15: "DEF 5",   # Defensive penalty
            16: "OFF 10",  # Offensive penalty
            17: "F - 5",   # Fumbled snap
            18: "30",      # Can make up to 30 yards
        },
        punt={},
        punt_return={},
        kickoff={},
        kickoff_return={},
        interception_return={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_team_chart(mock_special_teams):
    """Create a mock team chart."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            short_name="TST '83",
            power_rating=50,
        ),
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


@pytest.fixture
def game(mock_team_chart):
    """Create a game with mock team charts."""
    return PaydirtGameEngine(mock_team_chart, mock_team_chart)


class TestFieldGoalSuccess:
    """Tests for successful field goal attempts."""
    
    def test_fg_good_when_chart_exceeds_distance(self, game):
        """FG should be good when chart yardage exceeds distance to goal."""
        # Ball at opponent's 25 (position 75), distance to goal = 25
        game.state.ball_position = 75
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock dice roll: 10 = chart shows 45 yards, distance is 25, so GOOD
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3
    
    def test_fg_good_when_chart_equals_distance(self, game):
        """FG should be good when chart yardage equals distance to goal."""
        # Ball at opponent's 35 (position 65), distance to goal = 35
        game.state.ball_position = 65
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock dice roll: 11 = chart shows 35 yards, distance is 35, so GOOD
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3


class TestFieldGoalMiss:
    """Tests for missed field goal attempts."""
    
    def test_fg_miss_when_chart_less_than_distance(self, game):
        """FG should miss when chart yardage is less than distance to goal."""
        # Ball at opponent's 40 (position 60), distance to goal = 40
        game.state.ball_position = 60
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock dice roll: 11 = chart shows 35 yards, distance is 40, so MISS
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "no good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score  # No points
            # Possession should switch
            assert game.state.is_home_possession is False
    
    def test_fg_miss_defense_gets_ball_at_spot_when_better(self, game):
        """On miss from deep, defense should get ball at spot of hold when better than 20."""
        # Ball at own 45 (position 45), distance to goal = 55
        # Spot of hold = 45 - 7 = 38
        # Defense at spot = 100 - 38 = 62 (their 62 yard line = opponent's 38)
        # Defense at 20 = 20 (their 20 yard line)
        # 62 > 20, so spot of hold is better for defense
        game.state.ball_position = 45
        game.state.is_home_possession = True
        
        # Mock dice roll: 13 = chart shows 15 yards, distance is 55, so MISS
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W0+W3=13")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "no good" in outcome.description.lower()
            # Defense should get ball at spot of hold (62 yard line)
            assert game.state.ball_position == 62
    
    def test_fg_miss_defense_gets_ball_at_spot_of_hold(self, game):
        """On miss from close, defense should get ball at spot of hold."""
        # Ball at opponent's 15 (position 85), distance to goal = 15
        # Spot of hold = 85 - 7 = 78
        # Defense at spot = 100 - 78 = 22 (their 22)
        # Defense at 20 = 20
        # 22 is better for defense (further from their goal)
        game.state.ball_position = 85
        game.state.is_home_possession = True
        
        # Mock dice roll: 13 = chart shows 15 yards, distance is 15, so GOOD
        # Let's use a miss scenario instead
        game.state.ball_position = 80  # distance = 20
        # Spot of hold = 80 - 7 = 73
        # Defense at spot = 100 - 73 = 27
        # 27 > 20, so defense takes spot of hold
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W0+W3=13")  # 15 yards, need 20
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "no good" in outcome.description.lower()
            # Defense should get ball at spot of hold (27 yard line)
            assert game.state.ball_position == 27


class TestBlockedFieldGoal:
    """Tests for blocked field goal attempts."""
    
    def test_blocked_fg_defense_recovers(self, game):
        """Blocked FG with defense recovery roll should give ball to defense."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        
        # Mock dice rolls: FG roll = 14 (BK -8 = blocked), recovery roll = 35 (defense recovers)
        # Per rules, recovery uses fumble ranges: 10-31 = offense recovers, 32-39 = defense recovers
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W0+W4=14"), (35, "B3+W2+W0=35")]
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            # Possession should switch (defense recovers on roll 35)
            assert game.state.is_home_possession is False
    
    def test_blocked_fg_kicking_team_recovers_turnover_on_downs(self, game):
        """Blocked FG with kicking team recovery but short of line to gain = turnover on downs."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 10  # Line to gain is at 85
        
        # Mock dice rolls: FG roll = 14 (BK -8 = blocked), recovery roll = 20 (kicking team recovers)
        # Ball at 75, spot of hold = 68, block -8 = ball at 60
        # Line to gain = 75 + 10 = 85, so 60 < 85 = turnover on downs
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W0+W4=14"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            assert "turnover on downs" in outcome.description.lower()
            # Possession SHOULD switch (kicking team recovers but short of line to gain)
            assert game.state.is_home_possession is False
    
    def test_blocked_fg_safety(self, game):
        """Blocked FG in end zone should be a safety."""
        # Ball at own 5 (position 5), spot of hold = -2
        # Block -8 would put ball at -10 = safety
        game.state.ball_position = 5
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (14, "B1+W0+W4=14")  # BK -8
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            assert "safety" in outcome.description.lower()
            assert game.state.away_score == initial_away_score + 2
    
    def test_blocked_fg_on_3rd_down_kicking_team_recovers(self, game):
        """Blocked FG on 3rd down with kicking team recovery = next down, not turnover."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 10  # Line to gain is at 85
        
        # Mock dice rolls: FG roll = 14 (BK -8 = blocked), recovery roll = 20 (kicking team recovers)
        # Ball at 75, spot of hold = 68, block -8 = ball at 60
        # Line to gain = 85, recovery at 60 = short of line to gain
        # But it's 3rd down, so kicking team keeps ball and advances to 4th down
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W0+W4=14"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            assert "turnover" not in outcome.description.lower()
            # Possession should NOT switch (3rd down, kicking team recovers)
            assert game.state.is_home_possession is True
            # Should advance to 4th down
            assert game.state.down == 4
    
    def test_blocked_fg_on_1st_down_kicking_team_recovers(self, game):
        """Blocked FG on 1st down with kicking team recovery = 2nd down."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        game.state.down = 1
        game.state.yards_to_go = 10
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W0+W4=14"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            assert "turnover" not in outcome.description.lower()
            assert game.state.is_home_possession is True
            assert game.state.down == 2
    
    def test_blocked_fg_on_non_4th_down_defense_recovers(self, game):
        """Blocked FG on non-4th down with defense recovery = turnover regardless of down."""
        game.state.ball_position = 75
        game.state.is_home_possession = True
        game.state.down = 2  # 2nd down
        game.state.yards_to_go = 10
        
        # Defense recovers (roll 35 is in defense recovery range 32-39)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W0+W4=14"), (35, "B3+W2+W0=35")]
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "blocked" in outcome.description.lower()
            # Defense recovers = turnover regardless of down
            assert game.state.is_home_possession is False
            assert game.state.down == 1
            assert game.state.yards_to_go == 10


class TestFieldGoalPenalties:
    """Tests for penalties on field goal attempts."""
    
    def test_defensive_penalty_fg_good(self, game):
        """Defensive penalty on FG should result in good kick."""
        game.state.ball_position = 60  # Opponent's 40
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock dice roll: 15 = DEF 5 (defensive penalty)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (15, "B1+W0+W5=15")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3
    
    def test_offensive_penalty_fg_no_good(self, game):
        """Offensive penalty on FG should result in no good."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock dice roll: 16 = OFF 10 (offensive penalty)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (16, "B1+W0+W6=16")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "off" in outcome.description.lower()
            assert game.state.home_score == initial_home_score  # No points


class TestFieldGoalFumble:
    """Tests for fumbled snap on field goal attempts."""
    
    def test_fumbled_snap_defense_recovers(self, game):
        """Fumbled snap should give ball to defense at spot of hold."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        
        # Mock dice roll: 17 = F - 5 (fumbled snap)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B1+W0+W7=17")
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "fumble" in outcome.description.lower()
            # Possession should switch
            assert game.state.is_home_possession is False


class TestFieldGoalDistanceCalculation:
    """Tests for correct distance calculations."""
    
    def test_statistical_distance_in_description(self, game):
        """Description should show statistical distance (+ 17 yards)."""
        # Ball at opponent's 30 (position 70), distance to goal = 30
        # Statistical distance = 30 + 17 = 47 yards
        game.state.ball_position = 70
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # 45 yards, need 30
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Should mention 47 yard attempt (statistical distance)
            assert "47" in outcome.description
    
    def test_chart_distance_used_for_success(self, game):
        """Chart distance (not statistical) should determine success."""
        # Ball at opponent's 44 (position 56), distance to goal = 44
        # Statistical distance = 44 + 17 = 61 yards
        # Chart shows 45 yards, which is >= 44, so GOOD
        game.state.ball_position = 56
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")  # 45 yards
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3
