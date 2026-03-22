"""
Tests for season rules configuration.

Tests loading YAML files, scaffolding, validation,
and integration with the game engine.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from paydirt.season_rules import (
    SeasonRules,
    OvertimeConfig,
    load_season_rules,
    season_rules_to_overtime_rules,
    scaffold_season_rules,
)
from paydirt.overtime_rules import OvertimeFormat, OvertimeRules


@pytest.fixture
def seasons_dir():
    """Use the real seasons directory for tests that need actual YAML files."""
    return Path(__file__).parent.parent / "seasons"


@pytest.fixture
def temp_season_dir():
    """Create a temporary season directory for isolated tests."""
    tmp = tempfile.mkdtemp()
    season_dir = Path(tmp) / "2000"
    season_dir.mkdir()
    yield season_dir
    shutil.rmtree(tmp)


class TestLoadSeasonRules:
    """Tests for loading season rules from YAML files."""

    def test_load_1972_rules(self, seasons_dir):
        """1972 season: no 2-point conversion, sudden death OT."""
        rules = load_season_rules(seasons_dir / "1972")
        assert rules.season == 1972
        assert rules.two_point_conversion is False
        assert rules.overtime.format == "sudden_death"
        assert rules.overtime.period_length_minutes == 15
        assert rules.overtime.max_periods_regular == 1
        assert rules.overtime.can_end_in_tie_regular is True

    def test_load_1983_rules(self, seasons_dir):
        """1983 season: same rules as 1972."""
        rules = load_season_rules(seasons_dir / "1983")
        assert rules.season == 1983
        assert rules.two_point_conversion is False
        assert rules.overtime.format == "sudden_death"

    def test_load_2026_rules(self, seasons_dir):
        """2026 season: 2-point conversion, modified sudden death OT."""
        rules = load_season_rules(seasons_dir / "2026")
        assert rules.season == 2026
        assert rules.two_point_conversion is True
        assert rules.overtime.format == "modified_sudden_death"
        assert rules.overtime.period_length_minutes == 10

    def test_missing_yaml_raises_error(self, temp_season_dir):
        """Missing YAML file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_season_rules(temp_season_dir)
        assert "Season rules file not found" in str(exc_info.value)
        assert "--scaffold-season" in str(exc_info.value)

    def test_empty_yaml_raises_error(self, temp_season_dir):
        """Empty YAML file should raise ValueError."""
        yaml_path = temp_season_dir / f"{temp_season_dir.name}.yaml"
        yaml_path.write_text("")
        with pytest.raises(ValueError) as exc_info:
            load_season_rules(temp_season_dir)
        assert "empty" in str(exc_info.value)

    def test_malformed_yaml_raises_error(self, temp_season_dir):
        """YAML with missing required fields should raise ValueError."""
        yaml_path = temp_season_dir / f"{temp_season_dir.name}.yaml"
        yaml_path.write_text("season: 2000\n")
        with pytest.raises(ValueError) as exc_info:
            load_season_rules(temp_season_dir)
        assert "two_point_conversion" in str(exc_info.value)

    def test_missing_overtime_section_raises_error(self, temp_season_dir):
        """YAML without overtime section should raise ValueError."""
        yaml_path = temp_season_dir / f"{temp_season_dir.name}.yaml"
        yaml_path.write_text("season: 2000\ntwo_point_conversion: false\n")
        with pytest.raises(ValueError) as exc_info:
            load_season_rules(temp_season_dir)
        assert "overtime" in str(exc_info.value)

    def test_invalid_overtime_format_raises_error(self, temp_season_dir):
        """Invalid overtime format should raise ValueError."""
        yaml_path = temp_season_dir / f"{temp_season_dir.name}.yaml"
        yaml_path.write_text(
            "season: 2000\ntwo_point_conversion: false\n"
            "overtime:\n  enabled: true\n  format: invalid_format\n"
            "  period_length_minutes: 15\n  max_periods_regular: 1\n"
            "  max_periods_playoff: 0\n  can_end_in_tie_regular: true\n"
            "  can_end_in_tie_playoff: false\n  coin_toss_winner_receives: true\n"
        )
        with pytest.raises(ValueError) as exc_info:
            load_season_rules(temp_season_dir)
        assert "Invalid overtime format" in str(exc_info.value)


class TestSeasonRulesToDict:
    """Tests for SeasonRules.to_dict() method."""

    def test_to_dict_returns_correct_structure(self, seasons_dir):
        """to_dict should return properly structured dictionary."""
        rules = load_season_rules(seasons_dir / "1972")
        d = rules.to_dict()
        assert d["season"] == 1972
        assert d["two_point_conversion"] is False
        assert "overtime" in d
        assert d["overtime"]["format"] == "sudden_death"
        assert d["overtime"]["enabled"] is True


class TestSeasonRulesToOvertimeRules:
    """Tests for converting SeasonRules to OvertimeRules."""

    def test_sudden_death_conversion(self, seasons_dir):
        """Sudden death season should convert to SUDDEN_DEATH format."""
        rules = load_season_rules(seasons_dir / "1972")
        ot_rules = season_rules_to_overtime_rules(rules)
        assert isinstance(ot_rules, OvertimeRules)
        assert ot_rules.format == OvertimeFormat.SUDDEN_DEATH
        assert ot_rules.period_length_minutes == 15
        assert ot_rules.can_end_in_tie_regular is True

    def test_modified_sudden_death_conversion(self, seasons_dir):
        """Modern season should convert to MODIFIED_SUDDEN_DEATH format."""
        rules = load_season_rules(seasons_dir / "2026")
        ot_rules = season_rules_to_overtime_rules(rules)
        assert ot_rules.format == OvertimeFormat.MODIFIED_SUDDEN_DEATH
        assert ot_rules.period_length_minutes == 10


class TestScaffoldSeasonRules:
    """Tests for YAML scaffolding."""

    def test_pre_1994_no_two_point(self):
        """Pre-1994 seasons should scaffold with two_point_conversion: false."""
        yaml_str = scaffold_season_rules(1972)
        assert "two_point_conversion: false" in yaml_str
        assert "format: sudden_death" in yaml_str
        assert "period_length_minutes: 15" in yaml_str

    def test_post_1994_has_two_point(self):
        """Post-1994 seasons should scaffold with two_point_conversion: true."""
        yaml_str = scaffold_season_rules(2000)
        assert "two_point_conversion: true" in yaml_str

    def test_post_2010_modified_sudden_death(self):
        """Post-2010 seasons should use modified sudden death."""
        yaml_str = scaffold_season_rules(2015)
        assert "format: modified_sudden_death" in yaml_str
        assert "period_length_minutes: 15" in yaml_str

    def test_post_2017_ten_minute_ot(self):
        """Post-2017 seasons should use 10-minute overtime."""
        yaml_str = scaffold_season_rules(2026)
        assert "period_length_minutes: 10" in yaml_str

    def test_scaffold_creates_valid_yaml(self, temp_season_dir):
        """Scaffolded YAML should be loadable."""
        year = int(temp_season_dir.name)
        yaml_str = scaffold_season_rules(year)
        yaml_path = temp_season_dir / f"{year}.yaml"
        yaml_path.write_text(yaml_str)
        rules = load_season_rules(temp_season_dir)
        assert rules.season == year


class TestSeasonRulesDataClasses:
    """Tests for the dataclass structures."""

    def test_overtime_config_fields(self):
        """OvertimeConfig should have all required fields."""
        config = OvertimeConfig(
            enabled=True,
            format="sudden_death",
            period_length_minutes=15.0,
            max_periods_regular=1,
            max_periods_playoff=0,
            can_end_in_tie_regular=True,
            can_end_in_tie_playoff=False,
            coin_toss_winner_receives=True,
        )
        assert config.enabled is True
        assert config.format == "sudden_death"

    def test_season_rules_fields(self):
        """SeasonRules should have all required fields."""
        config = OvertimeConfig(
            enabled=True,
            format="sudden_death",
            period_length_minutes=15.0,
            max_periods_regular=1,
            max_periods_playoff=0,
            can_end_in_tie_regular=True,
            can_end_in_tie_playoff=False,
            coin_toss_winner_receives=True,
        )
        rules = SeasonRules(
            season=2000,
            two_point_conversion=True,
            overtime=config,
        )
        assert rules.season == 2000
        assert rules.two_point_conversion is True
