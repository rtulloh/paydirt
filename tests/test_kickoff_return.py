"""
Tests for kickoff return penalty handling.
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with kickoff return results."""
    return SpecialTeamsChart(
        kickoff={
            10: "60",   # Normal kickoff
            11: "65",   # Deep kickoff
            12: "TB",   # Touchback
        },
        kickoff_return={
            10: "20",      # Normal return
            11: "OFF 15",  # Offensive penalty on return
            12: "DEF 15",  # Defensive penalty on return
            13: "30",      # Long return
        },
        punt={},
        punt_return={},
        interception_return={},
        field_goal={},
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
            power_rating=50,
            short_name="TST '83"
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


class TestKickoffReturnPenalties:
    """Tests for penalty handling on kickoff returns."""
    
    def test_offensive_penalty_on_kickoff_return_moves_ball_back(self, game):
        """Offensive penalty on kickoff return: landing + rolled return - penalty."""
        # Set up charts for the scenario
        game.state.home_chart.special_teams.kickoff[11] = "50"
        game.state.away_chart.special_teams.kickoff[11] = "50"
        # Roll 13 gives 30 yard return (used on re-roll after penalty)
        game.state.away_chart.special_teams.kickoff_return[13] = "30"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll = 11: kickoff (50 yards) and return (OFF 15 penalty)
            # Second roll = 13: re-roll for actual return yardage (30 yards)
            mock_dice.side_effect = [(11, "B1+W0+W1=11"), (13, "B1+W2+W1=13")]
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # Re-rolled return 30 yards = 15 + 30 = 45
            # OFF 15 penalty subtracts = 45 - 15 = 30
            assert game.state.ball_position == 30
    
    def test_defensive_penalty_on_kickoff_return_moves_ball_forward(self, game):
        """Defensive penalty on kickoff return: landing + rolled return + penalty."""
        # Set up charts for the scenario
        game.state.home_chart.special_teams.kickoff[12] = "50"
        game.state.away_chart.special_teams.kickoff[12] = "50"
        # Roll 10 gives 20 yard return (used on re-roll after penalty)
        game.state.away_chart.special_teams.kickoff_return[10] = "20"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll = 12: kickoff (50 yards) and return (DEF 15 penalty)
            # Second roll = 10: re-roll for actual return yardage (20 yards)
            mock_dice.side_effect = [(12, "B1+W0+W2=12"), (10, "B1+W0+W0=10")]
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # Re-rolled return 20 yards = 15 + 20 = 35
            # DEF 15 penalty adds = 35 + 15 = 50
            assert game.state.ball_position == 50
    
    def test_offsetting_penalties_cause_rekick(self, game):
        """Offsetting penalties (OFF + DEF) should cause a rekick."""
        # Set up charts for the scenario
        game.state.home_chart.special_teams.kickoff[11] = "50"
        game.state.away_chart.special_teams.kickoff[11] = "50"
        # Roll 12 gives DEF penalty (opposite of OFF 15) - this is offsetting
        game.state.away_chart.special_teams.kickoff_return[12] = "DEF 10"
        # Roll 14 gives normal kickoff and return for the rekick
        game.state.home_chart.special_teams.kickoff[14] = "55"
        game.state.away_chart.special_teams.kickoff[14] = "55"
        game.state.away_chart.special_teams.kickoff_return[14] = "25"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll = 11: kickoff (50 yards) and return (OFF 15 penalty)
            # Second roll = 12: re-roll gets DEF 10 - offsetting (OFF + DEF)!
            # Third roll = 14: rekick - kickoff (55 yards) and return (25 yards)
            mock_dice.side_effect = [
                (11, "B1+W0+W1=11"),  # First kickoff + return (OFF 15)
                (12, "B1+W0+W2=12"),  # Re-roll gets DEF 10 - offsetting
                (14, "B1+W3+W1=14"),  # Rekick - normal result
            ]
            
            game.kickoff(kicking_home=True)
            
            # Rekick: 55 yards from 35 = lands at 10
            # Return 25 yards = 10 + 25 = 35
            assert game.state.ball_position == 35

    def test_same_penalty_twice_takes_larger_penalty(self, game):
        """Two penalties of same type (OFF + OFF) should take the larger penalty and re-roll again."""
        # Set up charts for the scenario
        game.state.home_chart.special_teams.kickoff[11] = "50"
        game.state.away_chart.special_teams.kickoff[11] = "50"
        # Roll 12 gives another OFF penalty but larger (OFF 20)
        game.state.away_chart.special_teams.kickoff_return[12] = "OFF 20"
        # Roll 13 gives actual return yardage
        game.state.away_chart.special_teams.kickoff_return[13] = "25"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll = 11: kickoff (50 yards) and return (OFF 15 penalty)
            # Second roll = 12: re-roll gets OFF 20 - same type, take larger, re-roll again
            # Third roll = 13: re-roll gets actual return yardage (25 yards)
            mock_dice.side_effect = [
                (11, "B1+W0+W1=11"),  # First kickoff + return (OFF 15)
                (12, "B1+W0+W2=12"),  # Re-roll gets OFF 20 - larger penalty
                (13, "B1+W2+W1=13"),  # Re-roll gets actual yardage (25)
            ]
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15
            # Re-rolled return 25 yards = 15 + 25 = 40
            # OFF 20 penalty (larger of 15 and 20) subtracts = 40 - 20 = 20
            assert game.state.ball_position == 20
    
    def test_same_penalty_twice_keeps_first_if_larger(self, game):
        """When first penalty is larger, it should be kept, then re-roll for yardage."""
        # Set up charts for the scenario
        game.state.home_chart.special_teams.kickoff[11] = "50"
        game.state.away_chart.special_teams.kickoff[11] = "50"
        # Roll 12 gives smaller OFF penalty (OFF 5)
        game.state.away_chart.special_teams.kickoff_return[12] = "OFF 5"
        # Roll 13 gives actual return yardage
        game.state.away_chart.special_teams.kickoff_return[13] = "25"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll = 11: kickoff (50 yards) and return (OFF 15 penalty)
            # Second roll = 12: re-roll gets OFF 5 - same type, keep larger (15), re-roll again
            # Third roll = 13: re-roll gets actual return yardage (25 yards)
            mock_dice.side_effect = [
                (11, "B1+W0+W1=11"),  # First kickoff + return (OFF 15)
                (12, "B1+W0+W2=12"),  # Re-roll gets OFF 5 - smaller
                (13, "B1+W2+W1=13"),  # Re-roll gets actual yardage (25)
            ]
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15
            # Re-rolled return 25 yards = 15 + 25 = 40
            # OFF 15 penalty (larger of 15 and 5) subtracts = 40 - 15 = 25
            assert game.state.ball_position == 25

    def test_normal_kickoff_return_still_works(self, game):
        """Normal kickoff return without penalty should work correctly."""
        # Note: Kickoff uses same dice roll for both kickoff and return charts
        # Set up charts so roll 10 gives 50 yard kickoff and 20 yard return
        game.state.home_chart.special_teams.kickoff[10] = "50"
        game.state.away_chart.special_teams.kickoff[10] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Single roll = 10 used for both kickoff (50 yards) and return (20 yards)
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.kickoff(kicking_home=True)
            
            # Kickoff 50 yards from 35 = lands at 15 (receiver's perspective)
            # landing_spot = 100 - (35 + 50) = 15
            # Return 20 yards = receiver at their 35
            # return_position = 15 + 20 = 35
            assert game.state.ball_position == 35


class TestKickoffChartPenalties:
    """Tests for penalties on the kickoff chart (pre-return)."""
    
    def test_def_penalty_on_kickoff_chart_offers_choice(self, game):
        """DEF penalty on kickoff chart should offer receiving team a choice."""
        # Set up DEF penalty on kickoff chart
        game.state.home_chart.special_teams.kickoff[10] = "DEF 5"
        game.state.home_chart.special_teams.kickoff[11] = "60"  # Re-roll result
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: kickoff chart (DEF 5), Roll 2: re-roll (60 yards)
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            outcome = game.kickoff(kicking_home=True)
            
            # Should return pending decision for receiving team
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "defense"  # Receiving team
            assert "DEF 5" in outcome.description
    
    def test_def_penalty_on_kickoff_accept_rekicks_from_closer(self, game):
        """When receiving team accepts DEF penalty, re-kick from closer spot."""
        game.state.home_chart.special_teams.kickoff[10] = "DEF 5"
        game.state.home_chart.special_teams.kickoff[11] = "60"  # Re-roll result
        game.state.home_chart.special_teams.kickoff[12] = "55"  # Re-kick result
        game.state.away_chart.special_teams.kickoff_return[12] = "20"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: kickoff chart (DEF 5), Roll 2: re-roll (60 yards)
            # Roll 3: re-kick (55 yards), uses same roll for return (20 yards)
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Initial roll - DEF 5
                (11, "B1+W0+W1=11"),  # Re-roll for yardage - 60
                (12, "B1+W0+W2=12"),  # Re-kick roll - 55 yards kickoff, 20 return
            ]
            
            outcome = game.kickoff(kicking_home=True)
            assert outcome.pending_penalty_decision is True
            
            # Accept penalty - re-kick from 30 (35 - 5)
            game.apply_kickoff_penalty_decision(outcome, accept_penalty=True)
            
            # Re-kick from 30: 55 yards = lands at 15 (100 - 30 - 55)
            # Return 20 yards = 15 + 20 = 35
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is False  # Receiving team has ball
    
    def test_def_penalty_on_kickoff_decline_takes_result(self, game):
        """When receiving team declines DEF penalty, take kickoff result."""
        game.state.home_chart.special_teams.kickoff[10] = "DEF 5"
        game.state.home_chart.special_teams.kickoff[11] = "60"  # Re-roll result
        game.state.away_chart.special_teams.kickoff_return[10] = "25"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Initial roll - DEF 5
                (11, "B1+W0+W1=11"),  # Re-roll for yardage - 60
            ]
            
            outcome = game.kickoff(kicking_home=True)
            assert outcome.pending_penalty_decision is True
            
            # Decline penalty - take kickoff result
            final_outcome = game.apply_kickoff_penalty_decision(outcome, accept_penalty=False)
            
            # Kickoff 60 yards from 35 = lands at 5 (100 - 35 - 60)
            # Return 25 yards = 5 + 25 = 30
            assert game.state.ball_position == 30
            assert "penalty declined" in final_outcome.description.lower()
    
    def test_off_penalty_on_kickoff_chart_offers_choice_to_kicking_team(self, game):
        """OFF penalty on kickoff chart should offer kicking team a choice."""
        game.state.home_chart.special_teams.kickoff[10] = "OFF 10"
        game.state.home_chart.special_teams.kickoff[11] = "55"  # Re-roll result
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            outcome = game.kickoff(kicking_home=True)
            
            # Should return pending decision for kicking team
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice.offended_team == "offense"  # Kicking team
            assert "OFF 10" in outcome.description
    
    def test_offsetting_penalties_on_kickoff_chart_rekicks(self, game):
        """Offsetting penalties on kickoff chart should cause re-kick."""
        game.state.home_chart.special_teams.kickoff[10] = "DEF 5"
        game.state.home_chart.special_teams.kickoff[11] = "OFF 10"  # Re-roll - opposite type!
        game.state.home_chart.special_teams.kickoff[12] = "55"  # Re-kick result
        game.state.away_chart.special_teams.kickoff_return[12] = "20"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Initial roll - DEF 5
                (11, "B1+W0+W1=11"),  # Re-roll - OFF 10 (offsetting!)
                (12, "B1+W0+W2=12"),  # Re-kick - normal result
            ]
            
            outcome = game.kickoff(kicking_home=True)
            
            # Offsetting penalties should auto-rekick, no pending decision
            assert outcome.pending_penalty_decision is False or outcome.pending_penalty_decision is None
            # Ball should be at normal position from re-kick
            assert game.state.is_home_possession is False


class TestKickoffDiceDisplay:
    """Tests for kickoff dice display format."""

    def test_kickoff_dice_format_in_description(self, game):
        """Kickoff description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[10] = "50"
        game.state.away_chart.special_teams.kickoff[10] = "50"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:10→" in outcome.description
            assert "| RT:10→" in outcome.description

    def test_kickoff_touchback_dice_format(self, game):
        """Kickoff touchback description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[12] = "TB"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W0+W2=12")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:12→" in outcome.description
            assert "Touchback" in outcome.description

    def test_kickoff_out_of_bounds_dice_format(self, game):
        """Kickoff out of bounds description should include dice in standard format."""
        game.state.home_chart.special_teams.kickoff[11] = "OB"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:11→\"OB\"" in outcome.description
            assert "out of bounds" in outcome.description

    def test_kickoff_negative_return_dice_format(self, game):
        """Kickoff with negative return should show negative yards in dice format."""
        game.state.home_chart.special_teams.kickoff[10] = "55"
        game.state.away_chart.special_teams.kickoff[10] = "10"
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            outcome = game.kickoff(kicking_home=True)
            
            assert "(KO:10→" in outcome.description
            assert "| RT:10→" in outcome.description

    def test_def_penalty_on_kickoff_chart_with_return_td(self, game):
        """DEF penalty on kickoff chart with return TD - TD should count, penalty to next kickoff."""
        # Both kickoff and return use the same dice roll
        game.state.home_chart.special_teams.kickoff[10] = "DEF 5"
        game.state.home_chart.special_teams.kickoff[11] = "65"  # Re-roll result - 65 yards
        # Return from same roll (10) should be TD
        game.state.away_chart.special_teams.kickoff_return[10] = "100"  # 100 yard return = TD
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Initial roll - DEF 5 on kickoff, return "100"
                (11, "B1+W0+W1=11"),  # Re-roll for yardage - 65
            ]
            
            outcome = game.kickoff(kicking_home=True)
            
            # Should have pending decision
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice.offended_team == "defense"
            
            # Decline penalty - take kickoff result
            # Kickoff 65 yards from 35 = lands at 0 (100 - 35 - 65)
            # Return 100 yards from 0 = 0 + 100 = 100 (TD)
            game.apply_kickoff_penalty_decision(outcome, accept_penalty=False)
            
            # TD was scored (ball at 99-100 depending on code)
            assert game.state.ball_position >= 99
            # Touchdown was recorded (away team scored)
            assert game.state.away_score >= 6
            # Penalty should be stored for next kickoff (THIS IS THE BUG - currently fails)
            assert game.state.pending_kickoff_penalty_yards == 5
            assert game.state.pending_kickoff_penalty_is_offense is False  # DEF penalty
