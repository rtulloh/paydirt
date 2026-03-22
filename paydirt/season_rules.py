"""
Season-specific rules loaded from YAML configuration files.

Each season directory (seasons/YYYY/) should contain a YYYY.yaml file
defining era-appropriate rules such as two-point conversion availability
and overtime format.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .overtime_rules import OvertimeRules, OvertimeFormat


@dataclass
class OvertimeConfig:
    """Overtime configuration for a season."""
    enabled: bool
    format: str  # "sudden_death" | "modified_sudden_death"
    period_length_minutes: float
    max_periods_regular: int
    max_periods_playoff: int
    can_end_in_tie_regular: bool
    can_end_in_tie_playoff: bool
    coin_toss_winner_receives: bool


@dataclass
class SeasonRules:
    """Complete season rules configuration."""
    season: int
    two_point_conversion: bool
    overtime: OvertimeConfig

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API consumption."""
        return {
            "season": self.season,
            "two_point_conversion": self.two_point_conversion,
            "overtime": {
                "enabled": self.overtime.enabled,
                "format": self.overtime.format,
                "period_length_minutes": self.overtime.period_length_minutes,
                "max_periods_regular": self.overtime.max_periods_regular,
                "max_periods_playoff": self.overtime.max_periods_playoff,
                "can_end_in_tie_regular": self.overtime.can_end_in_tie_regular,
                "can_end_in_tie_playoff": self.overtime.can_end_in_tie_playoff,
                "coin_toss_winner_receives": self.overtime.coin_toss_winner_receives,
            },
        }


def load_season_rules(season_dir: Path) -> SeasonRules:
    """
    Load season rules from YAML file.

    Expects a file named {season_dir}/{year}.yaml where year is
    the directory name (e.g., seasons/1972/1972.yaml).

    Args:
        season_dir: Path to the season directory (e.g., seasons/1972)

    Returns:
        SeasonRules loaded from the YAML file

    Raises:
        FileNotFoundError: If the season rules YAML file does not exist.
        ValueError: If the YAML is malformed or missing required fields.
    """
    season_dir = Path(season_dir)
    year_str = season_dir.name

    try:
        year = int(year_str)
    except ValueError:
        raise ValueError(
            f"Season directory name must be a year, got: {year_str}"
        )

    yaml_path = season_dir / f"{year}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Season rules file not found: {yaml_path}\n"
            f"Create it with: python -m paydirt --scaffold-season {year}"
        )

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Season rules file is empty: {yaml_path}")

    return _parse_season_rules(data, year, yaml_path)


def _parse_season_rules(data: dict[str, Any], year: int, yaml_path: Path) -> SeasonRules:
    """Parse season rules from loaded YAML data."""
    # Validate season field
    yaml_season = data.get("season")
    if yaml_season is not None and yaml_season != year:
        raise ValueError(
            f"Season mismatch in {yaml_path}: directory is {year}, "
            f"but YAML declares season {yaml_season}"
        )

    # Parse two_point_conversion
    if "two_point_conversion" not in data:
        raise ValueError(
            f"Missing required field 'two_point_conversion' in {yaml_path}"
        )
    two_point = bool(data["two_point_conversion"])

    # Parse overtime section
    ot_data = data.get("overtime")
    if not ot_data:
        raise ValueError(
            f"Missing required section 'overtime' in {yaml_path}"
        )

    required_ot_fields = [
        "enabled", "format", "period_length_minutes",
        "max_periods_regular", "max_periods_playoff",
        "can_end_in_tie_regular", "can_end_in_tie_playoff",
        "coin_toss_winner_receives",
    ]
    for field in required_ot_fields:
        if field not in ot_data:
            raise ValueError(
                f"Missing required field 'overtime.{field}' in {yaml_path}"
            )

    ot_format = ot_data["format"]
    if ot_format not in ("sudden_death", "modified_sudden_death"):
        raise ValueError(
            f"Invalid overtime format '{ot_format}' in {yaml_path}. "
            f"Must be 'sudden_death' or 'modified_sudden_death'"
        )

    overtime = OvertimeConfig(
        enabled=bool(ot_data["enabled"]),
        format=ot_format,
        period_length_minutes=float(ot_data["period_length_minutes"]),
        max_periods_regular=int(ot_data["max_periods_regular"]),
        max_periods_playoff=int(ot_data["max_periods_playoff"]),
        can_end_in_tie_regular=bool(ot_data["can_end_in_tie_regular"]),
        can_end_in_tie_playoff=bool(ot_data["can_end_in_tie_playoff"]),
        coin_toss_winner_receives=bool(ot_data["coin_toss_winner_receives"]),
    )

    return SeasonRules(
        season=year,
        two_point_conversion=two_point,
        overtime=overtime,
    )


def season_rules_to_overtime_rules(rules: SeasonRules) -> OvertimeRules:
    """
    Convert SeasonRules.overtime to an OvertimeRules instance.

    This provides compatibility with existing code that uses OvertimeRules.

    Args:
        rules: SeasonRules to convert

    Returns:
        OvertimeRules instance matching the season configuration
    """
    if rules.overtime.format == "sudden_death":
        fmt = OvertimeFormat.SUDDEN_DEATH
    else:
        fmt = OvertimeFormat.MODIFIED_SUDDEN_DEATH

    return OvertimeRules(
        format=fmt,
        period_length_minutes=rules.overtime.period_length_minutes,
        max_periods_regular=rules.overtime.max_periods_regular,
        max_periods_playoff=rules.overtime.max_periods_playoff,
        can_end_in_tie_regular=rules.overtime.can_end_in_tie_regular,
        can_end_in_tie_playoff=rules.overtime.can_end_in_tie_playoff,
        coin_toss_winner_receives=rules.overtime.coin_toss_winner_receives,
    )


def scaffold_season_rules(year: int) -> str:
    """
    Generate default YAML content for a given season year.

    Defaults are based on known NFL rule changes:
    - Two-point conversion introduced in 1994
    - Modified sudden death introduced in 2010
    - Overtime period reduced to 10 minutes in 2017

    Args:
        year: The season year (e.g., 1972, 2026)

    Returns:
        YAML string with default rules for that year
    """
    two_point = year >= 1994
    ot_format = "modified_sudden_death" if year >= 2010 else "sudden_death"
    period_length = 10.0 if year >= 2017 else 15.0

    return f"""season: {year}
two_point_conversion: {"true" if two_point else "false"}
overtime:
  enabled: true
  format: {ot_format}
  period_length_minutes: {period_length}
  max_periods_regular: 1
  max_periods_playoff: 0
  can_end_in_tie_regular: true
  can_end_in_tie_playoff: false
  coin_toss_winner_receives: true
"""
