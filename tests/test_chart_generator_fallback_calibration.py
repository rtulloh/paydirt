"""Run calibration covers modeled fallback without recalibrating empirical data."""
import re
from collections import Counter
from copy import deepcopy

import pytest

from paydirt.chart_generator import EmpiricalChartData, generate_team_charts, weighted_chart_mean
from paydirt.play_resolver import chart_roll_weights
from tests.test_chart_generator import _synthetic_stats


def weighted_tokens(column):
    counts = Counter()
    for roll, token in column.items():
        counts[token] += chart_roll_weights()[roll]
    return counts


def test_fallback_run_calibration_responds_and_preserves_other_units(tmp_path):
    stats = _synthetic_stats()
    baseline = generate_team_charts(stats, tmp_path / "neutral")
    calibrated = generate_team_charts(stats, tmp_path / "scaled", fallback_run_yard_multiplier=1.15)
    for family in ("draw", "line_plunge", "off_tackle", "end_run"):
        assert weighted_chart_mean(calibrated.offense[family]) > weighted_chart_mean(baseline.offense[family])
    for family in ("screen", "short_pass", "medium_pass", "long_pass", "te_short_long", "breakaway", "qb_time"):
        assert weighted_tokens(calibrated.offense[family]) == weighted_tokens(baseline.offense[family])
    assert calibrated.defense == baseline.defense
    assert calibrated.special_teams == baseline.special_teams


def test_neutral_fallback_profile_is_byte_identical(tmp_path):
    stats = _synthetic_stats()
    first = generate_team_charts(stats, tmp_path / "default")
    second = generate_team_charts(stats, tmp_path / "explicit", fallback_run_yard_multiplier=1.0)
    assert first == second
    for file in ("offense.csv", "defense.csv", "special.csv", "team.yaml"):
        assert (tmp_path / "default" / file).read_bytes() == (tmp_path / "explicit" / file).read_bytes()


def test_existing_empirical_runs_are_not_scaled_twice(tmp_path):
    empirical = EmpiricalChartData.from_rows([
        {"unit": "offense", "chart": family, "result": result}
        for family in ("line_plunge", "off_tackle", "end_run")
        for result in ("6", "-3", "0", "F + 2", "F - 2", "OFF 5", "B") * 4
    ])
    original = deepcopy(empirical)
    baseline = generate_team_charts(_synthetic_stats(), tmp_path / "base", empirical=empirical)
    scaled = generate_team_charts(_synthetic_stats(), tmp_path / "scaled", empirical=empirical,
                                  fallback_run_yard_multiplier=1.15)
    for family in ("line_plunge", "off_tackle", "end_run", "breakaway", "qb_time"):
        assert weighted_tokens(scaled.offense[family]) == weighted_tokens(baseline.offense[family])
    assert weighted_chart_mean(scaled.offense["draw"]) > weighted_chart_mean(baseline.offense["draw"])
    assert empirical == original


@pytest.mark.parametrize("factor", [0, -1, True, float("inf"), float("nan")])
def test_invalid_fallback_multiplier_fails(tmp_path, factor):
    with pytest.raises((TypeError, ValueError)):
        generate_team_charts(_synthetic_stats(), tmp_path, fallback_run_yard_multiplier=factor)


def test_fallback_scaling_preserves_tokens_flags_and_loss_semantics(tmp_path, monkeypatch):
    from paydirt import chart_generator

    original_generate = chart_generator._generate_offense
    def controlled(stats, seed):
        columns = original_generate(stats, seed)
        values = ("-10", "-1*", "0", "8†", "18", "B", "F", "F - 2", "F + 2", "OFF 5")
        columns["draw"] = {roll: values[index % len(values)] for index, roll in enumerate(columns["draw"])}
        return columns
    monkeypatch.setattr(chart_generator, "_generate_offense", controlled)
    baseline = generate_team_charts(_synthetic_stats(), tmp_path / "base")
    scaled = generate_team_charts(_synthetic_stats(), tmp_path / "scaled", fallback_run_yard_multiplier=1.15)
    # Layout can move cells; compare physical weighted token mass, not row positions.
    def masses(column):
        counts = Counter()
        for roll, token in column.items():
            if re.fullmatch(r"[+-]?\d+[*†]?", token):
                value = int(token.rstrip("*†"))
                key = ("numeric", "loss" if value < 0 else "gain" if value > 0 else "zero", token[-1] if token[-1] in "*†" else "")
            elif token.startswith("F"):
                key = ("fumble", "loss" if "-" in token else "gain" if "+" in token else "zero")
            else:
                key = ("protected", token)
            counts[key] += chart_roll_weights()[roll]
        return counts
    assert masses(scaled.offense["draw"]) == masses(baseline.offense["draw"])
    assert all(int(token.rstrip("*†")) <= 18 for token in scaled.offense["draw"].values()
               if re.fullmatch(r"[+-]?\d+[*†]?", token))
