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

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType, FieldGoalResult


def create_fg_result(dice_roll: int, raw_result: str, chart_yards: int = 0,
                     is_blocked: bool = False, is_fumble: bool = False) -> FieldGoalResult:
    """Helper to create a FieldGoalResult for testing."""
    return FieldGoalResult(
        dice_roll=dice_roll,
        dice_desc=f"B1+W0+W{dice_roll-10}={dice_roll}",
        raw_result=raw_result,
        chart_yards=chart_yards,
        is_blocked=is_blocked,
        is_fumble=is_fumble,
        is_penalty=False,
        penalty_options=[],
        offsetting=False,
        offended_team="",
        reroll_log=[]
    )


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
            fumble_recovered_range=(10, 31),
            fumble_lost_range=(32, 39),
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
        
        # Mock FG result: chart shows 45 yards, distance is 25, so GOOD
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(10, "45", chart_yards=45)
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3
    
    def test_fg_good_when_chart_equals_distance(self, game):
        """FG should be good when chart yardage equals distance to goal."""
        # Ball at opponent's 35 (position 65), distance to goal = 35
        game.state.ball_position = 65
        game.state.is_home_possession = True
        initial_home_score = game.state.home_score
        
        # Mock FG result: chart shows 35 yards, distance is 35, so GOOD
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(11, "35", chart_yards=35)
            
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
        
        # Mock FG result: chart shows 35 yards, distance is 40, so MISS
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(11, "35", chart_yards=35)
            
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
        
        # Mock FG result: chart shows 15 yards, distance is 55, so MISS
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(13, "15", chart_yards=15)
            
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
        
        # Let's use a miss scenario instead
        game.state.ball_position = 80  # distance = 20
        # Spot of hold = 80 - 7 = 73
        # Defense at spot = 100 - 73 = 27
        # 27 > 20, so defense takes spot of hold
        
        # Mock FG result: chart shows 15 yards, need 20, so MISS
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(13, "15", chart_yards=15)
            
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
        
        # Mock FG result as blocked, then mock recovery roll
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 35 (defense recovers, range 32-39)
                mock_dice.return_value = (35, "B3+W2+W0=35")
                
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
        
        # Mock FG result as blocked, then mock recovery roll
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 20 (kicking team recovers, range 10-31)
                mock_dice.return_value = (20, "B2+W0+W0=20")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                assert "blocked" in outcome.description.lower()
                assert "turnover on downs" in outcome.description.lower()
                # Possession SHOULD switch (kicking team recovers but short of line to gain)
                assert game.state.is_home_possession is False
    
    def test_blocked_fg_safety_kicking_team_recovers_in_end_zone(self, game):
        """Blocked FG with kicking team recovery in end zone = safety."""
        # Ball at own 5 (position 5), spot of hold = -2
        # Block -8 would put ball at -10 = in end zone
        # Kicking team recovers in their own end zone = safety
        game.state.ball_position = 5
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 20 (kicking team recovers, range 10-31)
                mock_dice.return_value = (20, "B2+W0+W0=20")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                assert "blocked" in outcome.description.lower()
                assert "safety" in outcome.description.lower()
                assert game.state.away_score == initial_away_score + 2
    
    def test_blocked_fg_touchback_defense_recovers_in_end_zone(self, game):
        """Blocked FG with defense recovery in end zone = touchback."""
        # Ball at own 5 (position 5), spot of hold = -2
        # Block -8 would put ball at -10 = in end zone
        # Defense recovers in kicking team's end zone = touchback for defense
        game.state.ball_position = 5
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 35 (defense recovers, range 32-39)
                mock_dice.return_value = (35, "B3+W2+W0=35")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                assert "blocked" in outcome.description.lower()
                assert "touchback" in outcome.description.lower()
                # No safety scored
                assert game.state.away_score == initial_away_score
                # Defense gets ball at their 20
                assert game.state.is_home_possession is False
                assert game.state.ball_position == 20
    
    def test_blocked_fg_on_3rd_down_kicking_team_recovers(self, game):
        """Blocked FG on 3rd down with kicking team recovery = next down, not turnover."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 10  # Line to gain is at 85
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 20 (kicking team recovers, range 10-31)
                mock_dice.return_value = (20, "B2+W0+W0=20")
                
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
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll = 20 (kicking team recovers, range 10-31)
                mock_dice.return_value = (20, "B2+W0+W0=20")
                
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
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (35, "B3+W2+W0=35")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                assert "blocked" in outcome.description.lower()
                # Defense recovers = turnover regardless of down
                assert game.state.is_home_possession is False
                assert game.state.down == 1
                assert game.state.yards_to_go == 10


class TestFieldGoalPenalties:
    """Tests for penalties on field goal attempts with full penalty procedure."""
    
    def test_defensive_penalty_fg_pending_decision(self, game):
        """Defensive penalty on FG should return pending decision for offense to choose."""
        from paydirt.play_resolver import PenaltyOption
        
        game.state.ball_position = 60  # Opponent's 40
        game.state.is_home_possession = True
        
        # Mock FG result with defensive penalty - offense gets choice
        fg_result = FieldGoalResult(
            dice_roll=15,
            dice_desc="B1+W0+W5=15",
            raw_result="35",  # Final result after reroll
            chart_yards=35,
            is_blocked=False,
            is_fumble=False,
            is_penalty=True,
            penalty_options=[PenaltyOption(
                penalty_type="DEF",
                raw_result="DEF 5",
                yards=5,
                description="Defensive penalty, 5 yards"
            )],
            offsetting=False,
            offended_team="offense",
            reroll_log=["FG roll: DEF 5 (penalty)", "FG roll: 35"]
        )
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = fg_result
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Should have pending penalty decision
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "offense"
    
    def test_offensive_penalty_fg_pending_decision(self, game):
        """Offensive penalty on FG should return pending decision for defense to choose."""
        from paydirt.play_resolver import PenaltyOption
        
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        
        # Mock FG result with offensive penalty - defense gets choice
        fg_result = FieldGoalResult(
            dice_roll=16,
            dice_desc="B1+W0+W6=16",
            raw_result="45",  # Final result after reroll (would be good)
            chart_yards=45,
            is_blocked=False,
            is_fumble=False,
            is_penalty=True,
            penalty_options=[PenaltyOption(
                penalty_type="OFF",
                raw_result="OFF 10",
                yards=10,
                description="Offensive penalty, 10 yards"
            )],
            offsetting=False,
            offended_team="defense",
            reroll_log=["FG roll: OFF 10 (penalty)", "FG roll: 45"]
        )
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = fg_result
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Should have pending penalty decision
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "defense"


class TestFieldGoalFumble:
    """Tests for fumbled snap on field goal attempts."""
    
    def test_fumbled_snap_defense_recovers(self, game):
        """Fumbled snap should give ball to defense at spot of hold."""
        game.state.ball_position = 75  # Opponent's 25
        game.state.is_home_possession = True
        
        # Mock FG result as fumbled snap - uses fixture's default "F - 5"
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(17, "F - 5", is_fumble=True)
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "fumble" in outcome.description.lower()
            # Possession should switch
            assert game.state.is_home_possession is False

    def test_fumbled_snap_with_negative_yards(self, game):
        """Fumble with negative yards (e.g., 'F - 7') should calculate correct recovery spot."""
        # Ball at opponent's 27 (position 73), spot_of_hold = 73 - 7 = 66 (opponent's 34)
        # "F - 7" means fumble loses 7 yards from spot_of_hold = 66 - 7 = 59 (opponent's 41)
        # After switching possession: defense at 100 - 59 = 41 (their own 41)
        game.state.ball_position = 73  # Opponent's 27
        game.state.is_home_possession = True
        
        # Mock FG result as fumbled snap with -7 yards - use the actual result from chart lookup
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(17, "F - 7", is_fumble=True)
            # Mock the fumble recovery dice roll to be outside the return TD range (37-39)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (20, "B2+W0+W0=20")  # Not in 37-39 range
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Check the raw_result in the outcome to verify our mock is being used
            assert outcome.result.raw_result == "F - 7", f"Expected 'F - 7' but got {outcome.result.raw_result}"
            assert "fumble" in outcome.description.lower()
            # Possession should switch to away team
            assert game.state.is_home_possession is False
            # Ball should be at defense's 41 (100 - 59 = 41)
            assert game.state.ball_position == 41, f"Expected 41 but got {game.state.ball_position}"

    def test_fumbled_snap_no_return(self, game):
        """Fumble with recovery roll outside 37-39 should not return."""
        # Ball at opponent's 27 (position 73), spot_of_hold = 73 - 7 = 66
        # "F - 5" means fumble loses 5 yards from spot_of_hold = 66 - 5 = 61
        # After switching possession: defense at 100 - 61 = 39 (their own 39)
        game.state.ball_position = 73  # Opponent's 27
        game.state.is_home_possession = True
        
        # Mock FG result as fumbled snap
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(17, "F - 5", is_fumble=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll 20 (not in return range 37-39)
                mock_dice.return_value = (20, "B2+W0+W0=20")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Should not mention return TD
            assert "return td" not in outcome.description.lower()
            assert outcome.touchdown is False
            # Should have ball position at defense's 39 (100 - 61 = 39)
            assert game.state.ball_position == 39, f"Expected 39 but got {game.state.ball_position}"

    def test_fumbled_snap_uses_proper_dice_for_recovery(self, game):
        """Fumble recovery should use roll_chart_dice() not random.randint()."""
        game.state.ball_position = 50  # Own 50
        game.state.is_home_possession = True
        
        # Mock FG result as fumbled snap
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(17, "F - 5", is_fumble=True)
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # First call: recovery roll (e.g., 38 = defense gets return)
                # Second call: return roll (if applicable)
                mock_dice.side_effect = [
                    (38, "B3+W2+W1=38"),  # Recovery roll 38 (in return range 37-39)
                    (14, "B1+W4+W0=14"),  # Return roll
                ]
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                # Verify roll_chart_dice was called for recovery roll
                assert mock_dice.call_count >= 1, "roll_chart_dice should be called for fumble recovery"
                # Recovery roll was 38, which is in range 37-39, so should have return
                assert "return" in outcome.description.lower() or "td" in outcome.description.lower()


class TestFieldGoalPenaltyDecision:
    """Tests for FG penalty decision logic."""
    
    def test_fg_penalty_offense_should_take_first_down_on_miss(self, game):
        """When FG misses with defensive penalty, offense should take the penalty for first down."""
        from paydirt.play_resolver import PenaltyOption
        
        game.state.ball_position = 69  # 4th & 4 at opponent's 31
        game.state.down = 4
        game.state.yards_to_go = 4
        game.state.is_home_possession = True
        
        # Create a FG result that missed (chart shows 25, needs 31 to goal)
        fg_result = create_fg_result(12, "25", chart_yards=25)
        fg_result.penalty_options = [
            PenaltyOption(penalty_type="DEF", raw_result="DEF 15", yards=15, description="Defensive penalty, 15 yards", auto_first_down=True)
        ]
        fg_result.offended_team = "offense"
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = fg_result
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Outcome should have pending penalty decision
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            
            # The FG was NO GOOD (25 < 31)
            assert outcome.field_goal_made is False
            
            # When offense accepts penalty, they should get first down
            game.apply_fg_penalty_decision(outcome, accept_play=False, penalty_index=0)
            
            # Offense should have first down at new position
            assert game.state.down == 1
            assert game.state.yards_to_go == 10  # Fresh set of downs = 10 yards
            # Ball should have moved forward 15 yards
            assert game.state.ball_position == 84  # 69 + 15


class TestFieldGoalDistanceCalculation:
    """Tests for correct distance calculations."""
    
    def test_statistical_distance_in_description(self, game):
        """Description should show statistical distance (+ 17 yards)."""
        # Ball at opponent's 30 (position 70), distance to goal = 30
        # Statistical distance = 30 + 17 = 47 yards
        game.state.ball_position = 70
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(10, "45", chart_yards=45)
            
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
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(10, "45", chart_yards=45)
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            assert "good" in outcome.description.lower()
            assert game.state.home_score == initial_home_score + 3


class TestBlockedFieldGoalReturnTD:
    """Tests for blocked FG return touchdown handling."""
    
    def test_blocked_fg_return_td_sets_touchdown_flag(self, game):
        """Blocked FG returned for TD should set touchdown=True in outcome."""
        game.state.ball_position = 70  # Opponent's 30
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 12
        initial_away_score = game.state.away_score
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll 39 = automatic TD for defense
                mock_dice.return_value = (39, "B3+W3+W6=39")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                # Defense should score TD (6 points)
                assert game.state.away_score == initial_away_score + 6
                # Outcome should have touchdown=True
                assert outcome.touchdown is True
                assert "TD" in outcome.description or "RETURN" in outcome.description
    
    def test_blocked_fg_no_td_has_touchdown_false(self, game):
        """Blocked FG without TD should have touchdown=False in outcome."""
        game.state.ball_position = 70  # Opponent's 30
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 12
        initial_away_score = game.state.away_score
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = create_fg_result(14, "BK -8", is_blocked=True)
            
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll 35 = defense recovers but no return
                mock_dice.return_value = (35, "B3+W1+W4=35")
                
                outcome = game.run_play(PlayType.FIELD_GOAL, None)
                
                # Defense should NOT score TD
                assert game.state.away_score == initial_away_score
                # Outcome should have touchdown=False
                assert outcome.touchdown is False


class TestFGPenaltyResultDisplay:
    """Tests for FG penalty result display.
    
    Bug fix: When an offensive penalty occurs on FG and the penalty choice is displayed,
    the play_result should NOT show "Gain of X yards" for the FG chart result.
    The FG chart result (e.g., "12") represents kick distance, not yards gained.
    """
    
    def test_fg_penalty_result_has_zero_yards(self, game):
        """FG penalty result should have yards=0 to avoid 'Gain of X yards' display."""
        from paydirt.play_resolver import PenaltyOption
        
        game.state.ball_position = 59  # Kicking team's 41 yard line (41 FG)
        game.state.is_home_possession = True
        
        # Create FG result with penalty
        fg_result = FieldGoalResult(
            dice_roll=15,
            dice_desc="B1+W0+W5=15",
            raw_result="12",  # Chart result - 12 yards (FG NO GOOD)
            chart_yards=12,
            is_blocked=False,
            is_fumble=False,
            is_penalty=True,
            penalty_options=[PenaltyOption(
                penalty_type="OFF",
                raw_result="OFF 10",
                yards=10,
                description="Offensive penalty, 10 yards"
            )],
            offsetting=False,
            offended_team="defense",
            reroll_log=["FG roll: OFF 10 (penalty)", "FG roll: 15 -> 12"]
        )
        
        with patch('paydirt.game_engine.resolve_field_goal_with_penalties') as mock_fg:
            mock_fg.return_value = fg_result
            
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
            
            # Verify penalty choice was created
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            
            # Key fix: play_result should have yards=0, not 12
            # This prevents "Gain of 12 yards" from showing in the display
            assert outcome.penalty_choice.play_result.yards == 0, \
                f"Expected yards=0, got {outcome.penalty_choice.play_result.yards}"
