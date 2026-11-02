import json
import re
from dataclasses import replace

import pytest

from paydirt.chart_generator import (
    EmpiricalChartData,
    EmpiricalPassCalibration,
    TeamSeasonStats,
    generate_team_charts,
    main,
    weighted_chart_mean,
    weighted_chart_rate,
)
from paydirt.chart_loader import load_team_chart
from paydirt.play_resolver import chart_roll_weights, parse_result_string


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


def test_empirical_play_results_override_one_offense_column(tmp_path) -> None:
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

    assert empirical.offense["line_plunge"] == baseline.offense["line_plunge"]
    assert empirical.offense["short_pass"] != baseline.offense["short_pass"]
    assert weighted_chart_rate(empirical.offense["short_pass"], "BLACK") == pytest.approx(
        0.25, abs=0.025
    )
    assert weighted_chart_mean(empirical.offense["short_pass"]) == pytest.approx(4.0)


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
        successful_mass = sum(
            weight
            for roll, weight in chart_roll_weights().items()
            if int(column[roll]) >= needed_chart_yards
        )
        return successful_mass / sum(chart_roll_weights().values())

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
    assert calibrated_events <= baseline_events


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
                    "result": f"F + {index}",
                }
                for index in range(1, 21)
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
