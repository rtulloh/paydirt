"""
Tests for punt handling per official Paydirt rules.

Official rules:
- Roll offensive dice, consult Punt column on punting team's Special Team Chart
- If result has † (downed/out of bounds) or * (fair catch), no return allowed
- Otherwise, receiving team rolls offensive dice and consults Punt Return column
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with various punt results."""
    return SpecialTeamsChart(
        punt={
            10: "40",      # Normal punt, returnable
            11: "45*",     # Fair catch
            12: "38†",     # Downed/out of bounds
            13: "BK -10",  # Blocked punt
            14: "OFF 10",  # Penalty
            15: "50",      # Long punt, returnable
            16: "65",      # Touchback punt
        },
        punt_return={
            10: "5",       # Short return
            11: "15",      # Medium return
            12: "F",       # Fumble on return
            13: "OFF 10",  # Penalty on return
            14: "25",      # Long return
            15: "0",       # No return
        },
        kickoff={},
        kickoff_return={},
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


class TestPuntBasics:
    """Basic punt functionality tests."""
    
    def test_normal_punt_allows_return(self, game):
        """Normal punt (no markers) should allow a return."""
        game.state.ball_position = 30  # Own 30
        game.state.is_home_possession = True
        
        # Mock dice rolls: punt roll = 10 (40 yards), return roll = 11 (15 yards)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 40 yards from own 30 lands at 70 (opponent's 30)
            # Return 15 yards puts ball at opponent's 45 (our 55)
            assert "returned" in outcome.description.lower() or "15" in outcome.description
    
    def test_fair_catch_no_return(self, game):
        """Punt with * (fair catch) should not allow return."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 11 (45* = fair catch)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "fair catch" in outcome.description.lower()
            # Should only have one dice roll (no return roll)
            assert mock_dice.call_count == 1
    
    def test_downed_punt_no_return(self, game):
        """Punt with † (downed/out of bounds) should not allow return."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 12 (38† = downed)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (12, "B1+W0+W2=12")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "downed" in outcome.description.lower()
            # Should only have one dice roll (no return roll)
            assert mock_dice.call_count == 1


class TestBlockedPunt:
    """Tests for blocked punt handling."""
    
    def test_blocked_punt_defense_recovers(self, game):
        """Blocked punt with defense recovery roll should give ball to defense."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock dice rolls: punt roll = 13 (BK -10 = blocked), recovery roll = 35 (defense recovers)
        # Per rules, recovery uses fumble ranges: 10-31 = offense recovers, 32-39 = defense recovers
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (35, "B3+W2+W0=35")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Possession should switch (defense recovers on roll 35)
            assert game.state.is_home_possession is False
    
    def test_blocked_punt_kicking_team_recovers_first_down(self, game):
        """Blocked punt on 4th down, kicking team recovers past first down marker."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 5  # First down marker at 35
        
        # Mock dice rolls: punt roll = 13 (BK -10 = blocked at 20), recovery roll = 20 (kicking team recovers)
        # Block at 20 is behind first down marker (35), so turnover on downs
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Kicking team recovers at 20, but first down marker was 35
            # So it's turnover on downs
            assert "turnover on downs" in outcome.description.lower()
            assert game.state.is_home_possession is False  # Possession switched
            assert game.state.down == 1

    def test_blocked_punt_kicking_team_recovers_reaches_first_down(self, game):
        """Blocked punt on 4th down, kicking team recovers at/past first down marker keeps ball."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 5  # First down marker at 35
        
        # Mock a blocked punt that lands at the 36 (past first down marker)
        # We need to mock the punt chart to return a small block
        game.state.possession_team.special_teams.punt = {13: "BK +6"}  # Block goes forward 6 yards to 36
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Kicking team recovers at 36, past first down marker (35)
            # So they keep possession with new set of downs
            assert "turnover" not in outcome.description.lower()
            assert game.state.is_home_possession is True
            assert game.state.down == 1

    def test_blocked_punt_kicking_team_recovers_not_fourth_down(self, game):
        """Blocked punt NOT on 4th down - kicking team always gets new set of downs."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.down = 1  # Not 4th down (fake punt scenario)
        game.state.yards_to_go = 10
        
        # Mock dice rolls: punt roll = 13 (BK -10 = blocked), recovery roll = 20 (kicking team recovers)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(13, "B1+W0+W3=13"), (20, "B2+W0+W0=20")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Not 4th down, so kicking team keeps ball regardless of position
            assert "turnover" not in outcome.description.lower()
            assert game.state.is_home_possession is True
            assert game.state.down == 1
    
    def test_blocked_punt_safety(self, game):
        """Blocked punt in end zone should be a safety."""
        game.state.ball_position = 5  # Own 5
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        # Mock dice roll: punt roll = 13 (BK -10 = blocked, goes into end zone)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W0+W3=13")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "blocked" in outcome.description.lower()
            # Should be a safety (2 points for away team)
            assert game.state.away_score == initial_away_score + 2
            # Outcome should have safety flag set for free kick handling
            assert outcome.safety is True
    
    def test_blocked_punt_safety_triggers_free_kick(self, game):
        """After blocked punt safety, team that gave up safety should kick."""
        game.state.ball_position = 5  # Own 5
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 13 (BK -10 = blocked, goes into end zone)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (13, "B1+W0+W3=13")
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert outcome.safety is True
            # Ball should be at 20 for free kick
            assert game.state.ball_position == 20
            # Home team (who gave up safety) should still have possession for free kick
            assert game.state.is_home_possession is True
            
            # Now execute free kick - this should switch possession
            mock_dice.return_value = (20, "B2+W0+W0=20")
            game.safety_free_kick(use_punt=False)
            
            # After free kick, possession should switch to receiving team
            assert game.state.is_home_possession is False


class TestTouchback:
    """Tests for touchback on punts."""
    
    def test_punt_into_endzone_touchback(self, game):
        """Punt into end zone should result in touchback at 20."""
        game.state.ball_position = 40  # Own 40
        game.state.is_home_possession = True
        
        # Mock dice roll: punt roll = 16 (65 yards = into end zone)
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (16, "B1+W0+W6=16")
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "touchback" in outcome.description.lower()
            # Ball should be at receiving team's 20
            assert game.state.ball_position == 20
            # Possession should switch
            assert game.state.is_home_possession is False


class TestPuntReturn:
    """Tests for punt return scenarios."""
    
    def test_return_for_touchdown(self, game):
        """Long punt return should result in touchdown."""
        game.state.ball_position = 70  # Own 70 (opponent's 30)
        game.state.is_home_possession = True
        
        # Short punt that lands close, then big return
        # Punt 15 yards lands at 85 (opponent's 15)
        # Return needs to go 85+ yards for TD
        game.state.ball_position = 30
        
        # Mock: punt 40 yards from 30 = lands at 70 (opp 30)
        # Return 80 yards = TD
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First call for punt, second for return
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W0+W4=14")]
            
            # Modify return chart to have big return
            game.state.home_chart.special_teams.punt_return[14] = "80"
            game.state.away_chart.special_teams.punt_return[14] = "80"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Should be a touchdown
            assert outcome.touchdown is True or "touchdown" in outcome.description.lower()
    
    def test_fumble_on_return(self, game):
        """Fumble on punt return should give ball back to punting team."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock: punt 40 yards, then fumble on return
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (12, "B1+W0+W2=12")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "fumble" in outcome.description.lower()
            # Punting team should retain possession
            assert game.state.is_home_possession is True
            # This is NOT a turnover - punting team recovered their own punt
            assert outcome.turnover is False
            # Should be 1st and 10 for punting team
            assert game.state.down == 1
            assert game.state.yards_to_go == 10


class TestPuntFieldPosition:
    """Tests for correct field position calculations."""
    
    def test_punt_from_own_20(self, game):
        """Punt from own 20 should land at correct spot."""
        game.state.ball_position = 20
        game.state.is_home_possession = True
        
        # Mock: punt 45 yards with fair catch
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")  # 45* fair catch
            
            game.run_play(PlayType.PUNT, None)
            
            # Punt 45 from own 20 = lands at 65 = opponent's 35
            # After possession switch, ball at 35
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is False
    
    def test_punt_with_return_field_position(self, game):
        """Punt with return should calculate correct final position."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        # Mock: punt 40 yards, return 15 yards
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11")]
            
            game.run_play(PlayType.PUNT, None)
            
            # Punt 40 from own 30 = lands at 70 = opponent's 30
            # Return 15 yards = opponent's 45 = our 55
            # After switch, receiving team at their 45
            assert game.state.ball_position == 45
            assert game.state.is_home_possession is False


class TestPuntDownAndDistance:
    """Tests for down and distance after punt."""
    
    def test_punt_resets_downs(self, game):
        """After punt, receiving team should have 1st and 10."""
        game.state.ball_position = 30
        game.state.down = 4
        game.state.yards_to_go = 15
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (11, "B1+W0+W1=11")  # Fair catch
            
            game.run_play(PlayType.PUNT, None)
            
            assert game.state.down == 1
            assert game.state.yards_to_go == 10
    
    def test_punt_fumble_recovery_resets_downs(self, game):
        """When kicking team recovers fumble on punt return, they should get 1st and 10."""
        game.state.ball_position = 9  # Deep in own territory
        game.state.down = 4
        game.state.yards_to_go = 21
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll: punt 45 yards, second roll: fumble on return
            mock_dice.side_effect = [(15, "B1+W5+W0=15"), (12, "B1+W2+W0=12")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Kicking team recovers fumble - should have 1st and 10
            assert game.state.down == 1
            assert game.state.yards_to_go == 10
            # Kicking team still has possession
            assert game.state.is_home_possession is True
            assert "FUMBLE" in outcome.description


class TestPuntReturnCommentary:
    """Tests for punt return commentary based on return yardage."""
    
    def test_long_return_commentary(self, game):
        """Long punt returns (30+ yards) should have 'What a return!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 35 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return 35 yards
            game.state.defense_team.special_teams.punt_return[14] = "35"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "What a return!" in outcome.description
    
    def test_good_return_commentary(self, game):
        """Good punt returns (20-29 yards) should have 'Great return!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 22 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return 22 yards
            game.state.defense_team.special_teams.punt_return[14] = "22"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Great return!" in outcome.description
    
    def test_no_return_coverage_commentary(self, game):
        """No return (0 yards) should have 'Excellent coverage!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return 0 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (15, "B1+W5+W0=15")]
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Excellent coverage!" in outcome.description
    
    def test_negative_return_coverage_commentary(self, game):
        """Negative return should have 'Outstanding special teams coverage!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt 40 yards, return -5 yards
            mock_dice.side_effect = [(10, "B1+W0+W0=10"), (14, "B1+W4+W0=14")]
            
            # Patch the return chart to return -5 yards
            game.state.defense_team.special_teams.punt_return[14] = "-5"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert "Outstanding special teams coverage!" in outcome.description


class TestPuntReturnPenalties:
    """Tests for penalty handling on punt returns."""
    
    def test_offensive_penalty_on_return_moves_ball_back(self, game):
        """Offensive penalty on punt return: re-roll for return, then apply penalty."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: Punt 40 yards
            # Roll 2: Return result = OFF 15 penalty
            # Roll 3: Re-roll for actual return = 10 yards
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Punt
                (13, "B1+W3+W0=13"),  # Return (OFF 15)
                (14, "B1+W4+W0=14"),  # Re-roll for return yardage
            ]
            
            # Patch the return chart
            game.state.defense_team.special_teams.punt_return[13] = "OFF 15"
            game.state.defense_team.special_teams.punt_return[14] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 40 from own 30 = lands at 70 = opponent's 30
            # Re-rolled return 10 yards = opponent's 40
            # OFF 15 penalty subtracts = opponent's 25
            assert game.state.ball_position == 25
            assert "Penalty on return" in outcome.description
    
    def test_defensive_penalty_on_return_moves_ball_forward(self, game):
        """Defensive penalty on punt return: re-roll for return, then apply penalty."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: Punt 40 yards
            # Roll 2: Return result = DEF 15 penalty
            # Roll 3: Re-roll for actual return = 10 yards
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Punt
                (13, "B1+W3+W0=13"),  # Return (DEF 15)
                (14, "B1+W4+W0=14"),  # Re-roll for return yardage
            ]
            
            # Patch the return chart
            game.state.defense_team.special_teams.punt_return[13] = "DEF 15"
            game.state.defense_team.special_teams.punt_return[14] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Punt 40 from own 30 = lands at 70 = opponent's 30
            # Re-rolled return 10 yards = opponent's 40
            # DEF 15 penalty adds = opponent's 55
            assert game.state.ball_position == 55
            assert "Penalty on return" in outcome.description


class TestPuntPenalties:
    """Tests for penalty handling on the punt itself (before the ball is kicked).
    
    Roles: Kicking team = OFFENSE, Receiving team = DEFENSE
    - OFF penalty = kicking team foul → receiving team gets choice
    - DEF penalty = receiving team foul → kicking team gets choice
    """
    
    def test_offensive_penalty_on_punt_offers_choice_to_receiving_team(self, game):
        """OFF penalty (kicking team foul) should offer receiving team a choice."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (OFF 5 penalty)
            # Roll 2: re-roll for punt yardage (40 yards)
            # Roll 3: return chart (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # OFF penalty = kicking team committed foul
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Should return pending decision for receiving team
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "defense"  # Receiving team
            assert len(outcome.penalty_choice.penalty_options) == 2
            assert "replay" in outcome.penalty_choice.penalty_options[0].description.lower()
            assert "keep" in outcome.penalty_choice.penalty_options[1].description.lower()
    
    def test_offensive_penalty_on_punt_keep_result(self, game):
        """When receiving team keeps result on OFF penalty, penalty yards are added."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (OFF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Receiving team chooses to keep result + yardage (accept_penalty=False)
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # Punt 40 yards from 30 = lands at 70 = opponent's 30
            # Return 10 yards = opponent's 40
            # OFF 5 penalty adds 5 yards = opponent's 45
            assert game.state.ball_position == 45
            assert "keeps result" in final_outcome.description.lower()
    
    def test_offensive_penalty_on_punt_replay(self, game):
        """When receiving team accepts OFF penalty, punt replayed from LOS - penalty."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (OFF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Receiving team accepts penalty (accept_penalty=True) - replay punt
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            # Penalty moves kicking team back 5 yards (30 - 5 = 25)
            # Possession should still be with kicking team (home)
            assert game.state.ball_position == 25
            assert game.state.is_home_possession is True  # Still kicking team's ball
            assert "replay" in final_outcome.description.lower()
    
    def test_defensive_penalty_on_punt_offers_choice_to_kicking_team(self, game):
        """DEF penalty (receiving team foul) should offer kicking team a choice."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # DEF penalty = receiving team committed foul (e.g., running into kicker)
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Should return pending decision for kicking team
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "offense"  # Kicking team
            assert len(outcome.penalty_choice.penalty_options) == 2
            # Options: accept (replay from better position) or decline (take punt result)
            assert "decline" in outcome.penalty_choice.penalty_options[1].description.lower()
    
    def test_defensive_penalty_on_punt_accept_no_first_down(self, game):
        """When kicking team accepts DEF penalty but doesn't get first down, still 4th down."""
        game.state.ball_position = 30
        game.state.yards_to_go = 10  # 4th and 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # DEF 5 on 4th and 10 = still 4th down (5 < 10)
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Kicking team accepts penalty (accept_penalty=True)
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            # Ball moves forward 5 yards (30 + 5 = 35)
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is True  # Still kicking team's ball
            assert game.state.down == 4  # Still 4th down
            assert game.state.yards_to_go == 5  # 10 - 5 = 5 yards to go
            assert final_outcome.first_down is False
    
    def test_defensive_penalty_on_punt_accept_gets_first_down(self, game):
        """When kicking team accepts DEF penalty and gets first down."""
        game.state.ball_position = 30
        game.state.yards_to_go = 5  # 4th and 5
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # DEF 5 on 4th and 5 = first down (5 >= 5)
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Kicking team accepts penalty (accept_penalty=True)
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            # Ball moves forward 5 yards (30 + 5 = 35), first down
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is True
            assert game.state.down == 1  # First down!
            assert final_outcome.first_down is True
    
    def test_defensive_penalty_on_punt_decline(self, game):
        """When kicking team declines DEF penalty, punt result stands."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Kicking team declines penalty (accept_penalty=False)
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # Punt 40 yards from 30 = lands at 70 = opponent's 30
            # Return 10 yards = opponent's 40 (no penalty applied)
            assert game.state.ball_position == 40
            assert game.state.is_home_possession is False  # Receiving team has ball
            assert "decline" in final_outcome.description.lower()
    
    def test_large_def_penalty_gives_first_down(self, game):
        """DEF 15 on 4th and 10 should give first down (15 >= 10)."""
        game.state.ball_position = 30
        game.state.yards_to_go = 10  # 4th and 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 15), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # DEF 15 on 4th and 10 = first down (15 >= 10)
            game.state.possession_team.special_teams.punt[14] = "DEF 15"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Kicking team accepts penalty
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            # Ball moves forward 15 yards (30 + 15 = 45), first down
            assert game.state.ball_position == 45
            assert game.state.is_home_possession is True
            assert game.state.down == 1
            assert final_outcome.first_down is True
    
    def test_def_5x_auto_first_down(self, game):
        """DEF 5X (X modifier) should give automatic first down even on 4th and 10."""
        game.state.ball_position = 30
        game.state.yards_to_go = 10  # 4th and 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5X), Roll 2: re-roll (40 yards), Roll 3: return (10 yards)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            # DEF 5X = automatic first down (X modifier)
            game.state.possession_team.special_teams.punt[14] = "DEF 5X"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            # Description should mention auto first down
            assert "auto first down" in outcome.penalty_choice.penalty_options[0].description.lower()
            
            # Kicking team accepts penalty
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            # Ball moves forward 5 yards (30 + 5 = 35), automatic first down
            assert game.state.ball_position == 35
            assert game.state.is_home_possession is True
            assert game.state.down == 1  # First down due to X modifier
            assert final_outcome.first_down is True
    
    def test_offsetting_penalties_on_punt_replay_down(self, game):
        """When punt chart penalty re-roll results in opposite penalty type, penalties offset and down is replayed."""
        game.state.ball_position = 30
        game.state.down = 4
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (OFF 5), Roll 2: re-roll (DEF 10) - offsetting!
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "DEF 10"  # Re-roll is opposite penalty type
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Offsetting penalties - down replayed, no pending decision
            assert outcome.pending_penalty_decision is False or outcome.pending_penalty_decision is None
            assert "OFFSETTING" in outcome.description
            # Ball position unchanged
            assert game.state.ball_position == 30
            # Still 4th down
            assert game.state.down == 4
    
    def test_punt_penalty_with_no_return(self, game):
        """DEF penalty on punt with no return should still offer choice to kicking team."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return (0 yards - downed)
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (12, "B1+W0+W0=12")]
            
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            # Use a downed result for the return (no return yardage)
            game.state.defense_team.special_teams.punt_return[12] = "0"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # Should return pending decision for DEF penalty (kicking team decides)
            assert outcome.pending_penalty_decision is True
            
            # Kicking team declines penalty, takes punt result
            game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # Punt 40 yards from 30 = lands at 70 = opponent's 30
            # Downed at opponent's 30 (no return, no penalty applied)
            assert game.state.ball_position == 30


class TestPuntReturnTDWithPenalty:
    """Tests for TD on punt return with penalty."""
    
    def test_punt_return_td_with_def_penalty_kicking_team_declines(self, game):
        """When punt is returned for TD with DEF penalty, kicking team can decline."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.home_score = 0
        game.state.away_score = 0
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (DEF 5), Roll 2: re-roll (40 yards), Roll 3: return for TD
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (39, "B6+W6+W6=39")]
            
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            # Large return that will result in TD
            game.state.defense_team.special_teams.punt_return[39] = "99"
            
            outcome = game._handle_punt()
            
            # Should return pending decision for kicking team
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice.offended_team == "offense"  # Kicking team
            
            # Kicking team declines penalty (accept_penalty=False), TD stands
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # TD should be scored (penalty declined, so no penalty applied)
            assert final_outcome.touchdown
            # No pending kickoff penalty since penalty was declined
            assert game.state.pending_kickoff_penalty_yards == 0
    
    def test_punt_return_td_with_off_penalty_receiving_team_keeps_result(self, game):
        """When punt is returned for TD with OFF penalty, receiving team can keep result + yardage = TD."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.home_score = 0
        game.state.away_score = 0
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: punt chart (OFF 5), Roll 2: re-roll (40 yards), Roll 3: return for TD
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (39, "B6+W6+W6=39")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"  # Re-roll result
            game.state.defense_team.special_teams.punt_return[39] = "99"
            
            outcome = game._handle_punt()
            
            # OFF penalty - receiving team gets choice
            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice.offended_team == "defense"  # Receiving team
            
            # Receiving team keeps result + yardage (accept_penalty=False) = TD
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # TD should be scored (return was already TD, plus penalty yards)
            assert final_outcome.touchdown
    
    def test_pending_def_penalty_adjusts_kickoff_spot(self, game):
        """DEF penalty during scoring play should move kickoff spot back (shorter kick)."""
        # Set up pending DEF penalty (kicking team committed penalty during scoring play)
        game.state.pending_kickoff_penalty_yards = 5
        game.state.pending_kickoff_penalty_is_offense = False  # DEF penalty
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (20, "B3+W3+W4=20")
            
            game.state.possession_team.special_teams.kickoff[20] = "60"
            game.state.defense_team.special_teams.kickoff_return[20] = "20"
            
            outcome = game.kickoff(kicking_home=True)
            
            # DEF penalty: kickoff from 30 instead of 35 (shorter kick, advantage to receiving team)
            # Kickoff 60 from 30 = lands at 90 = opponent's 10
            # Return 20 yards = opponent's 30
            assert game.state.ball_position == 30
            assert "Kickoff from 30" in outcome.description
            assert "DEF 5" in outcome.description
            # Pending penalty should be cleared
            assert game.state.pending_kickoff_penalty_yards == 0

    def test_off_penalty_on_td_return_applies_from_catch_point(self, game):
        """OFF penalty on TD return should apply from catch point, not final position."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: Punt 40 yards
            # Roll 2: Return = OFF 10 penalty
            # Roll 3: Re-roll for return = 99 (would be TD)
            mock_dice.side_effect = [
                (14, "B1+W3+W0=14"),  # Punt
                (39, "B6+W6+W6=39"),  # Return (OFF 10)
                (38, "B6+W6+W5=38"),  # Re-roll for return yardage
            ]
            
            # Punt from own 30 = 40 yards = lands at opponent's 30 (receiving_position = 30)
            game.state.possession_team.special_teams.punt[14] = "40"
            # OFF 10 penalty on return
            game.state.defense_team.special_teams.punt_return[39] = "OFF 10"
            # Re-roll gives 99 yard return (would be TD)
            game.state.defense_team.special_teams.punt_return[38] = "99"
            
            outcome = game._handle_punt()
            
            # TD negated by OFF penalty
            # Catch at 30, return 99 would be TD, but OFF 10 applies
            # Final: 30 + 99 - 10 = 119, but TD negated so capped
            assert not outcome.touchdown

    def test_half_the_distance_on_punt_return_penalty(self, game):
        """Half-the-distance rule should apply when penalty exceeds distance to goal."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 1: Punt 60 yards
            # Roll 2: Return = OFF 15 penalty
            # Roll 3: Re-roll for return = 5 yards
            mock_dice.side_effect = [
                (14, "B1+W3+W0=14"),  # Punt
                (39, "B6+W6+W6=39"),  # Return (OFF 15)
                (10, "B1+W0+W0=10"),  # Re-roll for return yardage
            ]
            
            # Punt 60 yards = lands at opponent's 10 (receiving_position = 10)
            game.state.possession_team.special_teams.punt[14] = "60"
            # OFF 15 penalty
            game.state.defense_team.special_teams.punt_return[39] = "OFF 15"
            # Re-roll gives 5 yard return
            game.state.defense_team.special_teams.punt_return[10] = "5"
            
            outcome = game._handle_punt()
            
            # Catch at 10, return 5 = 15
            # OFF 15 would move to 0, but half-the-distance applies
            # Half of 15 = 7, so 15 - 7 = 8
            assert not outcome.touchdown
            assert game.state.ball_position == 8


class TestAdvancedPuntRules:
    """Tests for advanced punt rules: Short-Drop and Coffin-Corner punts."""

    def test_short_drop_punt_removes_asterisk_markers(self, game):
        """Short-drop punt should remove * (fair catch) markers from punt result."""
        # Ball at own 3 (inside 5-yard line)
        game.state.ball_position = 3
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll that would normally result in fair catch (*)
            mock_dice.return_value = (12, "B2+W5+W5=12")
            
            # Patch punt chart to have * marker
            game.state.possession_team.special_teams.punt[12] = "35*"
            
            # Short-drop punt
            outcome = game._handle_punt(short_drop=True)
            
            # The * should be removed - fair catch should NOT apply
            assert "*" not in outcome.description
            assert "fair catch" not in outcome.description.lower()

    def test_short_drop_punt_removes_dagger_markers(self, game):
        """Short-drop punt should remove † (downed) markers from punt result."""
        game.state.ball_position = 5
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (14, "B2+W5+W7=14")
            
            # Patch punt chart to have † marker
            game.state.possession_team.special_teams.punt[14] = "40†"
            
            outcome = game._handle_punt(short_drop=True)
            
            # The † should be removed - downed should NOT apply
            assert "†" not in outcome.description

    def test_short_drop_punt_minus_returns_become_zero(self, game):
        """Short-drop punt: minus return yardage should become 0 yards."""
        game.state.ball_position = 3
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll: punt result, Second roll: return result
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Punt roll
                (15, "B1+W5+W0=15")   # Return roll
            ]
            
            # Patch return chart to have -10 yards (minus return)
            game.state.defense_team.special_teams.punt_return[15] = "-10"
            
            outcome = game._handle_punt(short_drop=True)
            
            # With short-drop, minus return becomes 0
            assert "0" in outcome.description or "no return" in outcome.description.lower()

    def test_coffin_corner_subtracts_yardage(self, game):
        """Coffin-corner punt should subtract specified yards from punt distance."""
        game.state.ball_position = 20
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Punt would normally go 40 yards
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.state.possession_team.special_teams.punt[10] = "40"
            
            outcome = game._handle_punt(coffin_corner_yards=10)
            
            # Should subtract 10 yards from 40 = 30 yard punt
            assert "30" in outcome.description or "10 yards subtracted" in outcome.description

    def test_coffin_corner_15_yards_auto_out_of_bounds(self, game):
        """Coffin-corner with 15+ yards subtracted = automatic out of bounds."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.state.possession_team.special_teams.punt[10] = "45"
            
            outcome = game._handle_punt(coffin_corner_yards=15)
            
            # Should be out of bounds, no return
            assert "out of bounds" in outcome.description.lower() or "coffin" in outcome.description.lower()

    def test_coffin_corner_20_yards_auto_out_of_bounds(self, game):
        """Coffin-corner with 20 yards subtracted = automatic out of bounds."""
        game.state.ball_position = 40
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (10, "B1+W0+W0=10")
            
            game.state.possession_team.special_teams.punt[10] = "50"
            
            outcome = game._handle_punt(coffin_corner_yards=20)
            
            # Should be out of bounds
            assert "out of bounds" in outcome.description.lower() or "coffin" in outcome.description.lower()

    def test_coffin_corner_less_than_15_allows_return(self, game):
        """Coffin-corner with less than 15 yards can still be returned."""
        game.state.ball_position = 25
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [
                (10, "B1+W0+W0=10"),  # Punt roll
                (15, "B1+W5+W0=15")   # Return roll
            ]
            
            game.state.possession_team.special_teams.punt[10] = "45"
            game.state.defense_team.special_teams.punt_return[15] = "10"
            
            outcome = game._handle_punt(coffin_corner_yards=10)
            
            # Should still allow return (not automatic OOB)
            # The punt goes 45-10=35 yards
            assert "returned" in outcome.description.lower() or "10" in outcome.description


class TestPuntDiceDisplay:
    """Tests for punt dice display format."""

    def test_punt_dice_roll_stored_in_result(self, game):
        """Punt result should include the dice roll."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "40"
            
            outcome = game._handle_punt()
            
            assert outcome.result.dice_roll == 17

    def test_punt_fair_catch_dice_format(self, game):
        """Punt with fair catch should show dice in display."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "40*"
            
            outcome = game._handle_punt()
            
            assert outcome.result.dice_roll == 17
            assert "fair catch" in outcome.description.lower()
    
    def test_punt_return_dice_roll_stored_in_result(self, game):
        """Punt return result should include the return dice roll."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # First roll: punt 40 yards
            # Second roll: return 10 yards
            mock_dice.side_effect = [
                (17, "B2+W2+W5=17"),  # Punt
                (10, "B1+W1+W1=10"),  # Return
            ]
            
            game.state.possession_team.special_teams.punt[17] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game._handle_punt()
            
            assert outcome.result.dice_roll == 17
            assert outcome.result.punt_return_dice == 10
            assert "returned 10 yards" in outcome.description


class TestPuntShankCommentary:
    """Tests for punt shank commentary."""

    def test_shank_commentary_for_short_normal_punt(self, game):
        """Normal punt under 20 yards should show 'Shanked!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "15"
            
            outcome = game._handle_punt()
            
            assert "shanked" in outcome.description.lower()

    def test_no_shank_for_short_drop_punt(self, game):
        """Short-drop punt under 20 yards should NOT show 'Shanked!' commentary."""
        game.state.ball_position = 3
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "15"
            
            outcome = game._handle_punt(short_drop=True)
            
            assert "shanked" not in outcome.description.lower()

    def test_no_shank_for_coffin_corner_punt(self, game):
        """Coffin-corner punt under 20 yards should NOT show 'Shanked!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "25"
            
            outcome = game._handle_punt(coffin_corner_yards=10)
            
            assert "shanked" not in outcome.description.lower()
            assert "[CC:" in outcome.description

    def test_no_shank_for_normal_punt_20_plus_yards(self, game):
        """Normal punt 20+ yards should NOT show 'Shanked!' commentary."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.return_value = (17, "B2+W2+W5=17")
            
            game.state.possession_team.special_teams.punt[17] = "40"
            
            outcome = game._handle_punt()
            
            assert "shanked" not in outcome.description.lower()


class TestPuntPenaltyApplyMethods:
    """Tests for apply_punt_penalty_decision method.
    
    Chart penalties use scrimmage play perspective:
    - OFF penalty = punting team foul → receiving team gets choice (replay or keep+yards)
    - DEF penalty = receiving team foul → punting team gets choice (accept for yards/1st down or decline)
    """
    
    def test_apply_punt_penalty_decision_off_accept_replay(self, game):
        """OFF penalty (punting team foul) accept = replay punt from LOS - penalty yards."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Receiving team accepts penalty = replay punt from LOS - 5 yards
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            assert game.state.ball_position == 25  # 30 - 5
            assert game.state.is_home_possession is True  # Still punting team's ball
            assert "replay" in final_outcome.description.lower()
    
    def test_apply_punt_penalty_decision_off_decline_keep_result(self, game):
        """OFF penalty (punting team foul) decline = keep result + penalty yards."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Receiving team declines penalty = keep result + 5 yards
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # Punt 40 from 30 = 70, return 10 = 40, + 5 penalty = 45
            assert game.state.ball_position == 45
            assert game.state.is_home_possession is False  # Receiving team has ball
            assert "keeps result" in final_outcome.description.lower()
    
    def test_apply_punt_penalty_decision_def_accept_first_down(self, game):
        """DEF penalty (receiving team foul) accept = ball moves forward, potential first down."""
        game.state.ball_position = 30
        game.state.yards_to_go = 10
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "DEF 15"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Punting team accepts penalty = ball moves forward 15 yards, first down
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            
            assert game.state.ball_position == 45  # 30 + 15
            assert game.state.is_home_possession is True  # Punting team keeps ball
            assert game.state.down == 1  # First down
            assert final_outcome.first_down is True
    
    def test_apply_punt_penalty_decision_def_decline(self, game):
        """DEF penalty (receiving team foul) decline = take punt result as-is."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "DEF 5"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            assert outcome.pending_penalty_decision is True
            
            # Punting team declines penalty = take punt result
            final_outcome = game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            
            # Punt 40 from 30 = 70, return 10 = 40
            assert game.state.ball_position == 40
            assert game.state.is_home_possession is False  # Receiving team has ball
            assert "declines" in final_outcome.description.lower()


class TestPuntPenaltyDisplayLogic:
    """Tests for punt penalty display in handle_penalty_decision.
    
    Verifies that punt penalties show 'Punt stands as called' instead of
    incorrectly showing 'TURNOVER ON DOWNS' when declining the penalty.
    """
    
    def test_punt_penalty_play_type_is_punt(self, game):
        """Punt penalty outcome should have play_type=PUNT for correct display routing."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        game.state.down = 4  # 4th down punt
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 15"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            # The outcome should have play_type=PUNT so display logic routes correctly
            assert outcome.play_type == PlayType.PUNT
            assert outcome.pending_penalty_decision is True
            # This ensures handle_penalty_decision will use is_punt_penalty branch
            # which shows "Punt stands as called" instead of "TURNOVER ON DOWNS"
    
    def test_punt_penalty_stores_final_position_for_display(self, game):
        """Punt penalty should store final_position in _pending_punt_state for display."""
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 5"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert outcome.pending_penalty_decision is True
            # The pending state should have final_position for display
            assert hasattr(game, '_pending_punt_state')
            assert 'final_position' in game._pending_punt_state
            # Punt 40 from 30 = 70, return 10 = 40
            assert game._pending_punt_state['final_position'] == 40
    
    def test_punt_penalty_half_distance_adjusts_position(self, game):
        """When half-distance rule applies, penalty position should be adjusted.
        
        This tests that when a 15-yard penalty is called near the goal line,
        the half-distance rule is applied and the adjusted position is used.
        Example: Ball at own 17, OFF 15 penalty -> half-distance = 8 yards
        Display should show 'Replay punt from own 9' not 'from own 2'.
        """
        from paydirt.penalty_handler import apply_half_distance_rule
        
        # Ball at own 17 (position 17), OFF 15 penalty
        ball_position = 17
        penalty_yards = 15
        is_offensive_penalty = True  # OFF penalty moves ball backward
        
        # Half-distance rule: can't go more than half the distance to goal
        # Half of 17 = 8.5, rounded to 8
        adjusted_yards = apply_half_distance_rule(
            penalty_yards, ball_position, is_offensive_penalty
        )
        
        # Should be reduced to 8 yards (half-distance)
        assert adjusted_yards == 8
        
        # New position should be 17 - 8 = 9 (own 9)
        new_position = ball_position - adjusted_yards
        assert new_position == 9
    
    def test_punt_penalty_stores_dice_roll_for_display(self, game):
        """Punt penalty should store punt_roll in _pending_punt_state for dice display.
        
        This ensures handle_penalty_decision can show dice rolls like:
        (P:14→"OFF 15" | R:→"10")
        """
        game.state.ball_position = 30
        game.state.is_home_possession = True
        
        with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
            # Roll 14 for punt chart (OFF 15), roll 15 for reroll (40 yards), roll 10 for return
            mock_dice.side_effect = [(14, "B1+W3+W0=14"), (15, "B2+W3+W0=15"), (10, "B1+W0+W0=10")]
            
            game.state.possession_team.special_teams.punt[14] = "OFF 15"
            game.state.possession_team.special_teams.punt[15] = "40"
            game.state.defense_team.special_teams.punt_return[10] = "10"
            
            outcome = game.run_play(PlayType.PUNT, None)
            
            assert outcome.pending_penalty_decision is True
            assert hasattr(game, '_pending_punt_state')
            
            # Verify dice roll info is stored for display
            state = game._pending_punt_state
            assert 'punt_roll' in state
            assert state['punt_roll'] == 14
            assert 'punt_result' in state
            assert state['punt_result'] == "OFF 15"
            assert 'return_yards' in state
            assert state['return_yards'] == 10
