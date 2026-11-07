"""
Tests for team charts and play resolution.
"""
import csv
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.chart_loader import load_team_chart
from paydirt.models import DefenseType, PlayResult, PlayType, Team
from paydirt.team_charts import (
    PlayOutcome,
    apply_defense_modifier,
    apply_team_modifier,
    get_base_rushing_chart,
    get_play_chart,
    resolve_extra_point,
    resolve_field_goal,
    resolve_play,
    resolve_punt,
    resolve_two_point_conversion,
    roll_dice,
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


@pytest.fixture
def chart_factory(tmp_path: Path) -> Callable[..., Path]:
    """Write independent synthetic CSV charts, with no historical input data."""
    def make(
        name: str = "Foundry",
        recovered_end: int = 29,
        short_name: str | None = None,
        extra_points: dict[int, str] | None = None,
        legacy_xp: bool = False,
    ) -> Path:
        directory = tmp_path / "2026" / name
        directory.mkdir(parents=True)
        with (directory / "offense.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["#", "Line Plunge", "Off Tackle", "End Run", "Draw",
                             "Screen", "Short", "Med", "Long", "T/E S/L", "B", "QT", "Fumble"])
            for roll in range(10, 40):
                values = ["4"] * 9 + ["30", "-6"]
                if roll == 24:
                    values = ["B", "-4", "", "6", "BLACK", "BLACK", "BLACK",
                              "BLACK", "14", "35", "-7"]
                elif roll == 25:
                    values[4] = "QT"
                elif roll == 26:
                    values[0] = "12*"
                writer.writerow([roll, *values, "R" if roll <= recovered_end else "L"])
            writer.writerow(["# Recovered", f"10-{recovered_end}"])
            writer.writerow(["# Lost", f"{recovered_end + 1}-39"])
        with (directory / "defense.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["#", "Formation", "Sub", *range(1, 10)])
            for formation in "ABCDEF":
                for row in range(1, 6):
                    values = ["0"] * 9
                    if (formation, row) == ("B", 3):
                        values = ["(2)", "(3)", "", "-2", "", "(8)", "", "", ""]
                    elif (formation, row) == ("D", 5):
                        values = ["", "", "", "4", "-3", "-2", "(TD)", "(TD)", "(5)"]
                    writer.writerow([f"{formation}-{row}", formation, row, *values])
        if extra_points is None:
            extra_points = {20: "0"} if legacy_xp else dict.fromkeys((13, 18, 19, 20), "NG")
        with (directory / "special.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["#", "Kickoff", "Kickoff Return", "Punt", "Punt Return",
                             "Int. Return", "Field Goal", "Extra Point"])
            for roll in range(10, 40):
                writer.writerow([roll, "60", "20", "40", "5", "8", "45",
                                 extra_points.get(roll, "1" if legacy_xp else "")])
        if short_name is not None:
            (directory / "team.yaml").write_text(f"short_name: {short_name}\n")
        return directory
    return make


@pytest.fixture
def chart_season(chart_factory: Callable[..., Path]) -> Path:
    """Retain a 28-team loader inventory using entirely invented charts."""
    for index in range(28):
        directory = chart_factory(
            f"Fixture{index:02d}", recovered_end=16 + index % 14,
            extra_points={10 + index % 30: "NG"},
        )
    return directory.parent


class TestChartLoaderPeripheralFromOffense:
    """Parse chart metadata without depending on imported developer charts."""

    def test_load_team_extracts_year_and_name(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert chart.peripheral.year == 2026
        assert chart.peripheral.team_name == "Foundry"

    def test_load_team_extracts_fumble_ranges(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert chart.peripheral.fumble_recovered_range == (10, 29)
        assert chart.peripheral.fumble_lost_range == (30, 39)

    def test_load_team_generates_short_name(self, chart_factory):
        """Without metadata, the loader derives an abbreviation from the directory."""
        chart = load_team_chart(chart_factory())
        assert chart.peripheral.short_name == "FOU '26"

    def test_load_team_disambiguates_shared_city_names(self, chart_factory):
        """Explicit metadata distinguishes two clubs with the same city prefix."""
        east = load_team_chart(chart_factory("MetroEast", short_name="MTE '26"))
        west = load_team_chart(chart_factory("MetroWest", short_name="MTW '26"))
        assert east.peripheral.short_name == "MTE '26"
        assert west.peripheral.short_name == "MTW '26"

    def test_load_team_disambiguates_shared_port_names(self, chart_factory):
        north = load_team_chart(chart_factory("PortNorth", short_name="PTN '26"))
        south = load_team_chart(chart_factory("PortSouth", short_name="PTS '26"))
        assert north.peripheral.short_name == "PTN '26"
        assert south.peripheral.short_name == "PTS '26"

    def test_fumble_ranges_vary_by_team(self, chart_season):
        ranges = {load_team_chart(team).peripheral.fumble_recovered_range
                  for team in chart_season.iterdir()}
        assert ranges == {(10, end) for end in range(16, 30)}

    def test_all_teams_load_without_peripheral_file(self, chart_season):
        teams = list(chart_season.iterdir())
        assert len(teams) == 28
        for directory in teams:
            assert not (directory / "PERIPHERAL DATA-Table 1.csv").exists()
            chart = load_team_chart(directory)
            assert chart.peripheral.short_name
            assert chart.peripheral.fumble_recovered_range[0] == 10


class TestExtraPointChartLoading:
    """Parse both supported XP encodings from explicitly written fixtures."""

    def test_extra_point_no_good_loaded_from_csv(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert set(chart.special_teams.extra_point_no_good) == {13, 18, 19, 20}
        assert 10 not in chart.special_teams.extra_point_no_good
        assert 11 not in chart.special_teams.extra_point_no_good

    def test_numeric_encoding_uses_zero_for_no_good(self, chart_factory):
        chart = load_team_chart(chart_factory(legacy_xp=True))
        assert set(chart.special_teams.extra_point_no_good) == {20}
        assert 10 not in chart.special_teams.extra_point_no_good
        assert 12 not in chart.special_teams.extra_point_no_good

    def test_numeric_encoding_in_multiple_teams(self, chart_factory):
        for index in range(28):
            chart = load_team_chart(chart_factory(f"Legacy{index:02d}", legacy_xp=True))
            assert set(chart.special_teams.extra_point_no_good) == {20}

    def test_text_encoding_uses_ng_for_no_good(self, chart_factory):
        chart = load_team_chart(chart_factory(extra_points={13: "NG"}))
        assert set(chart.special_teams.extra_point_no_good) == {13}
        assert 10 not in chart.special_teams.extra_point_no_good

    def test_different_teams_have_different_no_good_rolls(self, chart_factory):
        first = load_team_chart(chart_factory("First", extra_points={12: "NG"}))
        second = load_team_chart(chart_factory("Second", extra_points={17: "NG"}))
        assert set(first.special_teams.extra_point_no_good) == {12}
        assert set(second.special_teams.extra_point_no_good) == {17}
        assert first.special_teams.extra_point_no_good != second.special_teams.extra_point_no_good

    def test_all_teams_have_extra_point_data(self, chart_season):
        teams = list(chart_season.iterdir())
        assert len(teams) == 28
        for directory in teams:
            chart = load_team_chart(directory)
            assert chart.special_teams.extra_point_no_good is not None
            assert len(chart.special_teams.extra_point_no_good) == 1


class TestDefenseChartParsing:
    """Parse synthetic replacement markers, negative modifiers and empty cells."""

    def test_defense_b3_modifiers(self, chart_factory):
        chart = load_team_chart(chart_factory())
        modifiers = chart.defense.modifiers[("B", 3)]
        assert modifiers == {1: "(2)", 2: "(3)", 4: "-2", 6: "(8)"}
        assert all(column not in modifiers for column in (3, 5, 7, 8, 9))

    def test_defense_d5_modifiers(self, chart_factory):
        chart = load_team_chart(chart_factory())
        modifiers = chart.defense.modifiers[("D", 5)]
        assert modifiers == {4: "4", 5: "-3", 6: "-2", 7: "(TD)", 8: "(TD)", 9: "(5)"}
        assert all(column not in modifiers for column in (1, 2, 3))

    def test_defense_has_30_rows(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert len(chart.defense.modifiers) == 30

    def test_defense_all_formations_present(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert set(chart.defense.modifiers) == {
            (formation, row) for formation in "ABCDEF" for row in range(1, 6)
        }


class TestOffenseChartParsing:
    """Retain empty cells, BLACK, supplemental values and primary symbols."""

    def test_offense_mixed_roll(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert chart.offense.line_plunge[24] == "B"
        assert chart.offense.off_tackle[24] == "-4"
        assert chart.offense.end_run.get(24) is None
        assert chart.offense.draw[24] == "6"
        assert chart.offense.screen[24] == "BLACK"
        assert chart.offense.short_pass[24] == "BLACK"
        assert chart.offense.medium_pass[24] == "BLACK"
        assert chart.offense.long_pass[24] == "BLACK"
        assert chart.offense.te_short_long[24] == "14"
        assert chart.offense.breakaway[24] == "35"
        assert chart.offense.qb_time[24] == "-7"
        assert chart.peripheral.fumble_recovered_range == (10, 29)

    def test_offense_qt_and_sideline_symbols(self, chart_factory):
        chart = load_team_chart(chart_factory())
        assert chart.offense.screen[25] == "QT"
        assert chart.offense.line_plunge[26] == "12*"
