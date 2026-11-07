"""A known zero-yard sack is distinct from a scramble or a real fumble."""

from fractions import Fraction
from unittest.mock import patch

import pytest

from paydirt.chart_audit import _exact_team_mechanics
from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.chart_generator import (
    EmpiricalChartData,
    StatLine,
    TeamSeasonStats,
    _empirical_pressure_rate,
    generate_team_charts,
    supported_generated_cell,
)
from paydirt.chart_loader import load_team_chart
from paydirt.chart_tactics_audit import controlled_offense, resolved_outcome_distribution
from paydirt.empirical_adjustment import _format_adjusted_result, _qb_event_class
from paydirt.game_engine import PaydirtGameEngine
from paydirt.nflverse_play_by_play import classify_nflverse_rows
from paydirt.pfr_play_by_play import EmpiricalPlay
from paydirt.play_resolver import (
    DefenseType,
    PlayType,
    ResultType,
    resolve_play,
    resolve_play_with_penalties,
)


def _charts(token: str):
    offense, defender = controlled_offense("QT"), controlled_offense("0")
    offense.peripheral.short_name = "OFF"
    defender.peripheral.short_name = "DEF"
    offense.offense.qb_time = dict.fromkeys(range(10, 40), token)
    defender.defense.modifiers = {(formation, row): dict.fromkeys(range(1, 10), "0")
                                  for formation in "ABCDEF" for row in range(1, 6)}
    return offense, defender


@pytest.mark.parametrize("penalties", [False, True])
@pytest.mark.parametrize("token,kind,yards,oob", [
    ("SACK 0", ResultType.SACK, 0, False), ("SACK 0*", ResultType.SACK, 0, True),
    ("0", ResultType.QB_SCRAMBLE, 0, False), ("0*", ResultType.QB_SCRAMBLE, 0, True),
    ("-4", ResultType.SACK, -4, False), ("4", ResultType.QB_SCRAMBLE, 4, False),
    ("F", ResultType.FUMBLE, 0, False),
])
def test_both_qt_resolver_routes_preserve_zero_sack_class_and_dice(
    penalties: bool, token: str, kind: ResultType, yards: int, oob: bool,
) -> None:
    offense, defender = _charts(token)
    rolls = [(10, "primary"), (24, "QT")]
    if penalties and token == "F":
        rolls.append((10, "recovery"))
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls), \
         patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)), \
         patch("paydirt.play_resolver.random.randint", side_effect=AssertionError("random fallback")):
        output = (resolve_play_with_penalties if penalties else resolve_play)(
            offense, defender, PlayType.SHORT_PASS, DefenseType.STANDARD,
        )
    result = output.play_result if penalties else output
    assert (result.result_type, result.yards, result.out_of_bounds) == (kind, yards, oob)
    assert result.dice_roll == 10 and result.qb_scramble_dice == 24
    assert result.qb_scramble_yards == yards
    if kind == ResultType.SACK:
        assert "SACKED" in result.description
        assert not result.turnover and not result.fumble_resolved


@pytest.mark.parametrize("position", [1, 40, 99])
@pytest.mark.parametrize("token,sacks,rushes", [("SACK 0", 1, 0), ("0", 0, 1)])
def test_core_and_observer_credit_zero_sack_without_fumble_or_attempt(
    position: int, token: str, sacks: int, rushes: int,
) -> None:
    offense, defender = _charts(token)
    engine = PaydirtGameEngine(offense, defender)
    engine.state.is_home_possession = True
    engine.state.ball_position = position
    engine.state.quarter = 2
    engine.state.time_remaining = 300
    observer = EngineCalibrationObserver()
    observer.on_decision(engine, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(10, "primary"), (24, "QT")]), \
         patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 0, 1)), \
         patch("paydirt.play_resolver.random.randint", side_effect=AssertionError("random fallback")):
        outcome = engine.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    observer.on_result(engine, outcome)
    observer.finalize_game(engine)
    report = observer.report()["teams"]["OFF"]
    assert report["sacks"] == sacks and report["rushing_attempts"] == rushes
    assert report["sack_yards"] == report["pass_attempts"] == report["passing_yards"] == 0
    assert report["fumbles_lost"] == report["turnovers"] == report["rushing_yards"] == 0
    assert engine.state.down == 2 and engine.state.ball_position == position
    assert engine.state.is_home_possession and not outcome.turnover
    assert 0 < engine.state.time_remaining < 300


@pytest.mark.parametrize("token", ["SACK 0", "SACK 0*"])
def test_exact_audits_resolve_explicit_zero_sack_without_fallback(token: str) -> None:
    offense, defender = _charts(token)
    exact = _exact_team_mechanics(offense, [defender])
    assert exact["plays"]["short_pass/A"]["probabilities"] == {"sack:0": 1.0}
    assert exact["plays"]["short_pass/A"]["secondary_fallback_probability"] == 0
    resolved = resolved_outcome_distribution(offense, defender.defense, PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert sum(resolved.values()) == Fraction(1)
    assert {(outcome.kind, outcome.yards) for outcome in resolved} == {(ResultType.SACK.value, 0)}


@pytest.mark.parametrize("token", ["SACK 0", "SACK 0*"])
def test_pressure_model_counts_zero_sack_as_conditional_sack(token: str) -> None:
    stats = StatLine(attempts=100, sacks=10)
    baseline = dict.fromkeys(range(10, 40), "0")
    zero = _empirical_pressure_rate(stats, "short_pass", baseline, dict.fromkeys(range(10, 40), token))
    negative = _empirical_pressure_rate(stats, "short_pass", baseline, dict.fromkeys(range(10, 40), "-4"))
    assert 0 < zero < 1 and zero == pytest.approx(negative)


@pytest.mark.parametrize("column", ["line_plunge", "short_pass", "breakaway"])
def test_explicit_zero_sack_is_not_a_primary_or_breakaway_token(column: str) -> None:
    assert not supported_generated_cell("offense", column, "SACK 0")
    with pytest.raises(ValueError, match="Invalid empirical result"):
        EmpiricalChartData.from_rows([{"unit": "offense", "chart": column, "result": "SACK 0"}])


def test_generation_and_loader_preserve_explicit_zero_sack_token_and_flag(tmp_path) -> None:
    stats = TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Foxes", "short_name": "FOX",
        "offense": {"rushing": {"attempts": 100}, "passing": {"attempts": 100}},
        "defense": {"rushing": {"attempts": 100}, "passing": {"attempts": 100}},
    })
    empirical = EmpiricalChartData.from_rows([
        {"unit": "offense", "chart": "qb_time", "result": token}
        for token in ["SACK 0"] * 75 + ["SACK 0*"] * 25
    ])
    generate_team_charts(stats, tmp_path, empirical=empirical)
    loaded = load_team_chart(tmp_path)
    assert set(loaded.offense.qb_time.values()) == {"SACK 0", "SACK 0*"}
    assert all(supported_generated_cell("offense", "qb_time", cell) for cell in loaded.offense.qb_time.values())


def test_source_known_zero_sack_is_not_a_scramble_or_fumble() -> None:
    season = classify_nflverse_rows([{
        "season_type": "REG", "two_point_attempt": 0, "game_id": "syn", "play_id": 1,
        "posteam": "A", "defteam": "B", "play_type": "pass", "sack": 1, "yards_gained": 0,
    }])
    assert [(play.chart, play.result) for play in season.plays] == [("short_pass", "QT"), ("qb_time", "SACK 0")]
    assert season.event_counts["A"]["sacks"] == 1 and not season.fumbles


@pytest.mark.parametrize("original,proposed,expected", [
    ("-1", 0, "SACK 0"), ("-1*", 6, "SACK 0*"),
    ("SACK 0", -6, "-6"), ("SACK 0*", 6, "SACK 0*"),
])
def test_adjusted_sack_severity_can_reach_zero_without_an_invented_loss(
    original: str, proposed: float, expected: str,
) -> None:
    play = EmpiricalPlay("A", "offense", "qb_time", original, "syn", 1, "", "X")
    adjusted = _format_adjusted_result(play, proposed)
    assert adjusted == expected
    assert _qb_event_class(EmpiricalPlay("A", "offense", "qb_time", adjusted, "syn", 1, "", "X")) == "sack"
