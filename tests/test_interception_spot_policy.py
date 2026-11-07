"""Synthetic source and generator regressions for play-specific INT locations."""

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    _generate_offense,
    generate_team_charts,
)
from paydirt.nflverse_play_by_play import classify_nflverse_rows
from paydirt.pfr_play_by_play import PfrGame, PfrPlay, _pass_chart, classify_pfr_game
from paydirt.play_resolver import chart_roll_weights
from tests.test_chart_generator import _synthetic_stats

FALLBACKS = {"screen": 5, "short_pass": 5, "medium_pass": 12,
             "long_pass": 20, "te_short_long": 8}


def _play(detail: str) -> PfrPlay:
    return PfrPlay("synthetic-2026", 1, 1, "10:00", 1, 10, "FOX 20", 0, 0,
                   detail, ("PassPa00", "DefeDa00"))


@pytest.mark.parametrize(("depth", "family"), [
    (0, "screen"), (1, "short_pass"), (9, "short_pass"),
    (10, "medium_pass"), (19, "medium_pass"), (20, "long_pass"), (44, "long_pass"),
])
def test_known_interception_depth_never_uses_completion_yac_weights(depth: int, family: str) -> None:
    play = _play("Pat Passer pass intercepted by Dan Defender and returned for 5 yards")
    assert {_pass_chart(play, depth, seed)[0] for seed in range(1000)} == {family}


def test_explicit_screen_and_completion_yac_are_preserved() -> None:
    screen = _play("Pat Passer screen pass intercepted by Dan Defender")
    assert _pass_chart(screen, 44, 8306) == ("screen", False)
    completion = _play("Pat Passer pass complete for 44 yards")
    assert "screen" in {_pass_chart(completion, 44, seed)[0] for seed in range(1000)}


def _game(play: PfrPlay) -> PfrGame:
    return PfrGame(play.game_id, "FOX", "OWL", {"PassPa00": "FOX", "DefeDa00": "OWL"},
                   {"PassPa00": "QB", "DefeDa00": "DB"},
                   {"PassPa00": "Pat Passer", "DefeDa00": "Dan Defender"}, (play,))


def test_classified_int44_and_return_stay_on_their_respective_charts() -> None:
    play = _play("Pat Passer pass intercepted by Dan Defender at OWL36 and returned for 5 yards")
    for seed in range(100):
        classified = classify_pfr_game(_game(play), seed=seed)
        assert [(p.chart, p.result) for p in classified.plays] == [
            ("interception_return", "5"), ("long_pass", "INT 44"),
        ]
        assert classified.event_counts["FOX"]["interceptions"] == 1


@pytest.mark.parametrize("seed", range(10))
def test_missing_pfr_interception_depth_uses_selected_call_fallback(seed: int) -> None:
    play = _play("Pat Passer pass intercepted by Dan Defender and returned for 5 yards")
    classified = classify_pfr_game(_game(play), seed=seed)
    offense = [p for p in classified.plays if p.unit == "offense"]
    assert len(offense) == 1
    assert offense[0].result == f"INT {FALLBACKS[offense[0].chart]}"


@pytest.mark.parametrize(("description", "pass_length", "to_go", "family"), [
    ("Screen pass intercepted", "", 10, "screen"),
    ("Pass intercepted", "short", 10, "short_pass"),
    ("Pass intercepted", "", 15, "medium_pass"),
    ("Pass intercepted", "deep", 10, "long_pass"),
])
def test_missing_nflverse_depth_uses_call_fallback(description: str, pass_length: str,
                                                to_go: int, family: str) -> None:
    classified = classify_nflverse_rows([{
        "season_type": "REG", "game_id": "synthetic-2026", "play_id": 1,
        "posteam": "FOX", "defteam": "OWL", "play_type": "pass",
        "desc": description, "pass_attempt": 1, "interception": 1,
        "pass_length": pass_length, "ydstogo": to_go, "return_yards": 5,
    }])
    offense = [p for p in classified.plays if p.unit == "offense"]
    assert [(p.chart, p.result) for p in offense] == [(family, f"INT {FALLBACKS[family]}")]


@pytest.fixture(scope="module")
def aggregate_int_support() -> Mapping[str, frozenset[str]]:
    stats = _synthetic_stats()
    stats = replace(stats, offense=replace(stats.offense,
                    passing=replace(stats.offense.passing, interceptions=45)))
    supports: dict[str, set[str]] = {family: set() for family in FALLBACKS}
    for seed in range(30):
        columns = _generate_offense(stats, seed)
        for family in FALLBACKS:
            supports[family].update(value for value in columns[family].values()
                                    if value.startswith("INT"))
    return MappingProxyType({name: frozenset(values) for name, values in supports.items()})


@pytest.mark.parametrize(("family", "depth"), FALLBACKS.items())
def test_aggregate_int_support_is_specific_to_each_pass_call(
    aggregate_int_support: Mapping[str, frozenset[str]], family: str, depth: int,
) -> None:
    assert aggregate_int_support[family] == {f"INT {depth}"}


@pytest.mark.parametrize(("family", "depth"), FALLBACKS.items())
def test_sparse_calibration_keeps_interception_mass_with_call_fallback(
    tmp_path: Path, family: str, depth: int,
) -> None:
    stats = _synthetic_stats()
    stats = replace(stats, offense=replace(stats.offense,
                    passing=replace(stats.offense.passing, interceptions=0)))
    column = generate_team_charts(
        stats, tmp_path / family, empirical=EmpiricalChartData(offense={family: ("4",) * 1000}),
        calibrate_empirical_pass_events=True,
        empirical_pass_calibration=EmpiricalPassCalibration(interception_rate_adjustment=.02),
    ).offense[family]
    weights = chart_roll_weights()
    assert {value for value in column.values() if value.startswith("INT")} == {f"INT {depth}"}
    assert sum(weights[roll] for roll, cell in column.items() if cell.startswith("INT")) / 216 == pytest.approx(.02, abs=.01)


@pytest.mark.parametrize("calibrated", [False, True])
def test_supported_explicit_screen_depth_is_not_capped(tmp_path: Path, calibrated: bool) -> None:
    empirical = EmpiricalChartData.from_rows([
        {"unit": "offense", "chart": "screen", "result": "INT 44",
         "detail": "Pat Passer screen pass intercepted by Dan Defender at OWL36"}
        for _ in range(20)
    ] + [{"unit": "offense", "chart": "screen", "result": "4"} for _ in range(980)])
    stats = _synthetic_stats()
    # No aggregate interceptions: source support supplies the calibrated depth.
    stats = replace(stats, offense=replace(stats.offense,
                    passing=replace(stats.offense.passing, interceptions=0)))
    charts = generate_team_charts(stats, tmp_path / str(calibrated), empirical=empirical,
        calibrate_empirical_pass_events=calibrated,
        empirical_pass_calibration=EmpiricalPassCalibration(interception_rate_adjustment=.02))
    assert "INT 44" in charts.offense["screen"].values()


@pytest.mark.parametrize("unit", ["offense", "defense"])
def test_generator_rejects_cross_play_interception_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unit: str,
) -> None:
    from paydirt import chart_generator

    producer = getattr(chart_generator, f"_generate_{unit}")

    def pooled(*args: Any, **kwargs: Any) -> Any:
        columns = producer(*args, **kwargs)
        if unit == "offense":
            columns["screen"][10] = "INT 44"
        else:
            columns[("A", 5)][5] = "INT 44"
        return columns

    monkeypatch.setattr(chart_generator, f"_generate_{unit}", pooled)
    with pytest.raises(ValueError, match="interception spot support"):
        generate_team_charts(_synthetic_stats(), tmp_path / unit)
