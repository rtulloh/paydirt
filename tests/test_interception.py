"""
Tests for interception handling per official Paydirt rules.

Official rules:
- Move ball forward (+) or backward (-) the yards shown to get interception spot
- Defense rolls offensive dice and consults Interception Return column
- Defense may decline the interception (treat as incompletion) - handled in interactive mode
"""
import pytest
from unittest.mock import patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult


@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart with interception return data."""
    return SpecialTeamsChart(
        interception_return={
            10: "5",
            11: "8",
            12: "0",
            13: "14",
            14: "20",
            15: "-5",  # Negative return (tackled behind)
            16: "TD",  # Return touchdown
            17: "33",
            18: "56",
            19: "OFF 15",  # Penalty
            20: "10",
        },
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
        short_pass={10: "5", 11: "8", 12: "INC"},
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


class TestInterceptionSpot:
    """Tests for interception spot calculation."""
    
    def test_interception_at_positive_yards(self, game):
        """Interception at +8 yards should be 8 yards downfield from LOS."""
        game.state.ball_position = 50  # At midfield
        game.state.is_home_possession = True
        
        # Mock resolve_play to return an interception result
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,  # INT 8 = 8 yards downfield
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll of 10 (5 yard return)
                mock_dice.return_value = (10, "B1+W0+W0=10")
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        # INT 8 from 50 = ball at 58 from offense view
        # From defense view = 100 - 58 = 42
        assert outcome.result.result_type == ResultType.INTERCEPTION
        assert outcome.result.int_spot == 42  # Defense's perspective
    
    def test_interception_at_negative_yards(self, game):
        """Interception at -5 yards should be behind LOS."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-5,  # INT -5 = 5 yards behind LOS
            turnover=True,
            raw_result="INT -5",
            dice_roll=11,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (12, "B1+W2+W0=12")  # 0 yard return
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        # INT -5 from 50 = ball at 45 from offense view
        # From defense view = 100 - 45 = 55
        assert outcome.result.result_type == ResultType.INTERCEPTION
        assert outcome.result.int_spot == 55


class TestInterceptionReturn:
    """Tests for interception return mechanics."""
    
    def test_positive_return_yards(self, game):
        """Defense should gain yards on positive return."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll of 14 (20 yard return)
                mock_dice.return_value = (14, "B1+W4+W0=14")
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert outcome.result.int_return_yards == 20
        assert outcome.result.int_return_dice == 14
    
    def test_negative_return_yards(self, game):
        """Defense should lose yards on negative return (tackled behind)."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll of 15 (-5 yard return)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert outcome.result.int_return_yards == -5


class TestInterceptionReturnTouchdown:
    """Tests for pick-six (interception return TD)."""
    
    def test_return_td_on_td_result(self, game):
        """TD result in return column should score touchdown."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll of 16 (TD)
                mock_dice.return_value = (16, "B1+W6+W0=16")
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        # Away team (defense) should have scored
        assert game.state.away_score == initial_away_score + 6


class TestInterceptionPossessionChange:
    """Tests for possession change on interception."""
    
    def test_possession_switches_to_defense(self, game):
        """Possession should switch to defense after interception."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (10, "B1+W0+W0=10")
                
                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        # Home was on offense, so away should now have possession
        assert game.state.is_home_possession is False
        assert outcome.turnover is True
    
    def test_downs_reset_after_interception(self, game):
        """Downs should reset to 1st and 10 after interception."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 7
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (10, "B1+W0+W0=10")
                
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        assert game.state.down == 1
        assert game.state.yards_to_go == 10


class TestInterceptionStats:
    """Tests for interception statistics tracking."""
    
    def test_interception_counted_in_stats(self, game):
        """Interception should be counted in offense stats."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        # Home team is on offense, track their stats
        initial_ints = game.state.home_stats.interceptions_thrown
        
        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=8,
            turnover=True,
            raw_result="INT 8",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (10, "B1+W0+W0=10")
                
                game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)
        
        # After interception, possession switched, so check home_stats directly
        assert game.state.home_stats.interceptions_thrown == initial_ints + 1


class TestInterceptionInEndZone:
    """Tests for interception in end zone scenarios."""

    def test_interception_in_defense_own_end_zone_is_touchback(self, game):
        """INT in defense's own end zone (where offense was trying to score) = touchback."""
        # Offense at opponent's 2-yard line (ball_position = 98, about to score)
        # INT 3 yards downfield = raw_int_spot = 98 + 3 = 101 (in defense's end zone)
        # Defense intercepts in their own end zone = TOUCHBACK, ball at 20
        game.state.ball_position = 98
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=3,  # INT 3 yards downfield into end zone
            turnover=True,
            raw_result="INT 3",
            dice_roll=11,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll shouldn't matter - touchback has no return
                mock_dice.return_value = (10, "B1+W0+W0=10")

                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        # Should be a touchback, NOT a touchdown
        assert outcome.touchdown is False
        assert game.state.away_score == initial_away_score  # No points scored
        assert game.state.ball_position == 20  # Touchback at 20
        assert game.state.is_home_possession is False  # Defense has ball
        assert "TOUCHBACK" in outcome.result.description

    def test_interception_at_defense_goal_line_is_touchback(self, game):
        """INT at defense's goal line (raw_int_spot = 100) = touchback (goal line is part of end zone)."""
        # Offense at opponent's 5, INT 5 yards = raw_int_spot = 100 (at goal line, in end zone)
        game.state.ball_position = 95
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=5,  # INT exactly at goal line
            turnover=True,
            raw_result="INT 5",
            dice_roll=11,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (10, "B1+W0+W0=10")

                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        assert outcome.touchdown is False
        assert game.state.away_score == initial_away_score
        assert game.state.ball_position == 20
        assert "TOUCHBACK" in outcome.result.description

    def test_interception_in_offense_own_end_zone_is_td_for_defense(self, game):
        """INT in offense's own end zone (behind goal line) = TD for defense."""
        # Offense at their own 3-yard line (ball_position = 3)
        # INT -5 yards (behind LOS) = raw_int_spot = 3 + (-5) = -2 (in offense's end zone, behind goal line)
        # Defense intercepts in opponent's end zone = TOUCHDOWN for defense
        game.state.ball_position = 3
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-5,  # INT behind LOS, into offense's end zone
            turnover=True,
            raw_result="INT -5",
            dice_roll=11,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        # Should be a TD for defense
        assert outcome.touchdown is True
        assert game.state.away_score == initial_away_score + 6
        assert "TOUCHDOWN" in outcome.result.description

    def test_interception_near_goal_line_has_normal_return(self, game):
        """INT near goal line (on field, not in end zone) should have normal return."""
        # Offense at their own 20, INT -5 yards = raw_int_spot = 15 (still on field)
        game.state.ball_position = 20
        game.state.is_home_possession = True

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-5,  # INT behind LOS but still on field
            turnover=True,
            raw_result="INT -5",
            dice_roll=11,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll of 10 = 5 yard return
                mock_dice.return_value = (10, "B1+W0+W0=10")

                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        # Should have a return (not touchback, not TD)
        # INT spot from defense = 100 - 15 = 85, plus 5 return = 90
        assert outcome.touchdown is False
        assert outcome.result.int_return_yards == 5
        assert outcome.result.int_return_dice == 10
        assert game.state.ball_position == 90
        assert outcome.turnover is True


class TestInterceptionReturnTouchdown:
    """Tests for interception return touchdowns."""

    def test_long_return_scores_touchdown(self, game):
        """INT return that crosses goal line should score TD."""
        # Ball at own 38 (offense perspective = 38)
        # INT 14 yards downfield = spot at 52 from offense = 48 from defense
        # Return of 72 yards = 48 + 72 = 120 >= 100 = TD
        game.state.ball_position = 38
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=14,  # INT 14 yards downfield
            turnover=True,
            raw_result="INT 14",
            dice_roll=18,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Return roll gives 72 yards (from chart entry "56" we use 72 for test)
                mock_dice.return_value = (18, "B1+W4+W4=18")
                # Mock the chart lookup to return 72 yards
                game.state.away_chart.special_teams.interception_return[18] = "72"

                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        # Should be a pick-six
        assert outcome.touchdown is True
        assert game.state.away_score == initial_away_score + 6

    def test_return_just_short_of_goal_line(self, game):
        """INT return that stops just short of goal line should not score."""
        # Ball at own 50, INT 10 yards downfield = spot at 60 from offense = 40 from defense
        # Return of 50 yards = 40 + 50 = 90 < 100 = no TD
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score

        mock_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=10,
            turnover=True,
            raw_result="INT 10",
            dice_roll=20,
        )

        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (20, "B2+W0+W0=20")
                game.state.away_chart.special_teams.interception_return[20] = "50"

                outcome = game.run_play(PlayType.SHORT_PASS, DefenseType.STANDARD)

        # Should NOT be a touchdown
        assert outcome.touchdown is False
        assert game.state.away_score == initial_away_score
        # Ball should be at the 90 yard line (from new offense's perspective)
        assert game.state.ball_position == 90
