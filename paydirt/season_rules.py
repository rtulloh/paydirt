"""
Season-specific rules loaded from YAML configuration files.

Each season directory (seasons/YYYY/) should contain a YYYY.yaml file
defining era-appropriate rules such as two-point conversion availability
and overtime format. An optional ai_behavior.yaml file can customize
CPU AI pace-of-play and strategic decisions for the era.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .overtime_rules import OvertimeRules, OvertimeFormat


@dataclass
class TwoMinuteDrill:
    q2_hurry_when_trailing_by: int = 7
    q4_any_deficit_minutes: float = 2.0
    q4_deficit_9_minutes: float = 3.0
    q4_deficit_4_minutes: float = 2.0
    q4_always_minutes: float = 2.0
    skip_when_leading_by: int = 14


@dataclass
class HurryUp:
    q4_deficit_9_minutes: float = 3.0
    q4_deficit_4_minutes: float = 2.0
    q4_any_minutes: float = 2.0


@dataclass
class ClockKilling:
    q4_any_lead_minutes: float = 3.0
    q4_big_lead_minutes: float = 2.0
    clock_run_on_any_lead: bool = False


@dataclass
class AIStrategic:
    spike_ball_chance: float = 0.10
    timeout_after_incomplete: bool = True
    oob_designation_aggression: float = 0.2
    fourth_down_aggression: float = 0.5


@dataclass
class AIBehavior:
    two_minute_drill: TwoMinuteDrill = field(default_factory=TwoMinuteDrill)
    hurry_up: HurryUp = field(default_factory=HurryUp)
    clock_killing: ClockKilling = field(default_factory=ClockKilling)
    strategic: AIStrategic = field(default_factory=AIStrategic)


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
    ai_behavior: AIBehavior = field(default_factory=AIBehavior)

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
            "ai_behavior": {
                "two_minute_drill": {
                    "q2_hurry_when_trailing_by": self.ai_behavior.two_minute_drill.q2_hurry_when_trailing_by,
                    "q4_any_deficit_minutes": self.ai_behavior.two_minute_drill.q4_any_deficit_minutes,
                    "q4_deficit_9_minutes": self.ai_behavior.two_minute_drill.q4_deficit_9_minutes,
                    "q4_deficit_4_minutes": self.ai_behavior.two_minute_drill.q4_deficit_4_minutes,
                    "q4_always_minutes": self.ai_behavior.two_minute_drill.q4_always_minutes,
                    "skip_when_leading_by": self.ai_behavior.two_minute_drill.skip_when_leading_by,
                },
                "hurry_up": {
                    "q4_deficit_9_minutes": self.ai_behavior.hurry_up.q4_deficit_9_minutes,
                    "q4_deficit_4_minutes": self.ai_behavior.hurry_up.q4_deficit_4_minutes,
                    "q4_any_minutes": self.ai_behavior.hurry_up.q4_any_minutes,
                },
                "clock_killing": {
                    "q4_any_lead_minutes": self.ai_behavior.clock_killing.q4_any_lead_minutes,
                    "q4_big_lead_minutes": self.ai_behavior.clock_killing.q4_big_lead_minutes,
                    "clock_run_on_any_lead": self.ai_behavior.clock_killing.clock_run_on_any_lead,
                },
                "strategic": {
                    "spike_ball_chance": self.ai_behavior.strategic.spike_ball_chance,
                    "timeout_after_incomplete": self.ai_behavior.strategic.timeout_after_incomplete,
                    "oob_designation_aggression": self.ai_behavior.strategic.oob_designation_aggression,
                    "fourth_down_aggression": self.ai_behavior.strategic.fourth_down_aggression,
                },
            },
        }


def _era_ai_behavior(year: int) -> AIBehavior:
    """
    Return era-appropriate default AI behavior for a given year.

    CPU AI pace-of-play and strategic decisions are calibrated to match
    the norms of each football era. These defaults are used when no
    ai_behavior.yaml file exists in the season directory.
    """
    if year < 1985:
        profile = "conservative"
    elif year < 2000:
        profile = "moderate"
    elif year < 2012:
        profile = "aggressive"
    else:
        profile = "very_aggressive"

    if profile == "conservative":
        return AIBehavior(
            two_minute_drill=TwoMinuteDrill(
                q2_hurry_when_trailing_by=7,
                q4_any_deficit_minutes=2.0,
                q4_deficit_9_minutes=3.0,
                q4_deficit_4_minutes=2.0,
                q4_always_minutes=2.0,
                skip_when_leading_by=7,
            ),
            hurry_up=HurryUp(
                q4_deficit_9_minutes=3.0,
                q4_deficit_4_minutes=2.0,
                q4_any_minutes=2.0,
            ),
            clock_killing=ClockKilling(
                q4_any_lead_minutes=3.0,
                q4_big_lead_minutes=2.0,
                clock_run_on_any_lead=False,
            ),
            strategic=AIStrategic(
                spike_ball_chance=0.10,
                timeout_after_incomplete=True,
                oob_designation_aggression=0.2,
                fourth_down_aggression=0.3,
            ),
        )
    elif profile == "moderate":
        return AIBehavior(
            two_minute_drill=TwoMinuteDrill(
                q2_hurry_when_trailing_by=7,
                q4_any_deficit_minutes=2.0,
                q4_deficit_9_minutes=3.0,
                q4_deficit_4_minutes=2.0,
                q4_always_minutes=2.0,
                skip_when_leading_by=10,
            ),
            hurry_up=HurryUp(
                q4_deficit_9_minutes=4.0,
                q4_deficit_4_minutes=3.0,
                q4_any_minutes=2.0,
            ),
            clock_killing=ClockKilling(
                q4_any_lead_minutes=3.0,
                q4_big_lead_minutes=2.0,
                clock_run_on_any_lead=False,
            ),
            strategic=AIStrategic(
                spike_ball_chance=0.15,
                timeout_after_incomplete=True,
                oob_designation_aggression=0.3,
                fourth_down_aggression=0.4,
            ),
        )
    elif profile == "aggressive":
        return AIBehavior(
            two_minute_drill=TwoMinuteDrill(
                q2_hurry_when_trailing_by=7,
                q4_any_deficit_minutes=2.0,
                q4_deficit_9_minutes=4.0,
                q4_deficit_4_minutes=3.0,
                q4_always_minutes=2.0,
                skip_when_leading_by=14,
            ),
            hurry_up=HurryUp(
                q4_deficit_9_minutes=5.0,
                q4_deficit_4_minutes=4.0,
                q4_any_minutes=3.0,
            ),
            clock_killing=ClockKilling(
                q4_any_lead_minutes=4.0,
                q4_big_lead_minutes=2.0,
                clock_run_on_any_lead=True,
            ),
            strategic=AIStrategic(
                spike_ball_chance=0.20,
                timeout_after_incomplete=True,
                oob_designation_aggression=0.5,
                fourth_down_aggression=0.6,
            ),
        )
    else:
        return AIBehavior(
            two_minute_drill=TwoMinuteDrill(
                q2_hurry_when_trailing_by=7,
                q4_any_deficit_minutes=2.0,
                q4_deficit_9_minutes=4.0,
                q4_deficit_4_minutes=3.0,
                q4_always_minutes=3.0,
                skip_when_leading_by=14,
            ),
            hurry_up=HurryUp(
                q4_deficit_9_minutes=5.0,
                q4_deficit_4_minutes=4.0,
                q4_any_minutes=3.0,
            ),
            clock_killing=ClockKilling(
                q4_any_lead_minutes=4.0,
                q4_big_lead_minutes=3.0,
                clock_run_on_any_lead=True,
            ),
            strategic=AIStrategic(
                spike_ball_chance=0.25,
                timeout_after_incomplete=True,
                oob_designation_aggression=0.6,
                fourth_down_aggression=0.7,
            ),
        )


def load_ai_behavior(season_dir: Path, year: int) -> AIBehavior:
    """
    Load AI behavior settings from an optional ai_behavior.yaml file.

    If the file does not exist, era-appropriate defaults are returned.
    Partial files are merged with defaults.

    Args:
        season_dir: Path to the season directory (e.g., seasons/1983)
        year: The season year

    Returns:
        AIBehavior loaded from YAML or era defaults
    """
    season_dir = Path(season_dir)
    yaml_path = season_dir / "ai_behavior.yaml"

    if not yaml_path.exists():
        return _era_ai_behavior(year)

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return _era_ai_behavior(year)

    tmd = TwoMinuteDrill(
        q2_hurry_when_trailing_by=int(data.get("two_minute_drill", {}).get(
            "q2_hurry_when_trailing_by", 7)),
        q4_any_deficit_minutes=float(data.get("two_minute_drill", {}).get(
            "q4_any_deficit_minutes", 2.0)),
        q4_deficit_9_minutes=float(data.get("two_minute_drill", {}).get(
            "q4_deficit_9_minutes", 3.0)),
        q4_deficit_4_minutes=float(data.get("two_minute_drill", {}).get(
            "q4_deficit_4_minutes", 2.0)),
        q4_always_minutes=float(data.get("two_minute_drill", {}).get(
            "q4_always_minutes", 2.0)),
        skip_when_leading_by=int(data.get("two_minute_drill", {}).get(
            "skip_when_leading_by", 14)),
    )

    hur = HurryUp(
        q4_deficit_9_minutes=float(data.get("hurry_up", {}).get(
            "q4_deficit_9_minutes", 3.0)),
        q4_deficit_4_minutes=float(data.get("hurry_up", {}).get(
            "q4_deficit_4_minutes", 2.0)),
        q4_any_minutes=float(data.get("hurry_up", {}).get(
            "q4_any_minutes", 2.0)),
    )

    clk = ClockKilling(
        q4_any_lead_minutes=float(data.get("clock_killing", {}).get(
            "q4_any_lead_minutes", 3.0)),
        q4_big_lead_minutes=float(data.get("clock_killing", {}).get(
            "q4_big_lead_minutes", 2.0)),
        clock_run_on_any_lead=bool(data.get("clock_killing", {}).get(
            "clock_run_on_any_lead", False)),
    )

    stg = AIStrategic(
        spike_ball_chance=float(data.get("strategic", {}).get(
            "spike_ball_chance", 0.10)),
        timeout_after_incomplete=bool(data.get("strategic", {}).get(
            "timeout_after_incomplete", True)),
        oob_designation_aggression=float(data.get("strategic", {}).get(
            "oob_designation_aggression", 0.2)),
        fourth_down_aggression=float(data.get("strategic", {}).get(
            "fourth_down_aggression", 0.5)),
    )

    return AIBehavior(
        two_minute_drill=tmd,
        hurry_up=hur,
        clock_killing=clk,
        strategic=stg,
    )


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

    return _parse_season_rules(data, year, yaml_path, season_dir)


def _parse_season_rules(
    data: dict[str, Any], year: int, yaml_path: Path, season_dir: Path
) -> SeasonRules:
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
    for f in required_ot_fields:
        if f not in ot_data:
            raise ValueError(
                f"Missing required field 'overtime.{f}' in {yaml_path}"
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
        ai_behavior=load_ai_behavior(season_dir, year),
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

    CPU AI behavior defaults are handled by a separate ai_behavior.yaml
    file (optional) in the season directory. Era-appropriate defaults are
    used if the file is absent. See the ai_behavior.yaml schema in the
    paydirt source for documentation.

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

# NOTE: CPU AI behavior can be configured in seasons/{year}/ai_behavior.yaml
# See paydirt/season_rules.py for the schema.
# Era-appropriate defaults are used if ai_behavior.yaml is absent.
"""
