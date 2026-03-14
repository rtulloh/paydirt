"""
Tests for team charts and play resolution.
"""
import pytest
from pathlib import Path
from unittest.mock import patch

from paydirt.models import Team, PlayType, DefenseType, PlayResult
from paydirt.team_charts import (
    roll_dice, get_play_chart, resolve_play, resolve_field_goal,
    resolve_punt, resolve_extra_point, resolve_two_point_conversion,
    apply_team_modifier, apply_defense_modifier, get_base_rushing_chart,
    PlayOutcome
)
from paydirt.chart_loader import load_team_chart


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


class TestChartLoaderPeripheralFromOffense:
    """Tests for extracting peripheral data from offense.csv (no PERIPHERAL file needed)."""
    
    def test_load_team_extracts_year_and_name(self):
        """Chart loader should extract year and team name from directory."""
        team_dir = Path('seasons/1983/Bills')
        if not team_dir.exists():
            pytest.skip("Test data not available")
        
        chart = load_team_chart(team_dir)
        
        assert chart.peripheral.year == 1983
        assert chart.peripheral.team_name == "Bills"
    
    def test_load_team_extracts_fumble_ranges(self):
        """Chart loader should extract fumble recovery ranges from offense.csv."""
        team_dir = Path('seasons/1983/Bills')
        if not team_dir.exists():
            pytest.skip("Test data not available")
        
        chart = load_team_chart(team_dir)
        
        # Bills have fumble recovered 10-29, lost 30-39 (from Excel PERIPHERAL DATA)
        assert chart.peripheral.fumble_recovered_range == (10, 29)
        assert chart.peripheral.fumble_lost_range == (30, 39)
    
    def test_load_team_generates_short_name(self):
        """Chart loader should generate correct short names."""
        team_dir = Path('seasons/1983/Bills')
        if not team_dir.exists():
            pytest.skip("Test data not available")
        
        chart = load_team_chart(team_dir)
        
        assert chart.peripheral.short_name == "BUF '83"
    
    def test_load_team_disambiguates_ny_teams(self):
        """Chart loader should correctly distinguish Giants vs Jets."""
        giants_dir = Path('seasons/1983/Giants')
        jets_dir = Path('seasons/1983/Jets')
        
        if not giants_dir.exists() or not jets_dir.exists():
            pytest.skip("Test data not available")
        
        giants = load_team_chart(giants_dir)
        jets = load_team_chart(jets_dir)
        
        assert giants.peripheral.short_name == "NYG '83"
        assert jets.peripheral.short_name == "NYJ '83"
    
    def test_load_team_disambiguates_la_teams(self):
        """Chart loader should correctly distinguish Raiders vs Rams."""
        raiders_dir = Path('seasons/1983/Raiders')
        rams_dir = Path('seasons/1983/Rams')
        
        if not raiders_dir.exists() or not rams_dir.exists():
            pytest.skip("Test data not available")
        
        raiders = load_team_chart(raiders_dir)
        rams = load_team_chart(rams_dir)
        
        assert raiders.peripheral.short_name == "LV '83"
        assert rams.peripheral.short_name == "LAR '83"
    
    def test_fumble_ranges_vary_by_team(self):
        """Different teams should have different fumble recovery ranges."""
        teams_dir = Path('seasons/1983')
        if not teams_dir.exists():
            pytest.skip("Test data not available")
        
        fumble_ranges = set()
        for team_dir in teams_dir.iterdir():
            if team_dir.is_dir():
                chart = load_team_chart(team_dir)
                fumble_ranges.add(chart.peripheral.fumble_recovered_range)
        
        # Should have multiple different fumble ranges (not all defaults)
        assert len(fumble_ranges) > 5, "Expected varied fumble ranges across teams"
    
    def test_all_teams_load_without_peripheral_file(self):
        """All 28 teams should load successfully without PERIPHERAL file."""
        teams_dir = Path('seasons/1983')
        if not teams_dir.exists():
            pytest.skip("Test data not available")
        
        loaded_count = 0
        for team_dir in teams_dir.iterdir():
            if team_dir.is_dir():
                # This should not raise an error
                chart = load_team_chart(team_dir)
                assert chart.peripheral.short_name  # Should have a short name
                assert chart.peripheral.fumble_recovered_range[0] == 10  # All start at 10
                loaded_count += 1
        
        assert loaded_count == 28, f"Expected 28 teams, got {loaded_count}"


class TestExtraPointChartLoading:
    """Tests for loading extra point no-good rolls from special.csv."""

    def test_extra_point_no_good_loaded_from_csv(self):
        """Chart loader should extract extra_point_no_good rolls from special.csv."""
        team_dir = Path('seasons/1983/Bills')
        if not team_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(team_dir)

        # Bills have extra point failures on rolls 13, 18, 19, 20
        assert 13 in chart.special_teams.extra_point_no_good
        assert 18 in chart.special_teams.extra_point_no_good
        assert 19 in chart.special_teams.extra_point_no_good
        assert 20 in chart.special_teams.extra_point_no_good

    def test_1972_format_uses_zero_for_no_good(self):
        """1972 format uses 0 for no good, 1 for good - should parse correctly."""
        team_dir = Path('seasons/1972/Dolphins')
        if not team_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(team_dir)

        # 1972 Dolphins should have roll 20 as no good (column has 0)
        assert 20 in chart.special_teams.extra_point_no_good

        # Other rolls should be good (not in no_good list)
        assert 10 not in chart.special_teams.extra_point_no_good
        assert 12 not in chart.special_teams.extra_point_no_good

    def test_1972_format_all_teams_have_no_good_roll(self):
        """All 1972 teams should have roll 20 as no good (era rule)."""
        teams_dir = Path('seasons/1972')
        if not teams_dir.exists():
            pytest.skip("Test data not available")

        for team_dir in sorted(teams_dir.iterdir()):
            if team_dir.is_dir():
                chart = load_team_chart(team_dir)
                # In 1972 era, only roll 20 fails (boxcars)
                assert 20 in chart.special_teams.extra_point_no_good, \
                    f"{team_dir.name} should have roll 20 as no good"

    def test_1983_format_uses_ng_for_no_good(self):
        """1983 format uses NG for no good, blank for good - should parse correctly."""
        team_dir = Path('seasons/1983/Jets')
        if not team_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(team_dir)

        # 1983 Jets have roll 13 as no good (column has NG)
        assert 13 in chart.special_teams.extra_point_no_good
        # Roll 10 should be good (column is blank)
        assert 10 not in chart.special_teams.extra_point_no_good

    def test_different_teams_have_different_no_good_rolls(self):
        """Different teams should have different extra point failure rolls."""
        teams_dir = Path('seasons/1983')
        if not teams_dir.exists():
            pytest.skip("Test data not available")

        bills = load_team_chart(teams_dir / 'Bills')
        dolphins = load_team_chart(teams_dir / 'Dolphins')

        # Teams should have different no-good rolls
        assert bills.special_teams.extra_point_no_good != dolphins.special_teams.extra_point_no_good

    def test_all_teams_have_extra_point_data(self):
        """All 28 teams should have extra_point_no_good data."""
        teams_dir = Path('seasons/1983')
        if not teams_dir.exists():
            pytest.skip("Test data not available")

        for team_dir in teams_dir.iterdir():
            if team_dir.is_dir():
                chart = load_team_chart(team_dir)
                assert chart.special_teams.extra_point_no_good is not None


class Test1983BearsDefenseChart:
    """Tests for 1983 Bears defense chart values."""

    def test_bears_defense_b3_modifiers(self):
        """Bears defense B-3 should have correct modifier values."""
        bears_dir = Path('seasons/1983/Bears')
        if not bears_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(bears_dir)

        # B-3: dice 1=(1), dice 2=(1), dice 4=-1, dice 6=(6) - parens from Excel format
        b3_modifiers = chart.defense.modifiers.get(('B', 3), {})
        
        assert b3_modifiers.get(1) == '(1)'
        assert b3_modifiers.get(2) == '(1)'
        assert b3_modifiers.get(4) == '-1'
        assert b3_modifiers.get(6) == '(6)'
        # Empty columns should not be present
        assert 3 not in b3_modifiers
        assert 5 not in b3_modifiers
        assert 7 not in b3_modifiers
        assert 8 not in b3_modifiers
        assert 9 not in b3_modifiers

    def test_bears_defense_d5_modifiers(self):
        """Bears defense D-5 should have correct modifier values."""
        bears_dir = Path('seasons/1983/Bears')
        if not bears_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(bears_dir)

        # D-5: dice 4=2, dice 5=-1, dice 6=-1, dice 7=[TD], dice 8=[TD], dice 9=(3)
        d5_modifiers = chart.defense.modifiers.get(('D', 5), {})
        
        assert d5_modifiers.get(4) == '2'
        assert d5_modifiers.get(5) == '-1'
        assert d5_modifiers.get(6) == '-1'
        assert d5_modifiers.get(7) == '[TD]'
        assert d5_modifiers.get(8) == '[TD]'
        assert d5_modifiers.get(9) == '(3)'
        # Empty columns should not be present
        assert 1 not in d5_modifiers
        assert 2 not in d5_modifiers
        assert 3 not in d5_modifiers

    def test_bears_defense_has_30_rows(self):
        """Bears defense chart should have all 30 formation/sub-row combinations."""
        bears_dir = Path('seasons/1983/Bears')
        if not bears_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(bears_dir)

        # Should have 6 formations (A-F) x 5 sub-rows (1-5) = 30 entries
        assert len(chart.defense.modifiers) == 30

    def test_bears_defense_all_formations_present(self):
        """Bears defense chart should have all formations A-F."""
        bears_dir = Path('seasons/1983/Bears')
        if not bears_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(bears_dir)

        modifiers = chart.defense.modifiers
        
        for formation in ['A', 'B', 'C', 'D', 'E', 'F']:
            for sub_row in range(1, 6):
                assert (formation, sub_row) in modifiers, f"Missing {formation}-{sub_row}"


class Test1983BearsOffenseChart:
    """Tests for 1983 Bears offense chart values."""

    def test_bears_offense_roll_24(self):
        """Bears offense roll 24 should have correct values including empty cell and BLACK cells."""
        bears_dir = Path('seasons/1983/Bears')
        if not bears_dir.exists():
            pytest.skip("Test data not available")

        chart = load_team_chart(bears_dir)

        # Roll 24: Line Plunge=B, Off Tackle=-3, End Run=(empty), Draw=3, 
        # Screen=BLACK, Short=BLACK, Med=BLACK, Long=BLACK, T/E S/L=10, B=10, QT=8, Fumble=R
        assert chart.offense.line_plunge.get(24) == 'B'
        assert chart.offense.off_tackle.get(24) == '-3'
        assert chart.offense.end_run.get(24) is None  # Empty cell
        assert chart.offense.draw.get(24) == '3'
        assert chart.offense.screen.get(24) == 'BLACK'  # Incomplete pass
        assert chart.offense.short_pass.get(24) == 'BLACK'  # Incomplete pass
        assert chart.offense.medium_pass.get(24) == 'BLACK'  # Incomplete pass
        assert chart.offense.long_pass.get(24) == 'BLACK'  # Incomplete pass
        assert chart.offense.te_short_long.get(24) == '10'
        assert chart.offense.breakaway.get(24) == '10'
        assert chart.offense.qb_time.get(24) == '8'
        # Fumble is stored in peripheral - check that's loaded
        assert chart.peripheral.fumble_recovered_range is not None
