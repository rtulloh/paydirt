"""
Tests for team charts and play resolution.
"""
import pytest
from unittest.mock import patch

from paydirt.models import Team, PlayType, DefenseType, PlayResult
from paydirt.team_charts import (
    roll_dice, get_play_chart, resolve_play, resolve_field_goal,
    resolve_punt, resolve_extra_point, resolve_two_point_conversion,
    apply_team_modifier, apply_defense_modifier, get_base_rushing_chart,
    PlayOutcome
)


class TestDiceRolling:
    """Tests for dice rolling mechanics."""
    
    def test_roll_dice_range(self):
        """roll_dice should return values between 2 and 12."""
        for _ in range(100):
            result = roll_dice()
            assert 2 <= result <= 12
    
    @patch('paydirt.team_charts.random.randint')
    def test_roll_dice_uses_two_dice(self, mock_randint):
        """roll_dice should sum two dice rolls."""
        mock_randint.side_effect = [3, 4]  # First die = 3, second die = 4
        
        result = roll_dice()
        
        assert result == 7
        assert mock_randint.call_count == 2


class TestPlayCharts:
    """Tests for play outcome charts."""
    
    def test_rushing_chart_covers_all_rolls(self):
        """Rushing chart should have outcomes for all possible dice rolls."""
        chart = get_base_rushing_chart()
        
        for roll in range(2, 13):
            assert roll in chart
            assert isinstance(chart[roll], PlayOutcome)
    
    def test_rushing_chart_outcomes_make_sense(self):
        """Rushing chart outcomes should follow expected patterns."""
        chart = get_base_rushing_chart()
        
        # Low rolls should be bad
        assert chart[2].result in [PlayResult.FUMBLE, PlayResult.LOSS]
        assert chart[2].turnover is True
        
        # High rolls should be good
        assert chart[12].result == PlayResult.GAIN
        assert chart[12].yards > 20
    
    def test_get_play_chart_returns_correct_chart(self):
        """get_play_chart should return appropriate chart for play type."""
        # Running plays should use rushing chart
        run_chart = get_play_chart(PlayType.RUN_MIDDLE)
        assert run_chart[7].yards == 4  # Matches rushing chart
        
        # Short pass should use short pass chart
        pass_chart = get_play_chart(PlayType.SHORT_PASS)
        assert pass_chart[7].yards == 5  # Matches short pass chart


class TestTeamModifiers:
    """Tests for team rating modifiers."""
    
    def test_apply_team_modifier_neutral(self):
        """Equal ratings should result in minimal change."""
        base_yards = 10
        result = apply_team_modifier(base_yards, offense_rating=5, defense_rating=5)
        
        # Should be close to base yards (within variance)
        assert abs(result - base_yards) <= 4
    
    def test_apply_team_modifier_strong_offense(self):
        """Strong offense vs weak defense should increase yards."""
        results = []
        for _ in range(50):
            result = apply_team_modifier(10, offense_rating=9, defense_rating=3)
            results.append(result)
        
        # Average should be higher than base
        avg = sum(results) / len(results)
        assert avg > 10
    
    def test_apply_team_modifier_strong_defense(self):
        """Weak offense vs strong defense should decrease yards."""
        results = []
        for _ in range(50):
            result = apply_team_modifier(10, offense_rating=3, defense_rating=9)
            results.append(result)
        
        # Average should be lower than base
        avg = sum(results) / len(results)
        assert avg < 10


class TestDefenseModifiers:
    """Tests for defensive formation modifiers."""
    
    def test_blitz_vs_screen(self):
        """Blitz should be weak against screen passes."""
        outcome = PlayOutcome(PlayResult.GAIN, 10, "Screen pass")
        
        modified = apply_defense_modifier(outcome, DefenseType.BLITZ, PlayType.SCREEN_PASS)
        
        # Yards should increase vs blitz
        assert modified.yards > outcome.yards
    
    def test_blitz_vs_run(self):
        """Blitz should be weak against runs."""
        outcome = PlayOutcome(PlayResult.GAIN, 10, "Run play")
        
        modified = apply_defense_modifier(outcome, DefenseType.BLITZ, PlayType.RUN_MIDDLE)
        
        assert modified.yards > outcome.yards
    
    def test_prevent_vs_long_pass(self):
        """Prevent defense should limit long pass gains."""
        outcome = PlayOutcome(PlayResult.GAIN, 30, "Long pass")
        
        modified = apply_defense_modifier(outcome, DefenseType.PREVENT, PlayType.LONG_PASS)
        
        assert modified.yards < outcome.yards
    
    def test_prevent_vs_run(self):
        """Prevent defense should be weak against runs."""
        outcome = PlayOutcome(PlayResult.GAIN, 10, "Run play")
        
        modified = apply_defense_modifier(outcome, DefenseType.PREVENT, PlayType.RUN_MIDDLE)
        
        assert modified.yards > outcome.yards
    
    def test_goal_line_vs_short_run(self):
        """Goal line defense should limit short yardage runs."""
        outcome = PlayOutcome(PlayResult.GAIN, 4, "Run play")
        
        modified = apply_defense_modifier(outcome, DefenseType.GOAL_LINE, PlayType.RUN_MIDDLE)
        
        assert modified.yards < outcome.yards
    
    def test_normal_defense_no_change(self):
        """Normal defense should not modify outcomes."""
        outcome = PlayOutcome(PlayResult.GAIN, 10, "Play")
        
        modified = apply_defense_modifier(outcome, DefenseType.NORMAL, PlayType.RUN_MIDDLE)
        
        assert modified.yards == outcome.yards


class TestPlayResolution:
    """Tests for full play resolution."""
    
    @pytest.fixture
    def offense(self):
        """Create an offensive team."""
        return Team(name="Offense", abbreviation="OFF", rushing_offense=7, passing_offense=8)
    
    @pytest.fixture
    def defense(self):
        """Create a defensive team."""
        return Team(name="Defense", abbreviation="DEF", rushing_defense=6, passing_defense=5)
    
    def test_resolve_play_returns_dice_and_outcome(self, offense, defense):
        """resolve_play should return dice roll and outcome."""
        dice_roll, outcome = resolve_play(
            PlayType.RUN_MIDDLE, DefenseType.NORMAL, offense, defense
        )
        
        assert 2 <= dice_roll <= 12
        assert isinstance(outcome, PlayOutcome)
        assert outcome.result in PlayResult
    
    @patch('paydirt.team_charts.roll_dice')
    def test_resolve_play_uses_correct_chart(self, mock_roll, offense, defense):
        """resolve_play should use appropriate chart for play type."""
        mock_roll.return_value = 7
        
        # Run play
        _, run_outcome = resolve_play(PlayType.RUN_MIDDLE, DefenseType.NORMAL, offense, defense)
        
        # Short pass
        _, pass_outcome = resolve_play(PlayType.SHORT_PASS, DefenseType.NORMAL, offense, defense)
        
        # Outcomes should differ (different charts)
        # Both roll 7, but charts have different base yards
        assert run_outcome.description != pass_outcome.description


class TestSpecialTeams:
    """Tests for special teams plays."""
    
    def test_resolve_field_goal_short_range(self):
        """Short field goals should have high success rate."""
        successes = 0
        for _ in range(100):
            _, success = resolve_field_goal(distance=25, kicker_rating=5)
            if success:
                successes += 1
        
        # Should succeed most of the time
        assert successes > 70
    
    def test_resolve_field_goal_long_range(self):
        """Long field goals should have lower success rate."""
        successes = 0
        for _ in range(200):
            _, success = resolve_field_goal(distance=55, kicker_rating=5)
            if success:
                successes += 1
        
        # Should succeed less often (expected ~42% for 8+ on 2d6)
        # Allow up to 55% for random variance
        assert successes < 110  # Less than 55% success rate
    
    def test_resolve_field_goal_kicker_rating_matters(self):
        """Better kickers should make more field goals."""
        good_kicker_successes = 0
        bad_kicker_successes = 0
        
        for _ in range(100):
            _, success = resolve_field_goal(distance=45, kicker_rating=9)
            if success:
                good_kicker_successes += 1
            
            _, success = resolve_field_goal(distance=45, kicker_rating=2)
            if success:
                bad_kicker_successes += 1
        
        assert good_kicker_successes > bad_kicker_successes
    
    def test_resolve_punt_returns_distance(self):
        """resolve_punt should return valid punt distance."""
        dice_roll, distance = resolve_punt(punter_rating=5)
        
        assert 2 <= dice_roll <= 12
        assert 20 <= distance <= 70
    
    def test_resolve_punt_rating_affects_distance(self):
        """Better punters should average longer punts."""
        good_punter_distances = []
        bad_punter_distances = []
        
        for _ in range(100):
            _, dist = resolve_punt(punter_rating=9)
            good_punter_distances.append(dist)
            
            _, dist = resolve_punt(punter_rating=2)
            bad_punter_distances.append(dist)
        
        assert sum(good_punter_distances) / 100 > sum(bad_punter_distances) / 100
    
    def test_resolve_extra_point_high_success(self):
        """Extra points should succeed almost always."""
        successes = 0
        for _ in range(100):
            _, success = resolve_extra_point(kicker_rating=5)
            if success:
                successes += 1
        
        # Should succeed almost all the time
        assert successes > 90
    
    def test_resolve_two_point_conversion(self):
        """Two-point conversions should succeed about 40-50% of the time."""
        offense = Team(name="OFF", abbreviation="OFF")
        defense = Team(name="DEF", abbreviation="DEF")
        
        successes = 0
        for _ in range(100):
            _, success = resolve_two_point_conversion(PlayType.RUN_MIDDLE, offense, defense)
            if success:
                successes += 1
        
        # Should be around 40-50%
        assert 25 <= successes <= 65
