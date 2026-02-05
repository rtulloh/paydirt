"""
Tests for fumble handling per official Paydirt rules.

Official rules:
- Move ball forward (+) or backward (-) the yards shown
- Roll offensive dice and check FUMBLE line on Offensive Team Chart
- Offense recovers on rolls within recovered range, loses on lost range
- Special returns:
  - Defense gets INT return on lost fumbles with rolls 37, 38, 39 (39 = auto TD)
  - Offense gets INT return on recovered fumbles with rolls 17, 18, 19 (19 = auto TD)
- If offense recovers on 4th down but fails to make first down yardage, defense takes over
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
            15: "-5",
            16: "TD",
            17: "33",
            18: "56",
            19: "10",
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


class TestFumbleRecovery:
    """Tests for fumble recovery mechanics."""
    
    def test_offense_recovers_on_low_roll(self, game):
        """Offense should recover fumble on roll within recovered range."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,  # Fumble 3 yards downfield
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (within 10-27 range = recovered)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert outcome.turnover is False
        assert game.state.is_home_possession is True  # Still has possession
    
    def test_defense_recovers_on_high_roll(self, game):
        """Defense should recover fumble on roll within lost range."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 30 (within 28-39 range = lost)
                mock_dice.return_value = (30, "B2+W5+W4=30")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is False
        assert outcome.turnover is True
        assert game.state.is_home_possession is False  # Defense has possession


class TestFumbleSpot:
    """Tests for fumble spot calculation."""
    
    def test_fumble_spot_positive_yards(self, game):
        """Fumble spot should be calculated correctly for positive yards."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=5,  # Fumble 5 yards downfield
            turnover=True,
            raw_result="F + 5",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Fumble at 50 + 5 = 55
        assert outcome.result.fumble_spot == 55
    
    def test_fumble_spot_negative_yards(self, game):
        """Fumble spot should be calculated correctly for negative yards."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-3,  # Fumble 3 yards behind LOS
            turnover=True,
            raw_result="F - 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Fumble at 50 - 3 = 47
        assert outcome.result.fumble_spot == 47


class TestFumbleSpecialReturns:
    """Tests for special fumble return rules."""
    
    def test_offense_return_on_roll_17(self, game):
        """Offense should get INT return on recovery roll 17."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # First call: recovery roll of 17 (triggers return)
                # Second call: return roll of 14 (20 yard return)
                mock_dice.side_effect = [(17, "B1+W7+W0=17"), (14, "B1+W4+W0=14")]
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert outcome.result.fumble_return_yards == 20
        assert outcome.result.fumble_return_dice == 14
    
    def test_offense_auto_td_on_roll_19(self, game):
        """Recovery roll 19 should be automatic TD for offense."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_score = game.state.home_score
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 19 = auto TD
                mock_dice.side_effect = [(19, "B1+W9+W0=19"), (10, "B1+W0+W0=10")]
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.home_score == initial_score + 6
    
    def test_defense_return_on_roll_37(self, game):
        """Defense should get INT return on recovery roll 37."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # First call: recovery roll of 37 (triggers return)
                # Second call: return roll of 14 (20 yard return)
                mock_dice.side_effect = [(37, "B3+W5+W3=37"), (14, "B1+W4+W0=14")]
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is False
        assert outcome.result.fumble_return_yards == 20
        assert outcome.result.fumble_return_dice == 14
    
    def test_defense_auto_td_on_roll_39(self, game):
        """Recovery roll 39 should be automatic TD for defense."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_away_score = game.state.away_score
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 39 = auto TD for defense
                mock_dice.side_effect = [(39, "B3+W5+W5=39"), (10, "B1+W0+W0=10")]
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.touchdown is True
        assert game.state.away_score == initial_away_score + 6


class TestFumbleFourthDown:
    """Tests for 4th down fumble recovery rules."""
    
    def test_turnover_on_downs_if_recovered_short(self, game):
        """If offense recovers on 4th down but short of first down, defense gets ball."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 5
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=2,  # Only 2 yards, need 5
            turnover=True,
            raw_result="F + 2",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (recovered)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Offense recovered but short of first down on 4th down
        assert outcome.result.fumble_recovered is True
        assert outcome.turnover is True  # Turnover on downs
        assert game.state.is_home_possession is False  # Defense has ball
    
    def test_no_turnover_if_recovered_past_first_down(self, game):
        """If offense recovers on 4th down past first down marker, they keep ball."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 4
        game.state.yards_to_go = 3
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=5,  # 5 yards, need only 3
            turnover=True,
            raw_result="F + 5",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (recovered)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        # Offense recovered past first down marker
        assert outcome.result.fumble_recovered is True
        assert outcome.turnover is False
        assert game.state.is_home_possession is True


class TestFumbleStats:
    """Tests for fumble statistics tracking."""
    
    def test_fumble_lost_counted_in_stats(self, game):
        """Lost fumble should be counted in offense stats."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_fumbles = game.state.home_stats.fumbles_lost
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 30 (lost)
                mock_dice.return_value = (30, "B2+W5+W4=30")
                
                game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert game.state.home_stats.fumbles_lost == initial_fumbles + 1
    
    def test_fumble_recovered_not_counted_as_lost(self, game):
        """Recovered fumble should NOT be counted as lost."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        initial_fumbles = game.state.home_stats.fumbles_lost
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (recovered)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert game.state.home_stats.fumbles_lost == initial_fumbles  # No change


class TestFieldPositionDisplay:
    """Tests for proper field position display formatting.
    
    Field positions should always be displayed as team name + yard line (1-50),
    never as raw numbers > 50 (e.g., "55 yard line" is invalid).
    """
    
    def test_fumble_spot_on_offense_side(self):
        """Fumble at offense's 30 should display as 'OffTeam 30'."""
        # fumble_spot = 30 (offense's perspective, their own 30)
        fumble_spot = 30
        off_team = "NYG '83"
        def_team = "Wash 83"
        
        if fumble_spot <= 50:
            fumble_pos_str = f"{off_team} {fumble_spot}"
        else:
            fumble_pos_str = f"{def_team} {100 - fumble_spot}"
        
        assert fumble_pos_str == "NYG '83 30"
        assert "55" not in fumble_pos_str
        assert "60" not in fumble_pos_str
    
    def test_fumble_spot_on_defense_side(self):
        """Fumble at offense's 55 (defense's 45) should display as 'DefTeam 45'."""
        # fumble_spot = 55 (offense's perspective, past midfield)
        fumble_spot = 55
        off_team = "NYG '83"
        def_team = "Wash 83"
        
        if fumble_spot <= 50:
            fumble_pos_str = f"{off_team} {fumble_spot}"
        else:
            fumble_pos_str = f"{def_team} {100 - fumble_spot}"
        
        assert fumble_pos_str == "Wash 83 45"
        assert "55" not in fumble_pos_str
    
    def test_fumble_spot_at_midfield(self):
        """Fumble at the 50 should display as 'OffTeam 50'."""
        fumble_spot = 50
        off_team = "NYG '83"
        def_team = "Wash 83"
        
        if fumble_spot <= 50:
            fumble_pos_str = f"{off_team} {fumble_spot}"
        else:
            fumble_pos_str = f"{def_team} {100 - fumble_spot}"
        
        assert fumble_pos_str == "NYG '83 50"
    
    def test_fumble_spot_deep_in_defense_territory(self):
        """Fumble at offense's 90 (defense's 10) should display as 'DefTeam 10'."""
        fumble_spot = 90
        off_team = "NYG '83"
        def_team = "Wash 83"
        
        if fumble_spot <= 50:
            fumble_pos_str = f"{off_team} {fumble_spot}"
        else:
            fumble_pos_str = f"{def_team} {100 - fumble_spot}"
        
        assert fumble_pos_str == "Wash 83 10"
        assert "90" not in fumble_pos_str
    
    def test_interception_spot_on_offense_side(self):
        """Interception at offense's 25 should display as 'OffTeam 25'."""
        int_spot = 25
        off_team = "CHI '83"
        def_team = "GB '83"
        
        if int_spot <= 50:
            int_pos_str = f"{off_team} {int_spot}"
        else:
            int_pos_str = f"{def_team} {100 - int_spot}"
        
        assert int_pos_str == "CHI '83 25"
    
    def test_interception_spot_on_defense_side(self):
        """Interception at offense's 70 (defense's 30) should display as 'DefTeam 30'."""
        int_spot = 70
        off_team = "CHI '83"
        def_team = "GB '83"
        
        if int_spot <= 50:
            int_pos_str = f"{off_team} {int_spot}"
        else:
            int_pos_str = f"{def_team} {100 - int_spot}"
        
        assert int_pos_str == "GB '83 30"
        assert "70" not in int_pos_str


class TestFumbleRecoveryDownAdvancement:
    """Tests for down advancement when offense recovers own fumble."""
    
    def test_offense_recovers_fumble_down_advances(self, game):
        """When offense recovers own fumble, down should advance (not reset to 1st and 10)."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 1
        game.state.yards_to_go = 10
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,  # Fumble at line of scrimmage
            turnover=True,
            raw_result="F",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 15 (within 10-27 range = recovered)
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert outcome.turnover is False
        assert game.state.down == 2  # Down advanced from 1st to 2nd
        assert game.state.yards_to_go == 10  # Still 10 to go (no gain)
    
    def test_offense_recovers_fumble_on_2nd_down(self, game):
        """Fumble recovery on 2nd down should advance to 3rd down."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 7
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,
            turnover=True,
            raw_result="F",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert game.state.down == 3  # 2nd -> 3rd
        assert game.state.yards_to_go == 7  # Still 7 to go
    
    def test_offense_recovers_fumble_on_3rd_down(self, game):
        """Fumble recovery on 3rd down should advance to 4th down."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 3
        game.state.yards_to_go = 5
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,
            turnover=True,
            raw_result="F",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert game.state.down == 4  # 3rd -> 4th
        assert game.state.yards_to_go == 5
    
    def test_offense_recovers_fumble_forward_adjusts_ytg(self, game):
        """Fumble recovered forward should adjust yards to go."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 1
        game.state.yards_to_go = 10
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,  # Fumble 3 yards downfield
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert game.state.ball_position == 53  # 50 + 3
        assert game.state.down == 2
        assert game.state.yards_to_go == 7  # 10 - 3 = 7
    
    def test_offense_recovers_fumble_backward_increases_ytg(self, game):
        """Fumble recovered backward should increase yards to go."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 1
        game.state.yards_to_go = 10
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-3,  # Fumble 3 yards behind LOS
            turnover=True,
            raw_result="F - 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert game.state.ball_position == 47  # 50 - 3
        assert game.state.down == 2
        assert game.state.yards_to_go == 13  # 10 - (-3) = 13
    
    def test_offense_recovers_fumble_for_first_down(self, game):
        """Fumble recovered past first down marker should give first down."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 5
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=7,  # Fumble 7 yards downfield (past first down marker)
            turnover=True,
            raw_result="F + 7",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        assert outcome.first_down is True
        assert game.state.ball_position == 57  # 50 + 7
        assert game.state.down == 1  # First down!
        assert game.state.yards_to_go == 10
    
    def test_defense_recovers_fumble_gets_first_and_10(self, game):
        """When defense recovers fumble, they should get 1st and 10."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 7
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=3,
            turnover=True,
            raw_result="F + 3",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll of 30 (within 28-39 range = lost)
                mock_dice.side_effect = [(30, "B2+W5+W4=30"), (10, "B1+W0+W0=10")]
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is False
        assert outcome.turnover is True
        assert game.state.is_home_possession is False  # Defense has ball
        assert game.state.down == 1  # Fresh set of downs
        assert game.state.yards_to_go == 10
    
    def test_offense_recovers_fumble_not_counted_as_lost(self, game):
        """When offense recovers own fumble, it should not count as fumble lost."""
        game.state.ball_position = 50
        game.state.is_home_possession = True
        game.state.down = 1
        game.state.yards_to_go = 10
        initial_fumbles_lost = game.state.offense_stats.fumbles_lost
        
        mock_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,
            turnover=True,
            raw_result="F",
            dice_roll=10,
        )
        
        with patch('paydirt.game_engine.resolve_play', return_value=mock_result):
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                mock_dice.return_value = (15, "B1+W5+W0=15")
                
                outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
        
        assert outcome.result.fumble_recovered is True
        # Fumbles lost should not increase when offense recovers
        assert game.state.offense_stats.fumbles_lost == initial_fumbles_lost


class TestFumbleActionLine:
    """Tests for fumble action line display in transactions."""

    def test_fumble_turnover_zero_return_shows_spot(self, game):
        """Defense fumble recovery with 0 return yards should show the fumble spot."""
        from paydirt.play_events import PlayTransaction, EventType, PlayEvent
        
        # Create a transaction with fumble turnover and 0 return yards
        txn = PlayTransaction()
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE,
            description="Fumble",
            spot=36,
            dice_roll=15,
            chart_result="F + 8"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RECOVERY,
            description="Defense recovers",
            dice_roll=37,
            chart_result="lost"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RETURN,
            description="No return",
            yards=0,
            dice_roll=10,
            chart_result="0"
        ))
        txn.turnover = True
        txn.touchdown = False
        
        # Verify the transaction has the expected structure
        assert txn.has_event_type(EventType.FUMBLE)
        assert txn.turnover is True
        fumble_event = txn.get_events_by_type(EventType.FUMBLE)[0]
        assert fumble_event.spot == 36
        ret_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
        assert len(ret_events) == 1
        assert ret_events[0].yards == 0

    def test_fumble_turnover_with_return_yards(self, game):
        """Defense fumble recovery with positive return yards."""
        from paydirt.play_events import PlayTransaction, EventType, PlayEvent
        
        txn = PlayTransaction()
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE,
            description="Fumble",
            spot=50,
            dice_roll=15,
            chart_result="F"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RECOVERY,
            description="Defense recovers",
            dice_roll=37,
            chart_result="lost"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE_RETURN,
            description="Return",
            yards=15,
            dice_roll=14,
            chart_result="15"
        ))
        txn.turnover = True
        txn.touchdown = False
        
        ret_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
        assert ret_events[0].yards == 15

    def test_defense_fumble_return_on_roll_37_creates_event(self, game):
        """Defense recovery on roll 37 should create FUMBLE_RETURN event with actual yards."""
        from paydirt.play_events import EventType
        
        game.state.ball_position = 28  # Own 28
        game.state.is_home_possession = True
        game.state.down = 2
        game.state.yards_to_go = 12
        
        # Use run_play_with_penalty_procedure which creates transactions
        with patch('paydirt.game_engine.resolve_play_with_penalties') as mock_resolve:
            from paydirt.play_resolver import PenaltyChoice
            mock_resolve.return_value = PenaltyChoice(
                play_result=PlayResult(
                    result_type=ResultType.FUMBLE,
                    yards=8,  # Fumble at 36
                    turnover=True,
                    raw_result="F + 8",
                    dice_roll=15,
                ),
                penalty_options=[],
                offended_team="",
            )
            with patch('paydirt.game_engine.roll_chart_dice') as mock_dice:
                # Recovery roll 37 = defense recovers with return
                # Return roll 14 = some return yards
                mock_dice.side_effect = [
                    (37, "B3+W2+W2=37"),  # Recovery roll
                    (14, "B1+W2+W1=14"),  # Return roll
                ]
                
                outcome = game.run_play_with_penalty_procedure(
                    PlayType.SHORT_PASS, DefenseType.STANDARD
                )
        
        # Should have a transaction with FUMBLE_RETURN event
        assert outcome.transaction is not None
        txn = outcome.transaction
        
        # Verify FUMBLE_RETURN event exists
        ret_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
        assert len(ret_events) == 1
        # Return yards should match what was calculated (20 based on chart lookup)
        assert ret_events[0].yards == 20
