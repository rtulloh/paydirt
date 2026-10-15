"""Public sample teams with explicit, synthetic rule/scenario configuration."""

from pathlib import Path

from paydirt.chart_loader import load_team_chart
from paydirt.game_engine import PaydirtGameEngine
from paydirt.season_rules import OvertimeConfig


def make_sample_game(home_label: str = "HOME", away_label: str = "AWAY") -> PaydirtGameEngine:
    """Create fresh public charts with traditional sudden-death test rules.

    Labels are display-only scenario inputs, not historical chart data. Tests
    must explicitly set any chart cells their deterministic scenarios require.
    """
    season = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    home = load_team_chart(str(season / "Thunderhawks"))
    away = load_team_chart(str(season / "Ironclads"))
    home.peripheral.short_name = home_label
    away.peripheral.short_name = away_label
    engine = PaydirtGameEngine(home, away)
    engine.season_rules.two_point_conversion = False
    engine.season_rules.overtime = OvertimeConfig(
        enabled=True, format="sudden_death", period_length_minutes=15,
        max_periods_regular=1, max_periods_playoff=0,
        can_end_in_tie_regular=True, can_end_in_tie_playoff=False,
        coin_toss_winner_receives=True,
    )
    return engine
