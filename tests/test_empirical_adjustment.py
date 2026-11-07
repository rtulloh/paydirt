"""Tests for separating offense and defense effects in empirical chart data."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from statistics import mean

import pytest

from paydirt.chart_generator import TeamSeasonStats
from paydirt.empirical_adjustment import (
    DefenseProfile,
    adjust_empirical_offense,
    calibrate_defense_stats,
    fit_additive_effects,
)
from paydirt.pfr_play_by_play import EmpiricalPlay


def _play(
    team: str,
    opponent: str,
    result: str,
    number: int,
    chart: str = "line_plunge",
) -> EmpiricalPlay:
    """Build one synthetic matched play without historical season data."""
    return EmpiricalPlay(
        team=team,
        unit="offense",
        chart=chart,
        result=result,
        game_id="synthetic",
        play_number=number,
        detail=f"synthetic result {result}",
        opponent=opponent,
    )


def _numeric_mean(plays: tuple[EmpiricalPlay, ...]) -> float:
    """Return the mean of numeric results in an adjusted synthetic sample."""
    return mean(int(play.result.rstrip("*†")) for play in plays)


def test_additive_model_recovers_balanced_offense_and_defense_effects() -> None:
    observations = (
        ("strong_offense", "weak_defense", 8.0),
        ("strong_offense", "strong_defense", 4.0),
        ("weak_offense", "weak_defense", 4.0),
        ("weak_offense", "strong_defense", 0.0),
    )

    model = fit_additive_effects(observations, shrinkage=0.0)

    assert model.baseline == pytest.approx(4.0)
    assert model.offense_effects == pytest.approx(
        {"strong_offense": 2.0, "weak_offense": -2.0}
    )
    assert model.defense_effects == pytest.approx(
        {"weak_defense": 2.0, "strong_defense": -2.0}
    )
    assert model.predict("strong_offense") == pytest.approx(6.0)
    assert model.predict("weak_offense") == pytest.approx(2.0)


def test_empirical_adjustment_translates_results_to_average_defense() -> None:
    plays = (
        _play("strong_offense", "weak_defense", "8", 1),
        _play("strong_offense", "strong_defense", "4", 2),
        _play("weak_offense", "weak_defense", "4", 3),
        _play("weak_offense", "strong_defense", "0", 4),
    )

    adjusted = adjust_empirical_offense(plays, shrinkage=0.0)

    assert _numeric_mean(adjusted.plays_by_team["strong_offense"]) == 6.0
    assert _numeric_mean(adjusted.plays_by_team["weak_offense"]) == 2.0
    assert adjusted.defense_profiles["weak_defense"].rushing_yards_per_attempt > 4.0
    assert adjusted.defense_profiles["strong_defense"].rushing_yards_per_attempt < 4.0


def test_defense_profile_replaces_schedule_biased_defense_rates() -> None:
    stats = TeamSeasonStats.from_dict(
        {
            "season": 2026,
            "team_name": "Foxes",
            "short_name": "FOX",
            "offense": {
                "rushing": {"attempts": 100, "yards": 400},
                "passing": {"attempts": 100, "completions": 60, "yards": 700},
            },
            "defense": {
                "rushing": {"attempts": 200, "yards": 1000},
                "passing": {
                    "attempts": 300,
                    "completions": 210,
                    "yards": 2400,
                    "interceptions": 3,
                    "sacks": 6,
                    "sack_yards": 42,
                },
            },
        }
    )
    profile = DefenseProfile(
        rushing_yards_per_attempt=3.5,
        passing_yards_per_attempt=6.4,
        completion_rate=0.55,
        interception_rate=0.04,
        sack_rate=0.08,
    )

    calibrated = calibrate_defense_stats(stats, profile)

    assert calibrated.defense.rushing.attempts == 200
    assert calibrated.defense.rushing.yards == 700
    assert calibrated.defense.passing.attempts == 300
    assert calibrated.defense.passing.yards == 1920
    assert calibrated.defense.passing.completions == 165
    assert calibrated.defense.passing.interceptions == 12
    assert calibrated.defense.passing.sacks == 26
    assert calibrated.defense.passing.sack_yards == 182


def test_run_yard_calibration_preserves_symbols_and_non_run_results() -> None:
    """Run calibration should scale yardage without losing result semantics."""
    from paydirt.empirical_adjustment import scale_empirical_run_yards

    plays = (
        _play("alpha", "beta", "8*", 1, chart="line_plunge"),
        _play("alpha", "beta", "F - 6", 2, chart="off_tackle"),
        _play("alpha", "beta", "TD", 3, chart="end_run"),
        _play("alpha", "beta", "12", 4, chart="short_pass"),
    )

    calibrated = scale_empirical_run_yards(plays, multiplier=0.75)

    assert [play.result for play in calibrated] == ["6*", "F - 4", "TD", "12"]
    assert [play.chart for play in calibrated] == [
        "line_plunge",
        "off_tackle",
        "end_run",
        "short_pass",
    ]


@pytest.mark.parametrize("symbol,detail", [
    ("INT 10", "Pass intercepted, returned for 80 yards"),
    ("QT", "Passer sacked for 8 yards"),
    ("QT*", "Passer scrambles for 12 yards"),
    ("BLACK", "Pass incomplete; prior drive for 80 yards"),
    ("OFF 5", "Penalty after a return for 80 yards"),
])
def test_symbolic_primary_results_do_not_supply_narrative_yards(symbol: str, detail: str) -> None:
    from paydirt.empirical_adjustment import _result_yards

    play = replace(_play("A", "X", symbol, 1, "short_pass"), detail=detail)
    assert _result_yards(play) is None


@pytest.mark.parametrize("symbol,expected", [
    ("10*", 10), ("-8", -8), ("F - 6", -6), ("F + 4", 4), ("F", 0),
])
def test_signed_numeric_and_initial_fumble_yards_override_narrative(
    symbol: str, expected: int,
) -> None:
    from paydirt.empirical_adjustment import _result_yards

    play = replace(_play("A", "X", symbol, 1, "quarterback"),
                   detail="Passer sacked for 80 yards; recovered and advanced for 40 yards")
    assert _result_yards(play) == expected


@pytest.mark.parametrize("symbol", ["INT 10", "QT"])
def test_return_or_sack_prose_cannot_shift_primary_completion_yards(symbol: str) -> None:
    def adjusted_with_prose(yards: int):
        plays = []
        for team in ("A", "B"):
            for defense in ("X", "Y"):
                for index in range(20):
                    plays.extend([
                        _play(team, defense, "10", index, "short_pass"),
                        replace(_play(team, defense, symbol, 100 + index, "short_pass"),
                                detail=f"Other procedure for {yards if defense == 'Y' else 0} yards"),
                    ])
        return adjust_empirical_offense(plays, shrinkage=24)

    control = adjusted_with_prose(0)
    changed = adjusted_with_prose(80)
    for team in ("A", "B"):
        expected = Counter({"10": 40, symbol: 40})
        assert Counter(play.result for play in control.plays_by_team[team]) == expected
        assert Counter(play.result for play in changed.plays_by_team[team]) == expected
    assert changed.defense_profiles == control.defense_profiles
    for profile in changed.defense_profiles.values():
        assert profile.passing_yards_per_attempt == (5 if symbol.startswith("INT") else 10)


def test_touchdown_prose_does_not_replace_normalized_source_gain() -> None:
    from paydirt.empirical_adjustment import _result_yards

    touchdown = _play("A", "X", "TD", 1, "short_pass")
    assert _result_yards(touchdown) is None
    observed = replace(touchdown, result="25", detail="Pass complete for 25 yards, touchdown")
    assert _result_yards(observed) == 25
    assert _result_yards(replace(observed, result="TD")) is None


@pytest.mark.parametrize("symbol", ["TD", "B", "B*"])
@pytest.mark.parametrize("detail", [
    "Pass complete, touchdown; defender returned for 80 yards on another play",
    "Recovered and advanced for 80 yards, touchdown",
    "Pass complete for 25 yards, touchdown; PENALTY for 80 yards",
])
def test_symbolic_touchdown_or_breakaway_has_no_trusted_initial_gain(
    symbol: str, detail: str,
) -> None:
    from paydirt.empirical_adjustment import _result_yards

    play = replace(_play("A", "X", symbol, 1, "short_pass"), detail=detail)
    assert _result_yards(play) is None


@pytest.mark.parametrize("symbol", ["TD", "B", "B*"])
def test_opponent_adjustment_rejects_unknown_retained_primary_gain(symbol: str) -> None:
    play = replace(_play("A", "X", symbol, 1, "short_pass"),
                   detail="Pass complete, touchdown; return for 80 yards")
    with pytest.raises(ValueError, match="initial gain"):
        adjust_empirical_offense([play])


def test_defense_passing_yards_use_retained_attempt_categories() -> None:
    plays = [
        _play("A", "X", "12", 1, "short_pass"),
        _play("A", "X", "F + 4", 2, "short_pass"),
        replace(_play("A", "X", "INT 10", 3, "short_pass"), detail="Return for 80 yards"),
        replace(_play("A", "X", "BLACK", 4, "short_pass"), detail="Incomplete for 80 yards"),
        replace(_play("A", "X", "QT", 5, "short_pass"), detail="Sacked for 8 yards"),
        _play("A", "X", "OFF 5", 6, "short_pass"),
    ]
    profile = adjust_empirical_offense(plays).defense_profiles["X"]
    assert profile.passing_yards_per_attempt == 4
    assert profile.completion_rate == .5
    assert profile.interception_rate == .25
    assert profile.sack_rate == .2


@pytest.mark.parametrize("ordering", ["chronological", "reversed", "rotated", "interleaved"])
def test_reduced_category_sampling_represents_same_source_multiset(ordering: str) -> None:
    from paydirt.empirical_adjustment import _adjust_chart

    gains = [0] * 20 + [80] * 20
    if ordering == "reversed":
        gains.reverse()
    elif ordering == "rotated":
        gains = gains[7:] + gains[:7]
    elif ordering == "interleaved":
        gains = [gain for pair in zip(gains[:20], gains[20:]) for gain in pair]
    plays = [_play("A", "X", str(gain), index, "short_pass")
             for index, gain in enumerate(gains)]
    plays.extend(_play("B", "X", "BLACK", 100 + index, "short_pass") for index in range(40))
    adjusted = _adjust_chart(plays, 24)
    # Shrinkage allocates 32 numeric results and eight incompletions to A.
    # A representative reduction retains each half of the bimodal population.
    assert Counter(play.result for play in adjusted["A"]) == {"0": 16, "80": 16, "BLACK": 8}
    assert len(adjusted["A"]) == len(adjusted["B"]) == 40
    borrowed = Counter(play.result for play in adjusted["B"])
    assert borrowed["BLACK"] == 33
    assert borrowed["0"] + borrowed["80"] == 7
    assert abs(borrowed["0"] - borrowed["80"]) == 1


def test_representative_category_sampling_preserves_flat_control_and_markers() -> None:
    from paydirt.empirical_adjustment import _adjust_chart

    plays = [_play("A", "X", "10*", i, "short_pass") for i in range(40)]
    plays.extend(_play("B", "X", "BLACK", 100 + i, "short_pass") for i in range(40))
    adjusted = _adjust_chart(plays, 24)
    assert Counter(play.result for play in adjusted["A"]) == {"10*": 32, "BLACK": 8}
    assert Counter(play.result for play in adjusted["B"]) == {"10*": 7, "BLACK": 33}



def test_adjusted_sampling_reports_population_and_conditional_tail_changes() -> None:
    plays = [_play("A", "X", str(gain), i, "short_pass")
             for i, gain in enumerate([0] * 20 + [80] * 20)]
    plays.extend(_play("B", "X", "BLACK", 100 + i, "short_pass") for i in range(40))
    adjusted = adjust_empirical_offense(plays)
    report = adjusted.sampling_diagnostics["A"]["short_pass"]["numeric"]
    assert report["method"] == "sorted_midpoint_quantiles_v1"
    assert report["source_count"] == 40 and report["selected_count"] == 32
    assert report["source_result_counts"] == {"0": 20, "80": 20}
    assert report["selected_result_counts"] == {"0": 16, "80": 16}
    assert report["source_gain_mean"] == report["selected_gain_mean"] == 40
    assert report["omitted_results"] == []



def test_representative_sampling_balances_repeated_support_without_losing_flags() -> None:
    from paydirt.empirical_adjustment import _representative_outcomes

    support = [_play("A", "X", value, i, "short_pass")
               for i, value in enumerate(["0", "10*", "80"])]
    selected = _representative_outcomes(support, 250)
    counts = Counter(play.result for play in selected)
    assert len(selected) == 250 and set(counts) == {"0", "10*", "80"}
    assert max(counts.values()) - min(counts.values()) <= 1
    assert counts == Counter(play.result for play in _representative_outcomes(support[::-1], 250))


def test_rare_tail_omission_is_disclosed_without_inflating_source_probability() -> None:
    from paydirt.empirical_adjustment import _representative_outcomes, _sampling_evidence

    support = [_play("A", "X", value, i, "short_pass")
               for i, value in enumerate(["0"] * 99 + ["80*"])]
    selected = _representative_outcomes(support, 1)
    assert [play.result for play in selected] == ["0"]
    evidence = _sampling_evidence(support, selected)
    assert evidence["omitted_results"] == ["80*"]
    assert evidence["source_result_counts"]["80*"] == 1
    assert evidence["source_gain_range"] == [0, 80]
    assert evidence["selected_gain_range"] == [0, 0]


def test_representative_sampling_bounds_conditional_cdf_error() -> None:
    from paydirt.empirical_adjustment import _representative_outcomes

    support = [_play("A", "X", str(i), i, "short_pass") for i in range(100)]
    selected = _representative_outcomes(support, 7)
    for threshold in range(100):
        source_cdf = sum(int(play.result) <= threshold for play in support) / len(support)
        selected_cdf = sum(int(play.result) <= threshold for play in selected) / len(selected)
        assert abs(source_cdf - selected_cdf) <= 1 / len(selected)


@pytest.mark.parametrize("original,proposed,expected", [
    ("-1", 0, "SACK 0"), ("-1*", 6, "SACK 0*"),
    ("0", -6, "0"), ("1*", -6, "0*"),
    ("F", 6, "F"), ("F - 1", 6, "F"), ("F + 1", -6, "F + 1"),
])
def test_qb_time_yard_adjustment_preserves_sack_or_scramble_class(
    original: str, proposed: float, expected: str,
) -> None:
    from paydirt.empirical_adjustment import _format_adjusted_result

    assert _format_adjusted_result(_play("A", "X", original, 1, "qb_time"), proposed) == expected


def test_opposing_qb_time_gains_do_not_erase_sacks_during_adjustment() -> None:
    from paydirt.empirical_adjustment import _adjust_chart

    plays = [_play(team, defense, gain, i, "qb_time")
             for team in ("A", "B") for defense, gain in (("X", "-1"), ("Y", "1"))
             for i in range(20)]
    adjusted = _adjust_chart(plays, 24)
    for team in ("A", "B"):
        # Typed zero-yard sacks keep the original 20/20 event-class split.
        assert Counter(play.result for play in adjusted[team]) == {"SACK 0": 20, "0": 20}


def test_primary_fumble_yard_adjustment_is_not_a_qb_sack_boundary() -> None:
    from paydirt.empirical_adjustment import _format_adjusted_result

    primary = _play("A", "X", "F + 1", 1, "short_pass")
    assert _format_adjusted_result(primary, -6) == "F - 6"



def test_qb_boundary_constraints_disclose_proposals_and_class_counts() -> None:
    plays = [_play(team, defense, gain, i, "qb_time")
             for team in ("A", "B") for defense, gain in (("X", "-1"), ("Y", "1"))
             for i in range(20)]
    report = adjust_empirical_offense(plays).sampling_diagnostics["A"]["qb_time"]["numeric"]
    boundary = report["qb_class_adjustment"]
    assert boundary["source_class_counts"] == {"sack": 20, "scramble": 20}
    assert boundary["adjusted_class_counts"] == boundary["selected_class_counts"] == {"sack": 20, "scramble": 20}
    assert boundary["class_boundary_clamps"] == 0
    assert boundary["actual_gain_range"] == [0, 0]
    assert len(boundary["proposals"]) == 2
    assert all(set(row) == {"source_class", "source_gain", "unbounded_gain", "actual_gain", "count"}
               for row in boundary["proposals"])
