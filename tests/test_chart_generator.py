import json
import re
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt import chart_generator
from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    generate_team_charts,
    main,
    weighted_chart_mean,
    weighted_chart_rate,
)
from paydirt.chart_layout import PRIMARY_COLUMNS
from paydirt.chart_loader import load_team_chart
from paydirt.play_resolver import (
    chart_roll_weights,
    defense_subrow_weights,
    parse_result_string,
)


def _synthetic_stats() -> TeamSeasonStats:
    return TeamSeasonStats.from_dict(
        {
            "season": 2026,
            "team_name": "Synthetic Foxes",
            "short_name": "FOX '26",
            "offense": {
                "rushing": {
                    "attempts": 480,
                    "yards": 2160,
                    "touchdowns": 18,
                    "fumbles": 12,
                    "fumbles_lost": 6,
                },
                "passing": {
                    "attempts": 520,
                    "completions": 338,
                    "yards": 4056,
                    "touchdowns": 30,
                    "interceptions": 12,
                    "sacks": 32,
                    "sack_yards": 220,
                },
            },
            "defense": {
                "rushing": {
                    "attempts": 440,
                    "yards": 1760,
                    "touchdowns": 12,
                },
                "passing": {
                    "attempts": 560,
                    "completions": 336,
                    "yards": 3920,
                    "touchdowns": 24,
                    "interceptions": 16,
                    "sacks": 40,
                    "sack_yards": 280,
                },
            },
            "special_teams": {
                "kickoff": {"attempts": 80, "yards": 4960},
                "kickoff_return": {"attempts": 54, "yards": 1188},
                "punt": {"attempts": 72, "yards": 3024, "blocked": 1},
                "punt_return": {"attempts": 38, "yards": 380},
                "interception_return": {"attempts": 16, "yards": 192},
                "field_goal": {"attempts": 32, "made": 25, "long": 52},
                "extra_point": {"attempts": 30, "made": 29},
            },
        }
    )


def test_supplied_out_of_bounds_rates_mark_aggregate_numeric_results(tmp_path) -> None:
    """Aggregate charts should preserve supplied run and pass clock-stop rates."""
    data = _synthetic_stats().to_dict()
    data["offense"]["rushing"]["out_of_bounds"] = 38
    data["offense"]["passing"]["out_of_bounds"] = 66
    stats = TeamSeasonStats.from_dict(data)

    generated = generate_team_charts(stats, tmp_path / "Foxes", seed=8306)
    roll_weights = chart_roll_weights()
    total_weight = sum(roll_weights.values())

    def marked_rate(
        column: dict[int, str], excluded_prefixes: tuple[str, ...]
    ) -> float:
        marked_mass = sum(
            weight
            for roll, weight in roll_weights.items()
            if re.fullmatch(r"[+-]?\d+\*", column[roll])
        )
        penalty_mass = sum(
            weight
            for roll, weight in roll_weights.items()
            if column[roll].startswith(excluded_prefixes)
        )
        return marked_mass / (total_weight - penalty_mass)

    assert stats.offense.rushing.out_of_bounds == 38
    assert stats.offense.passing.out_of_bounds == 66
    assert marked_rate(
        generated.offense["line_plunge"], ("OFF", "DEF", "PI")
    ) == pytest.approx(38 / 480, abs=0.02)
    assert marked_rate(
        generated.offense["short_pass"], ("OFF", "DEF", "PI", "QT")
    ) == pytest.approx(66 / 520, abs=0.02)


def test_team_season_stats_round_trip() -> None:
    stats = _synthetic_stats()

    restored = TeamSeasonStats.from_dict(json.loads(json.dumps(stats.to_dict())))

    assert restored == stats
    assert restored.offense.rushing.average == 4.5
    assert restored.offense.passing.completion_rate == 0.65


def test_aggregate_run_columns_cap_direct_gains_before_breakaway(tmp_path) -> None:
    """Aggregate fallbacks should reserve gains above 18 yards for B."""
    stats = _synthetic_stats()
    stats = replace(
        stats,
        offense=replace(
            stats.offense,
            rushing=replace(stats.offense.rushing, yards=4800),
        ),
    )

    generated = generate_team_charts(stats, tmp_path / "Foxes", seed=8306)

    for name in ("line_plunge", "off_tackle", "end_run", "draw"):
        direct_yards = [
            int(match.group(1))
            for result in generated.offense[name].values()
            if (match := re.fullmatch(r"([+-]?\d+)[*†]?", result))
        ]
        assert max(direct_yards) <= 18


def test_generated_numeric_columns_track_season_averages(tmp_path) -> None:
    stats = _synthetic_stats()

    generated = generate_team_charts(stats, tmp_path / "Foxes", seed=8306)

    run_means = {
        name: weighted_chart_mean(generated.offense[name])
        for name in ("line_plunge", "off_tackle", "end_run", "draw")
    }
    assert run_means["line_plunge"] == pytest.approx(4.4, abs=0.2)
    assert run_means["off_tackle"] == pytest.approx(4.4, abs=0.2)
    assert run_means["end_run"] <= run_means["line_plunge"] - 0.5
    assert run_means["draw"] <= run_means["line_plunge"] - 0.25

    pass_means = {
        name: weighted_chart_mean(generated.offense[name])
        for name in ("screen", "short_pass", "medium_pass", "long_pass")
    }
    assert abs(pass_means["screen"] - pass_means["short_pass"]) <= 2.0
    assert pass_means["long_pass"] >= pass_means["medium_pass"] * 2
    assert weighted_chart_mean(generated.offense["qb_time"]) == pytest.approx(-3.2, abs=0.8)
    assert weighted_chart_mean(generated.special_teams["punt"]) == pytest.approx(42.0, abs=0.2)
    assert weighted_chart_mean(generated.special_teams["kickoff_return"]) == pytest.approx(
        24.2, abs=0.35
    )


def test_pass_numeric_yardage_includes_engine_resolution_calibration(tmp_path) -> None:
    """Completed-pass yardage must offset the engine's defensive reductions."""
    stats = _synthetic_stats()

    generated = generate_team_charts(stats, tmp_path / "Foxes", seed=8306)

    yards_per_completion = 4056 / 338
    assert weighted_chart_mean(generated.offense["short_pass"]) == pytest.approx(
        yards_per_completion * 0.59 * 1.28, abs=0.25
    )


def test_generated_charts_are_loadable_and_deterministic(tmp_path) -> None:
    stats = _synthetic_stats()
    first_dir = tmp_path / "first" / "2026" / "Foxes"
    second_dir = tmp_path / "second" / "2026" / "Foxes"

    generate_team_charts(stats, first_dir, seed=1234)
    generate_team_charts(stats, second_dir, seed=1234)

    for filename in ("offense.csv", "defense.csv", "special.csv", "team.yaml"):
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()

    chart = load_team_chart(str(first_dir))
    assert len(chart.offense.line_plunge) == 30
    assert len(chart.offense.short_pass) == 30
    assert len(chart.special_teams.punt) == 30
    assert chart.peripheral.short_name == "FOX '26"


@pytest.mark.parametrize("penalties", [False, True])
def test_empirical_play_results_override_one_offense_column(tmp_path, monkeypatch, penalties) -> None:
    from paydirt.play_resolver import (
        DefenseType,
        PlayType,
    )
    from tests.primary_distribution import primary_result_distribution

    quantized = []
    allocated = []
    reallocate = chart_generator.rebalance_primary_allocation
    layout = chart_generator.disperse_primary_layout

    def capture_quantization(columns):
        quantized.append(deepcopy(columns))
        return reallocate(columns)

    def capture(columns):
        allocated.append(deepcopy(columns))
        return layout(columns)

    monkeypatch.setattr(chart_generator, "disperse_primary_layout", capture)
    monkeypatch.setattr(chart_generator, "rebalance_primary_allocation", capture_quantization)
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        [
            *({"unit": "offense", "chart": "short_pass", "result": "4"} for _ in range(75)),
            *({"unit": "offense", "chart": "short_pass", "result": "BLACK"} for _ in range(25)),
        ]
    )

    baseline = generate_team_charts(stats, tmp_path / "baseline", seed=8306)
    empirical = generate_team_charts(
        stats,
        tmp_path / "empirical",
        seed=8306,
        empirical=samples,
    )

    weights = chart_roll_weights()

    def physical_mass(column):
        mass = Counter()
        for row, token in column.items():
            mass[token] += weights[row]
        return mass

    for name in baseline.offense:
        if name not in {"short_pass", "te_short_long"}:
            # Existing TE pooling consumes Short Pass when no TE sample is supplied.
            # Every other source/default allocation stays exactly independent.
            assert quantized[1][name] == quantized[0][name], name
        for generated, raw, before in ((baseline, quantized[0], allocated[0]),
                                       (empirical, quantized[1], allocated[1])):
            # Reallocation may change printed counts but preserves every exact
            # full-token physical probability, including each flag variant.
            assert physical_mass(raw[name]) == physical_mass(before[name]), name
            # Complete raw tokens and their multiplicity within each weight group
            # must survive joint placement, including OOB and rare symbols.
            assert Counter((weights[row], token) for row, token in generated.offense[name].items()) == (
                Counter((weights[row], token) for row, token in before[name].items())
            ), name
        if name not in PRIMARY_COLUMNS:
            assert empirical.offense[name] == baseline.offense[name], name
    assert quantized[1]["short_pass"] != quantized[0]["short_pass"]
    assert quantized[1]["te_short_long"] != quantized[0]["te_short_long"]
    assert empirical.defense == baseline.defense
    assert empirical.special_teams == baseline.special_teams

    public = Path(__file__).resolve().parents[1] / "seasons" / "2026"
    defender = load_team_chart(public / "Thunderhawks")
    charts = [load_team_chart(tmp_path / name) for name in ("baseline", "empirical")]
    for play in [*(PlayType(name) for name in PRIMARY_COLUMNS
                   if name not in {"short_pass", "te_short_long"}),
                 PlayType.QB_SNEAK]:
        for defense in DefenseType:
            distributions = [primary_result_distribution(chart, defender, play, defense, penalties)
                             for chart in charts]
            assert distributions[0] == distributions[1], (play, defense, penalties)
    assert empirical.offense["short_pass"] != baseline.offense["short_pass"]
    assert weighted_chart_rate(empirical.offense["short_pass"], "BLACK") == pytest.approx(
        0.25, abs=0.025
    )
    assert weighted_chart_mean(empirical.offense["short_pass"]) == pytest.approx(4.0)
    # Joint geometry may relocate an unaffected column, while its complete
    # physical token distribution remains exactly the default allocation.
    assert physical_mass(empirical.offense["line_plunge"]) == physical_mass(baseline.offense["line_plunge"])


def test_empirical_play_csv_loads_normalized_outcomes(tmp_path) -> None:
    source = tmp_path / "plays.csv"
    source.write_text(
        "unit,chart,result\noffense,line_plunge,3\noffense,line_plunge,F\nspecial_teams,punt,42\n",
        encoding="utf-8",
    )

    samples = EmpiricalChartData.from_csv(source)

    assert samples.offense["line_plunge"] == ("3", "F")
    assert samples.special_teams["punt"] == ("42",)


def test_empirical_play_csv_rejects_unknown_chart(tmp_path) -> None:
    source = tmp_path / "plays.csv"
    source.write_text(
        "unit,chart,result\noffense,quarterback_sneak,2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="quarterback_sneak"):
        EmpiricalChartData.from_csv(source)


def test_command_line_generates_team_with_empirical_plays(tmp_path) -> None:
    stats_path = tmp_path / "stats.json"
    stats_path.write_text(json.dumps(_synthetic_stats().to_dict()), encoding="utf-8")
    plays_path = tmp_path / "plays.csv"
    plays_path.write_text(
        "unit,chart,result\noffense,line_plunge,2\noffense,line_plunge,2\n",
        encoding="utf-8",
    )
    output = tmp_path / "2026" / "Foxes"

    result = main(
        [
            str(stats_path),
            "--output",
            str(output),
            "--plays",
            str(plays_path),
            "--seed",
            "17",
        ]
    )

    assert result == 0
    assert (output / "offense.csv").is_file()
    assert load_team_chart(str(output)).offense.line_plunge == {roll: "2" for roll in range(10, 40)}


def test_generated_defense_keeps_tactical_structure_and_tracks_efficiency(tmp_path) -> None:
    stats = _synthetic_stats()
    strong = replace(
        stats,
        team_name="Strong Defense",
        defense=replace(
            stats.defense,
            rushing=replace(stats.defense.rushing, attempts=500, yards=1650),
            passing=replace(stats.defense.passing, attempts=500, yards=2750),
        ),
    )
    weak = replace(
        stats,
        team_name="Weak Defense",
        defense=replace(
            stats.defense,
            rushing=replace(stats.defense.rushing, attempts=500, yards=2500),
            passing=replace(stats.defense.passing, attempts=500, yards=4250),
        ),
    )

    strong_chart = generate_team_charts(strong, tmp_path / "strong").defense
    weak_chart = generate_team_charts(weak, tmp_path / "weak").defense
    strong_cells = [cell for row in strong_chart.values() for cell in row.values()]

    assert "BLACK" in strong_cells
    assert "QT" in strong_cells
    assert any(cell.startswith("INT") for cell in strong_cells)
    assert "(TD)" in strong_cells

    def numeric_average(chart, columns):
        values = []
        for row in chart.values():
            for column in columns:
                match = re.fullmatch(r"\(?([+-]?\d+)\)?", row.get(column, ""))
                if match:
                    values.append(int(match.group(1)))
        return sum(values) / len(values)

    assert numeric_average(strong_chart, range(1, 5)) < numeric_average(weak_chart, range(1, 5))
    assert numeric_average(strong_chart, range(5, 10)) < numeric_average(weak_chart, range(5, 10))


def test_generated_defense_preserves_close_efficiency_differences(tmp_path) -> None:
    stats = _synthetic_stats()
    stronger = replace(
        stats,
        team_name="Close Strong Defense",
        defense=replace(
            stats.defense,
            rushing=replace(stats.defense.rushing, attempts=500, yards=2000),
            passing=replace(stats.defense.passing, attempts=500, yards=3500),
        ),
    )
    weaker = replace(
        stats,
        team_name="Close Weak Defense",
        defense=replace(
            stats.defense,
            rushing=replace(stats.defense.rushing, attempts=500, yards=2100),
            passing=replace(stats.defense.passing, attempts=500, yards=3700),
        ),
    )

    stronger_chart = generate_team_charts(stronger, tmp_path / "stronger").defense
    weaker_chart = generate_team_charts(weaker, tmp_path / "weaker").defense

    assert stronger_chart != weaker_chart

    subrow_weights = {1: 12, 2: 11, 3: 9, 4: 3, 5: 1}

    def weighted_numeric_average(chart, columns):
        numerator = 0
        denominator = 0
        for (_, subrow), row in chart.items():
            for column in columns:
                match = re.fullmatch(r"\(?([+-]?\d+)\)?", row.get(column, ""))
                if match:
                    weight = subrow_weights[subrow]
                    numerator += int(match.group(1)) * weight
                    denominator += weight
        return numerator / denominator

    assert weighted_numeric_average(stronger_chart, range(1, 5)) < weighted_numeric_average(
        weaker_chart, range(1, 5)
    )
    assert weighted_numeric_average(stronger_chart, range(5, 10)) < weighted_numeric_average(
        weaker_chart, range(5, 10)
    )


def test_generated_charts_depend_on_rates_not_season_length(tmp_path) -> None:
    stats = _synthetic_stats()

    def double_counts(line):
        return replace(
            line,
            attempts=line.attempts * 2,
            yards=line.yards * 2,
            touchdowns=line.touchdowns * 2,
            fumbles=line.fumbles * 2,
            fumbles_lost=line.fumbles_lost * 2,
            completions=line.completions * 2,
            interceptions=line.interceptions * 2,
            sacks=line.sacks * 2,
            sack_yards=line.sack_yards * 2,
            made=line.made * 2,
            blocked=line.blocked * 2,
        )

    doubled = replace(
        stats,
        offense=replace(
            stats.offense,
            rushing=double_counts(stats.offense.rushing),
            passing=double_counts(stats.offense.passing),
        ),
        defense=replace(
            stats.defense,
            rushing=double_counts(stats.defense.rushing),
            passing=double_counts(stats.defense.passing),
        ),
        special_teams=replace(
            stats.special_teams,
            **{
                name: double_counts(getattr(stats.special_teams, name))
                for name in (
                    "kickoff",
                    "kickoff_return",
                    "punt",
                    "punt_return",
                    "interception_return",
                    "field_goal",
                    "extra_point",
                )
            },
        ),
    )

    original = generate_team_charts(stats, tmp_path / "original", seed=8306)
    scaled = generate_team_charts(doubled, tmp_path / "scaled", seed=8306)

    assert original == scaled


def test_generated_pass_rates_use_resolved_attempt_denominators(tmp_path) -> None:
    """Passing rates must survive pressure and penalty chart outcomes."""
    stats = _synthetic_stats()
    column = generate_team_charts(stats, tmp_path / "Foxes", seed=8306).offense[
        "short_pass"
    ]
    roll_weights = chart_roll_weights()
    total_weight = sum(roll_weights.values())

    def matching_rate(predicate) -> float:
        return sum(
            weight
            for roll, weight in roll_weights.items()
            if predicate(column[roll])
        ) / total_weight

    pressure_rate = matching_rate(lambda cell: cell.startswith("QT"))
    penalty_rate = matching_rate(
        lambda cell: cell.startswith(("OFF", "DEF", "PI"))
    )
    interception_rate = matching_rate(lambda cell: cell.startswith("INT"))
    completion_rate = matching_rate(
        lambda cell: bool(re.fullmatch(r"[+-]?\d+[*†]?|TD", cell))
    )
    attempt_mass = 1.0 - pressure_rate - penalty_rate

    assert completion_rate / attempt_mass == pytest.approx(0.75, abs=0.025)
    assert interception_rate / attempt_mass == pytest.approx(
        max(0.0, (12 / 520) - 0.006), abs=0.02
    )
    assert pressure_rate == pytest.approx((32 / 552) * 1.70, abs=0.02)


def test_generated_fumble_rates_survive_secondary_resolution(tmp_path) -> None:
    """Primary and QB-time chart mass must reproduce supplied fumble rates."""
    stats = _synthetic_stats()
    passing = replace(stats.offense.passing, fumbles=10, fumbles_lost=5)
    stats = replace(stats, offense=replace(stats.offense, passing=passing))
    offense = generate_team_charts(stats, tmp_path / "Foxes", seed=8306).offense
    roll_weights = chart_roll_weights()
    total_weight = sum(roll_weights.values())

    def prefix_rate(column: dict[int, str], prefix: str) -> float:
        return sum(
            weight
            for roll, weight in roll_weights.items()
            if column[roll].startswith(prefix)
        ) / total_weight

    run_fumble_rate = prefix_rate(offense["line_plunge"], "F")
    pressure_rate = prefix_rate(offense["short_pass"], "QT")
    qb_time_fumble_rate = prefix_rate(offense["qb_time"], "F")

    assert run_fumble_rate == pytest.approx(12 / 480, abs=0.005)
    expected_pass_fumble_rate = 10 / (520 + 32)
    assert pressure_rate * qb_time_fumble_rate == pytest.approx(
        expected_pass_fumble_rate, abs=0.005
    )


def test_generated_pass_column_preserves_each_symbolic_outcome_rate(tmp_path) -> None:
    stats = _synthetic_stats()
    column = generate_team_charts(stats, tmp_path / "Foxes", seed=8306).offense["short_pass"]
    roll_weights = chart_roll_weights()
    total_weight = sum(roll_weights.values())

    def rate_with_prefix(prefixes: tuple[str, ...]) -> float:
        return sum(
            weight
            for roll, weight in roll_weights.items()
            if column[roll].startswith(prefixes)
        ) / total_weight

    pressure_rate = (32 / 552) * 1.70
    interception_rate = max(0.0, (12 / 520) - 0.006)
    attempt_mass = 1.0 - pressure_rate - 0.055
    assert rate_with_prefix(("BLACK",)) == pytest.approx(
        (1.0 - 0.75 - interception_rate) * attempt_mass, abs=0.02
    )
    assert rate_with_prefix(("INT",)) == pytest.approx(
        interception_rate * attempt_mass, abs=0.02
    )
    assert rate_with_prefix(("TD",)) == pytest.approx(
        (30 / 520) * attempt_mass, abs=0.02
    )
    assert rate_with_prefix(("QT",)) == pytest.approx(pressure_rate, abs=0.02)
    assert rate_with_prefix(("OFF", "DEF", "PI")) == pytest.approx(0.055, abs=0.02)


def test_empirical_numeric_out_of_bounds_markers_survive_generation_and_loading(tmp_path) -> None:
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        [
            *(
                {"unit": "offense", "chart": "short_pass", "result": "4*"}
                for _ in range(3)
            ),
            {"unit": "offense", "chart": "short_pass", "result": "4"},
        ]
    )
    output = tmp_path / "2026" / "Foxes"

    generated = generate_team_charts(stats, output, seed=8306, empirical=samples)
    loaded = load_team_chart(str(output))

    assert weighted_chart_rate(generated.offense["short_pass"], "4*") == pytest.approx(
        0.75, abs=0.03
    )
    assert weighted_chart_rate(generated.offense["short_pass"], "4") == pytest.approx(
        0.25, abs=0.03
    )
    assert set(loaded.offense.short_pass.values()) == {"4", "4*"}
    assert parse_result_string("4*").out_of_bounds is True
    assert parse_result_string("4").out_of_bounds is False


def test_empirical_rows_reject_invalid_result_symbols() -> None:
    with pytest.raises(ValueError, match=r"TYPO.*row 2"):
        EmpiricalChartData.from_rows(
            [{"unit": "offense", "chart": "short_pass", "result": "TYPO"}]
        )


def test_field_goal_distance_results_control_generated_accuracy(tmp_path) -> None:
    stats = _synthetic_stats()
    accurate = replace(
        stats,
        team_name="Accurate Kicker",
        special_teams=replace(
            stats.special_teams,
            field_goal_by_distance=(
                {"distance": 30, "attempts": 10, "made": 10},
                {"distance": 45, "attempts": 10, "made": 8},
                {"distance": 55, "attempts": 10, "made": 4},
            ),
        ),
    )
    inaccurate = replace(
        stats,
        team_name="Inaccurate Kicker",
        special_teams=replace(
            stats.special_teams,
            field_goal_by_distance=(
                {"distance": 30, "attempts": 10, "made": 7},
                {"distance": 45, "attempts": 10, "made": 3},
                {"distance": 55, "attempts": 10, "made": 0},
            ),
        ),
    )

    accurate_column = generate_team_charts(
        TeamSeasonStats.from_dict(accurate.to_dict()), tmp_path / "accurate", seed=8306
    ).special_teams["field_goal"]
    inaccurate_column = generate_team_charts(
        TeamSeasonStats.from_dict(inaccurate.to_dict()), tmp_path / "inaccurate", seed=8306
    ).special_teams["field_goal"]

    def success_rate(column: dict[int, str], kick_distance: int) -> float:
        needed_chart_yards = kick_distance - 17
        numeric = {
            roll: int(cell)
            for roll, cell in column.items()
            if re.fullmatch(r"[+-]?\d+", cell)
        }
        successful_mass = sum(
            chart_roll_weights()[roll]
            for roll, yards in numeric.items()
            if yards >= needed_chart_yards
        )
        resolved_mass = sum(chart_roll_weights()[roll] for roll in numeric)
        return successful_mass / resolved_mass

    assert accurate_column != inaccurate_column
    assert success_rate(accurate_column, 30) == pytest.approx(1.0, abs=0.03)
    assert success_rate(accurate_column, 45) == pytest.approx(0.8, abs=0.03)
    assert success_rate(accurate_column, 55) == pytest.approx(0.4, abs=0.03)
    assert success_rate(inaccurate_column, 45) == pytest.approx(0.3, abs=0.03)


def test_supplied_fumble_loss_rate_controls_loaded_recovery_range(tmp_path) -> None:
    stats = _synthetic_stats()
    low_loss = replace(
        stats,
        team_name="Secure Ball",
        offense=replace(
            stats.offense,
            rushing=replace(stats.offense.rushing, fumbles=20, fumbles_lost=1),
            passing=replace(stats.offense.passing, fumbles=0, fumbles_lost=0),
        ),
    )
    high_loss = replace(
        stats,
        team_name="Loose Ball",
        offense=replace(
            stats.offense,
            rushing=replace(stats.offense.rushing, fumbles=20, fumbles_lost=15),
            passing=replace(stats.offense.passing, fumbles=0, fumbles_lost=0),
        ),
    )

    low_dir = tmp_path / "2026" / "Low"
    high_dir = tmp_path / "2026" / "High"
    generate_team_charts(low_loss, low_dir, seed=8306)
    generate_team_charts(high_loss, high_dir, seed=8306)
    low_range = load_team_chart(str(low_dir)).peripheral.fumble_recovered_range
    high_range = load_team_chart(str(high_dir)).peripheral.fumble_recovered_range

    def lost_rate(recovered_range: tuple[int, int]) -> float:
        start, end = recovered_range
        recovered_mass = sum(
            weight
            for roll, weight in chart_roll_weights().items()
            if start <= roll <= end
        )
        return 1.0 - recovered_mass / sum(chart_roll_weights().values())

    assert low_range != high_range
    assert lost_rate(low_range) == pytest.approx(0.05, abs=0.03)
    assert lost_rate(high_range) == pytest.approx(0.75, abs=0.03)


def test_empirical_pass_events_can_be_calibrated_to_engine_baseline(tmp_path) -> None:
    """Empirical yards should retain aggregate event rates needed by the engine."""
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        {"unit": "offense", "chart": "short_pass", "result": str(4 + index % 5)}
        for index in range(240)
    )

    raw = generate_team_charts(
        stats,
        tmp_path / "raw",
        seed=8306,
        empirical=samples,
    ).offense["short_pass"]
    calibrated = generate_team_charts(
        stats,
        tmp_path / "calibrated",
        seed=8306,
        empirical=samples,
        calibrate_empirical_pass_events=True,
    ).offense["short_pass"]

    assert all(re.fullmatch(r"[+-]?\d+", result) for result in raw.values())
    assert any(result == "BLACK" for result in calibrated.values())
    assert any(result.startswith("INT ") for result in calibrated.values())
    assert any(result.startswith("QT") for result in calibrated.values())
    assert any(result.startswith(("OFF ", "DEF ", "PI ")) for result in calibrated.values())
    numeric = [int(result) for result in calibrated.values() if re.fullmatch(r"[+-]?\d+", result)]
    assert min(numeric) >= 4
    assert max(numeric) <= 8


def test_empirical_long_runs_use_breakaway_trigger_and_conditional_yardage(tmp_path) -> None:
    """Exceptional runs trigger B while its chart represents all long runs."""
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        [
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "4"}
                for _ in range(100)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "10"}
                for _ in range(10)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "18"}
                for _ in range(10)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "19"}
                for _ in range(5)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "20"}
                for _ in range(5)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "25*"}
                for _ in range(5)
            ),
            *(
                {"unit": "offense", "chart": "line_plunge", "result": "F + 14"}
                for _ in range(10)
            ),
        ]
    )

    generated = generate_team_charts(
        stats, tmp_path / "empirical-breakaway", seed=8306, empirical=samples
    ).offense

    primary = set(generated["line_plunge"].values())
    assert "B" in primary
    assert {"10", "18", "F + 14"} <= primary
    assert "19" not in primary
    assert "20" not in primary
    assert "25*" not in primary
    breakaway = set(generated["breakaway"].values())
    assert {"10", "18", "19", "20", "25*"} <= breakaway
    assert not any(cell.startswith("F") for cell in breakaway)

    weights = chart_roll_weights()
    breakaway_mass = sum(
        weights[roll]
        for roll, result in generated["line_plunge"].items()
        if result == "B"
    )
    direct_long_mass = sum(
        weights[roll]
        for roll, result in generated["line_plunge"].items()
        if (match := re.fullmatch(r"(\d+)[*†]?", result))
        and int(match.group(1)) >= 10
    )
    assert breakaway_mass < direct_long_mass


def test_empirical_pass_data_replaces_aggregate_te_touchdowns(tmp_path) -> None:
    """T/E S/L should use observed gains instead of automatic aggregate TD cells."""
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        [
            *(
                {"unit": "offense", "chart": "short_pass", "result": "5"}
                for _ in range(80)
            ),
            *(
                {"unit": "offense", "chart": "medium_pass", "result": "12"}
                for _ in range(80)
            ),
            *(
                {"unit": "offense", "chart": "long_pass", "result": "30"}
                for _ in range(40)
            ),
        ]
    )

    generated = generate_team_charts(
        stats,
        tmp_path / "empirical-tight-end",
        seed=8306,
        empirical=samples,
        calibrate_empirical_pass_events=True,
    ).offense["te_short_long"]

    assert "TD" not in generated.values()
    numeric = {
        int(result)
        for result in generated.values()
        if re.fullmatch(r"[+-]?\d+", result)
    }
    assert numeric <= {5, 12, 30}
    assert numeric


def test_empirical_event_calibration_uses_compact_baseline_symbols(tmp_path) -> None:
    """Rare source symbol variants must not lose target event probability mass."""
    stats = _synthetic_stats()
    rows = [
        *(
            {"unit": "offense", "chart": "short_pass", "result": str(3 + index % 8)}
            for index in range(200)
        ),
        *(
            {"unit": "offense", "chart": "short_pass", "result": f"INT {index}"}
            for index in range(1, 31)
        ),
        *(
            {
                "unit": "offense",
                "chart": "short_pass",
                "result": result,
            }
            for result in ("OFF 5", "OFF 10", "DEF 5X", "PI 8") * 8
        ),
    ]
    empirical = EmpiricalChartData.from_rows(rows)
    baseline = generate_team_charts(
        stats, tmp_path / "baseline", seed=8306
    ).offense["short_pass"]
    calibrated = generate_team_charts(
        stats,
        tmp_path / "calibrated-variants",
        seed=8306,
        empirical=empirical,
        calibrate_empirical_pass_events=True,
    ).offense["short_pass"]
    weights = chart_roll_weights()
    total = sum(weights.values())

    def rate(column: dict[int, str], prefixes: tuple[str, ...]) -> float:
        return sum(
            weight
            for roll, weight in weights.items()
            if column[roll].startswith(prefixes)
        ) / total

    for prefixes in (("INT ",), ("QT",), ("OFF ", "DEF ", "PI "), ("BLACK",)):
        assert rate(calibrated, prefixes) == pytest.approx(
            rate(baseline, prefixes), abs=0.02
        )
    baseline_events = {
        result
        for result in baseline.values()
        if result.startswith(("INT ", "QT", "OFF ", "DEF ", "PI "))
        or result == "BLACK"
    }
    calibrated_events = {
        result
        for result in calibrated.values()
        if result.startswith(("INT ", "QT", "OFF ", "DEF ", "PI "))
        or result == "BLACK"
    }
    source_penalties = {"OFF 5", "OFF 10", "DEF 5X", "PI 8"}
    assert calibrated_events <= baseline_events | source_penalties
    assert source_penalties <= calibrated_events


def test_empirical_quantization_preserves_combined_fumble_family_rate(tmp_path) -> None:
    """Distinct fumble-yard variants must retain their combined probability mass."""
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        [
            *(
                {"unit": "offense", "chart": "line_plunge", "result": str(2 + index % 5)}
                for index in range(200)
            ),
            *(
                {
                    "unit": "offense",
                    "chart": "line_plunge",
                    "result": f"F + {1 + index % 8}",
                }
                for index in range(20)
            ),
        ]
    )

    column = generate_team_charts(
        stats, tmp_path / "fumble-family", seed=8306, empirical=samples
    ).offense["line_plunge"]
    weights = chart_roll_weights()
    fumble_rate = sum(
        weight
        for roll, weight in weights.items()
        if column[roll].startswith("F")
    ) / sum(weights.values())

    assert fumble_rate == pytest.approx(20 / 220, abs=0.02)


def test_empirical_pass_calibration_applies_engine_offsets_and_yard_scale(tmp_path) -> None:
    """Explicit engine calibration should shift event mass and resolved gain size."""
    stats = _synthetic_stats()
    samples = EmpiricalChartData.from_rows(
        {"unit": "offense", "chart": "short_pass", "result": str(4 + index % 5)}
        for index in range(240)
    )
    neutral = generate_team_charts(
        stats,
        tmp_path / "neutral-calibration",
        seed=8306,
        empirical=samples,
        calibrate_empirical_pass_events=True,
    ).offense["short_pass"]
    tuned = generate_team_charts(
        stats,
        tmp_path / "tuned-calibration",
        seed=8306,
        empirical=samples,
        calibrate_empirical_pass_events=True,
        empirical_pass_calibration=EmpiricalPassCalibration(
            completion_rate_adjustment=-0.03,
            interception_rate_adjustment=0.02,
            pressure_rate_adjustment=-0.02,
            resolved_yard_multiplier=1.5,
        ),
    ).offense["short_pass"]
    weights = chart_roll_weights()
    total = sum(weights.values())

    def rate(column: dict[int, str], prefixes: tuple[str, ...]) -> float:
        return sum(
            weight
            for roll, weight in weights.items()
            if column[roll].startswith(prefixes)
        ) / total

    assert rate(tuned, ("BLACK",)) > rate(neutral, ("BLACK",))
    assert rate(tuned, ("INT ",)) > rate(neutral, ("INT ",))
    assert rate(tuned, ("QT",)) < rate(neutral, ("QT",))
    assert weighted_chart_mean(tuned) > weighted_chart_mean(neutral) * 1.3


def test_generated_csvs_use_lf_line_endings(tmp_path) -> None:
    """Generated chart files should not add CR characters to tracked CSV lines."""
    output = tmp_path / "Foxes"

    generate_team_charts(_synthetic_stats(), output, seed=8306)

    for name in ("offense.csv", "defense.csv", "special.csv"):
        assert b"\r\n" not in (output / name).read_bytes()



def test_defensive_interception_strength_uses_distributed_low_mass_rows(tmp_path) -> None:
    """Defense strength must not create one high-probability interception trap."""
    stats = _synthetic_stats()

    def with_defensive_interception_rate(rate: float, name: str) -> TeamSeasonStats:
        attempts = 2000
        return replace(
            stats,
            team_name=name,
            defense=replace(
                stats.defense,
                passing=replace(
                    stats.defense.passing,
                    attempts=attempts,
                    completions=1200,
                    yards=14400,
                    interceptions=round(attempts * rate),
                ),
            ),
        )

    weak = generate_team_charts(
        with_defensive_interception_rate(0.015, "Weak Interception Defense"),
        tmp_path / "weak",
        seed=8306,
    ).defense
    neutral = generate_team_charts(
        with_defensive_interception_rate(0.025, "Neutral Interception Defense"),
        tmp_path / "neutral",
        seed=8306,
    ).defense
    strong = generate_team_charts(
        with_defensive_interception_rate(0.045, "Strong Interception Defense"),
        tmp_path / "strong",
        seed=8306,
    ).defense
    weights = defense_subrow_weights()
    total = sum(weights.values())

    def call_rate(
        defense: dict[tuple[str, int], dict[int, str]],
        formation: str,
        column: int,
    ) -> float:
        return sum(
            weights[subrow]
            for subrow in weights
            if defense[(formation, subrow)][column].startswith("INT")
        ) / total

    def combined_mass(
        defense: dict[tuple[str, int], dict[int, str]],
    ) -> float:
        return sum(
            call_rate(defense, formation, column)
            for formation in "ABCDEF"
            for column in range(5, 10)
        )

    assert combined_mass(weak) < combined_mass(neutral) < combined_mass(strong)
    assert max(
        call_rate(strong, formation, column)
        - call_rate(neutral, formation, column)
        for formation in "ABCDEF"
        for column in range(5, 10)
    ) <= (1 / 36) + 1e-12
    # The old 4/36 expectation included a hidden 3/36 neutral-template floor.
    # Generated interceptions now occupy only the rare 1/36 subrow.
    assert call_rate(strong, "D", 6) == pytest.approx(1 / 36)


def test_defensive_interception_threshold_has_no_large_call_specific_jump(tmp_path) -> None:
    """Crossing the old 3.5% threshold may change at most one low-mass row per call."""
    stats = _synthetic_stats()

    def generated(rate: float, name: str) -> dict[tuple[str, int], dict[int, str]]:
        attempts = 10000
        adjusted = replace(
            stats,
            team_name=name,
            defense=replace(
                stats.defense,
                passing=replace(
                    stats.defense.passing,
                    attempts=attempts,
                    completions=6000,
                    yards=72000,
                    interceptions=round(attempts * rate),
                ),
            ),
        )
        return generate_team_charts(adjusted, tmp_path / name, seed=8306).defense

    below = generated(0.0349, "Below Threshold")
    above = generated(0.0351, "Above Threshold")
    weights = defense_subrow_weights()
    total = sum(weights.values())

    def rate(
        defense: dict[tuple[str, int], dict[int, str]],
        formation: str,
        column: int,
    ) -> float:
        return sum(
            weights[subrow]
            for subrow in weights
            if defense[(formation, subrow)][column].startswith("INT")
        ) / total

    largest_jump = max(
        abs(rate(above, formation, column) - rate(below, formation, column))
        for formation in "ABCDEF"
        for column in range(5, 10)
    )
    assert largest_jump <= (1 / 36) + 1e-12


def test_generated_special_teams_include_penalty_mass(tmp_path) -> None:
    """Every generated special-teams family must be able to produce a foul."""
    generated = generate_team_charts(
        _synthetic_stats(), tmp_path / "Foxes", seed=8306
    ).special_teams

    for name in (
        "kickoff",
        "kickoff_return",
        "punt",
        "punt_return",
        "interception_return",
        "field_goal",
    ):
        assert any(
            cell.startswith(("OFF ", "DEF "))
            for cell in generated[name].values()
        ), name


def test_empirical_special_teams_keep_fallback_penalty_mass(tmp_path) -> None:
    """Resolved empirical samples must not erase all special-teams foul risk."""
    empirical = EmpiricalChartData(
        special_teams={"punt": tuple(str(38 + index % 5) for index in range(24))}
    )

    punt = generate_team_charts(
        _synthetic_stats(), tmp_path / "Foxes", empirical=empirical, seed=8306
    ).special_teams["punt"]

    assert any(cell.startswith(("OFF ", "DEF ")) for cell in punt.values())


def test_empirical_numeric_quantiles_are_ordered_by_yardage() -> None:
    """Quantiles must follow numeric rank, including negative and marked gains."""
    from paydirt.chart_generator import _assign_empirical_variants

    weights = chart_roll_weights()
    values = tuple(str(value) for value in range(-10, 100))
    column = {}
    _assign_empirical_variants(column, tuple(weights), values, seed=8306)
    import random
    order = list(weights)
    random.Random(8306).shuffle(order)
    observed = [int(column[roll]) for roll in order]
    assert observed == sorted(observed)


def test_long_run_reconstruction_preserves_fumbles_and_oob() -> None:
    """Routing long gains through B must retain clock and turnover information."""
    from paydirt.chart_generator import _reconstruct_empirical_breakaways

    result = _reconstruct_empirical_breakaways({
        'end_run': ('3', '25*', 'F + 30', '12'),
    })
    assert result['end_run'] == ('3', 'B*', 'F + 30', '12')
    assert result['breakaway'] == ('25*', '12')


def test_blocked_field_goals_survive_distance_calibration(tmp_path) -> None:
    """Blocks have their own result and must not reduce conditional accuracy twice."""
    data = _synthetic_stats().to_dict()
    data['special_teams']['field_goal'] = {'attempts': 100, 'made': 70, 'blocked': 10}
    data['special_teams']['field_goal_by_distance'] = [
        {'distance': 40, 'attempts': 100, 'made': 70, 'blocked': 10},
    ]
    chart = generate_team_charts(TeamSeasonStats.from_dict(data), tmp_path).special_teams['field_goal']
    weights = chart_roll_weights()
    attempts = sum(w for r,w in weights.items() if not chart[r].startswith(('OFF', 'DEF')))
    blocks = sum(w for r,w in weights.items() if chart[r].startswith('BK'))
    makes = sum(w for r,w in weights.items() if chart[r].isdigit() and int(chart[r]) >= 23)
    assert blocks / attempts == pytest.approx(.10, abs=.015)
    assert makes / attempts == pytest.approx(.70, abs=.015)


def test_empirical_pass_scaling_cannot_exceed_the_field(tmp_path) -> None:
    """Calibration may strengthen gains without encoding impossible 150-yard plays."""
    samples = EmpiricalChartData(offense={'long_pass': ('99',) * 100})
    charts = generate_team_charts(
        _synthetic_stats(), tmp_path, empirical=samples,
        calibrate_empirical_pass_events=True,
        empirical_pass_calibration=EmpiricalPassCalibration(resolved_yard_multiplier=2),
    )
    assert max(int(v) for v in charts.offense['long_pass'].values() if v.isdigit()) <= 99


def test_missing_source_markers_use_explicit_modeled_fallbacks(tmp_path) -> None:
    """An explicitly incomplete source must not remove clock and kick mechanisms."""
    samples = EmpiricalChartData(
        offense={'end_run': ('4',) * 100},
        special_teams={'punt': ('40',) * 100, 'kickoff': ('65',) * 100},
    )
    charts = generate_team_charts(
        _synthetic_stats(), tmp_path / 'fallback', empirical=samples,
        missing_source_features=('offense_oob', 'punt_fair_catch', 'kickoff_out'),
    )
    assert any(v.endswith('*') for v in charts.offense['end_run'].values())
    assert any(v.endswith('*') for v in charts.special_teams['punt'].values())
    assert 'OB' in charts.special_teams['kickoff'].values()
    control = generate_team_charts(_synthetic_stats(), tmp_path / 'control', empirical=samples)
    assert not any(v.endswith('*') for v in control.offense['end_run'].values())
    assert not any(v.endswith('*') for v in control.special_teams['punt'].values())
    assert 'OB' not in control.special_teams['kickoff'].values()


def test_calibration_samples_the_whole_season_and_preserves_observed_fouls() -> None:
    """Resampling must not truncate late-season fumbles or replace penalty types."""
    from paydirt.chart_generator import _calibrate_empirical_pass_events

    weights = chart_roll_weights()
    baseline = {roll: 'BLACK' if roll < 30 else '4' for roll in weights}
    outcomes = ('4',) * 80 + ('F + 4',) * 20
    calibrated = _calibrate_empirical_pass_events(outcomes, baseline, EmpiricalPassCalibration())
    resolved = [value for value in calibrated if value != 'BLACK']
    assert sum(value.startswith('F') for value in resolved) / len(resolved) == pytest.approx(.2, abs=.02)
    penalties = _calibrate_empirical_pass_events(
        ('DEF 5X',) * 10 + ('4',) * 90,
        {roll: 'OFF 5' if roll < 20 else '4' for roll in weights},
        EmpiricalPassCalibration(),
    )
    assert 'DEF 5X' in penalties
    assert 'OFF 5' not in penalties


def test_missing_rare_special_events_retain_engine_mechanisms(tmp_path) -> None:
    """Historical annotation gaps must not make rare kick mishaps impossible."""
    charts = generate_team_charts(
        _synthetic_stats(), tmp_path,
        missing_source_features=('field_goal_block', 'field_goal_fumble', 'punt_fumble', 'interception_return_fumble'),
    )
    assert any(v.startswith('BK') for v in charts.special_teams['field_goal'].values())
    assert any(v.startswith('F ') for v in charts.special_teams['field_goal'].values())
    assert any(v.startswith('F') for v in charts.special_teams['punt'].values())
    assert any(v.startswith('F') for v in charts.special_teams['interception_return'].values())


@pytest.mark.parametrize("column,cell", [("qb_time", "OFF 5"), ("breakaway", "F + 2"),
                                        ("qb_time", "BLACK")])
def test_generator_rejects_unusable_conditional_samples(tmp_path, column, cell):
    empirical = EmpiricalChartData(offense={column: (cell, "4", "-5")}, special_teams={})
    with pytest.raises(ValueError, match="unsupported.*" + column):
        generate_team_charts(_synthetic_stats(), tmp_path, empirical=empirical)


@pytest.mark.parametrize("sack_samples", [25, 75, 100])
def test_empirical_pressure_reserves_defense_and_uses_actual_qt_sack_mix(tmp_path, sack_samples):
    """Equal sack targets require different QT mass for mobile and immobile QBs."""
    from fractions import Fraction

    from paydirt.chart_generator import _generate_defense
    from paydirt.chart_loader import DefenseChart
    from paydirt.chart_tactics_audit import resolved_outcome_distribution
    from paydirt.play_resolver import DefenseType, PlayType

    stats = _synthetic_stats()
    stats = replace(stats, offense=replace(stats.offense, passing=replace(
        stats.offense.passing, attempts=920, sacks=80,
    )), defense=replace(stats.defense, passing=replace(
        stats.defense.passing, attempts=1000, sacks=65, interceptions=25,
    )))
    samples = EmpiricalChartData(offense={
        **{name: ("8",) * 1000 for name in
           ("screen", "short_pass", "medium_pass", "long_pass", "te_short_long")},
        "qb_time": ("-6",) * sack_samples + ("5",) * (100 - sack_samples),
    })
    generate_team_charts(stats, tmp_path, empirical=samples,
                         calibrate_empirical_pass_events=True)
    chart = load_team_chart(tmp_path)
    neutral = DefenseChart(_generate_defense(stats))
    sack_mass, scramble_mass, retained_mass = Fraction(), Fraction(), Fraction()
    for formation, weight in zip(DefenseType, [22, 12, 16, 20, 14, 16]):
        for call, call_weight in zip(
            (PlayType.SCREEN, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
             PlayType.LONG_PASS, PlayType.TE_SHORT_LONG), (8, 22, 16, 6, 4),
        ):
            distribution = resolved_outcome_distribution(chart, neutral, call, formation)
            for outcome, probability in distribution.items():
                mass = probability * weight * call_weight / 5600
                if outcome.kind == "sack":
                    sack_mass += mass
                elif outcome.kind == "qb_scramble":
                    scramble_mass += mass
                if outcome.kind != "pending_penalty":
                    retained_mass += mass
    # Official denominator excludes QB scrambles, rather than treating all QT
    # branches as sacks. Finite 216-face allocation is the only approximation.
    observed = sack_mass / (retained_mass - scramble_mass)
    assert float(observed) == pytest.approx(.08, abs=.006)


def test_empirical_pressure_rejects_missing_sack_support(tmp_path):
    samples = EmpiricalChartData(offense={"short_pass": ("8",) * 100,
                                         "qb_time": ("5",) * 100})
    with pytest.raises(ValueError, match="QT.*sack"):
        generate_team_charts(_synthetic_stats(), tmp_path, empirical=samples,
                             calibrate_empirical_pass_events=True)


def test_empirical_pressure_exposes_unattainable_defensive_sack_floor(tmp_path):
    stats = _synthetic_stats()
    stats = replace(stats, offense=replace(stats.offense, passing=replace(
        stats.offense.passing, attempts=1000, sacks=1,
    )))
    samples = EmpiricalChartData(offense={"short_pass": ("8",) * 1000,
                                         "qb_time": ("-6",) * 100})
    with pytest.raises(ValueError, match="QT.*attainable"):
        generate_team_charts(stats, tmp_path, empirical=samples,
                             calibrate_empirical_pass_events=True)


def test_empirical_allocation_discloses_unrepresented_rare_variant(tmp_path):
    samples = EmpiricalChartData(offense={"short_pass": ("8",) * 9999 + ("INT 5",)})
    generated = generate_team_charts(_synthetic_stats(), tmp_path, empirical=samples)
    evidence = generated.empirical_allocations["offense/short_pass"]
    assert evidence["population"] == "modeled column inputs, not raw event counts"
    assert evidence["variants"]["INT 5"] == {
        "requested_samples": 1, "requested_probability": .0001,
        "physical_mass": 0, "physical_probability": 0.0,
    }
    assert evidence["unrepresented_variants"] == ["INT 5"]
    assert evidence["physical_denominator"] == 216
    assert all(value == "8" for value in generated.offense["short_pass"].values())


def test_neutral_defense_interception_mass_fits_declared_offense_allowance(tmp_path):
    from fractions import Fraction

    stats = _synthetic_stats()
    stats = replace(stats, defense=replace(stats.defense, passing=replace(
        stats.defense.passing, attempts=1000, interceptions=25,
    )))
    generated = generate_team_charts(stats, tmp_path)
    # Independent specification of the declared normal chart-focused pass mix.
    formations = dict(zip("ABCDEF", [22, 12, 16, 20, 14, 16]))
    calls = dict(zip(range(5, 10), [8, 22, 16, 6, 4]))
    mass = sum(Fraction(formation_weight * play_weight * row_weight, 100 * 56 * 36)
               for formation, formation_weight in formations.items()
               for column, play_weight in calls.items()
               for row, row_weight in defense_subrow_weights().items()
               if generated.defense[(formation, row)][column].startswith("INT"))
    assert 0 < mass <= Fraction(6, 1000), mass


def test_generated_interception_strength_only_uses_rare_defensive_subrows(tmp_path):
    generated = generate_team_charts(_synthetic_stats(), tmp_path)
    assert all(row == 5 for (formation, row), cells in generated.defense.items()
               for cell in cells.values() if cell.startswith("INT"))
