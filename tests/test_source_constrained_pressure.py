"""Synthetic controls for one cohort-wide neutral pressure allocation."""

from collections import Counter
from dataclasses import replace
from fractions import Fraction

import pytest

from paydirt import chart_generator as generator
from paydirt.chart_generator import EmpiricalChartData, TeamSeasonStats
from paydirt.chart_loader import DefenseChart, load_team_chart
from paydirt.chart_tactics_audit import resolved_outcome_distribution
from paydirt.play_resolver import DefenseType, PlayType


def _source(sacks: int = 40, attempts: int = 960) -> tuple[TeamSeasonStats, EmpiricalChartData]:
    """Create source observations with known sack severity and neutral defense."""
    stats = TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Synthetic Low Pressure", "short_name": "SLP",
        "offense": {
            "passing": {"attempts": attempts, "sacks": sacks, "sack_yards": sacks * 6,
                        "completions": attempts // 2, "yards": attempts * 6},
            "rushing": {"attempts": 400, "yards": 1600},
        },
        "defense": {
            "passing": {"attempts": 1000, "sacks": 65, "interceptions": 25,
                        "yards": 7200, "completions": 600},
            "rushing": {"attempts": 1000, "yards": 4100},
        },
    })
    samples = EmpiricalChartData(offense={
        **{name: ("8",) * 100 + ("BLACK",) * 100 for name in (
            "screen", "short_pass", "medium_pass", "long_pass", "te_short_long",
        )},
        "qb_time": ("-6",) * 100,
    })
    return stats, samples


def _neutral() -> dict[tuple[str, int], dict[int, str]]:
    cells = {(formation, subrow): dict(enumerate(row, 1))
             for formation, rows in generator._DEFENSE_TEMPLATE.items()
             for subrow, row in enumerate(rows, 1)}
    generator._allocate_defense_interceptions(
        cells, generator._DEFENSE_INTERCEPTION_NEUTRAL_RATE,
    )
    return cells


def test_shared_pressure_makes_low_source_target_attainable_and_replays(tmp_path) -> None:
    stats, samples = _source()
    with pytest.raises(ValueError, match="QT.*attainable"):
        generator.generate_team_charts(stats, tmp_path / "old", empirical=samples,
                                       calibrate_empirical_pass_events=True)

    model = generator.resolve_cohort_pressure([(stats, samples)], seed=8306)
    assert model.evidence["moves"]
    assert model.evidence["attained_neutral_qt"] <= model.evidence["source_ceiling"]
    generator.generate_team_charts(
        stats, tmp_path / "resolved", empirical=samples,
        calibrate_empirical_pass_events=True, neutral_pressure=model,
    )
    chart = load_team_chart(tmp_path / "resolved")
    defense = DefenseChart(model.defense)
    sacks, dropbacks = Fraction(), Fraction()
    for formation, weight in zip(DefenseType, (22, 12, 16, 20, 14, 16)):
        for call, call_weight in zip(
            (PlayType.SCREEN, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
             PlayType.LONG_PASS, PlayType.TE_SHORT_LONG), (8, 22, 16, 6, 4),
        ):
            for outcome, probability in resolved_outcome_distribution(
                chart, defense, call, formation,
            ).items():
                mass = probability * weight * call_weight / 5600
                if outcome.kind == "sack":
                    sacks += mass
                if outcome.kind not in {"pending_penalty", "qb_scramble"}:
                    dropbacks += mass
    assert float(sacks / dropbacks) == pytest.approx(.04, abs=.006)


def test_pressure_relocation_preserves_tokens_and_protected_strength_cells() -> None:
    model = generator.resolve_cohort_pressure([_source()], seed=8306)
    before = _neutral()
    for formation in "ABCDEF":
        for column in range(1, 10):
            assert Counter(model.defense[(formation, row)][column] for row in range(1, 6)) == (
                Counter(before[(formation, row)][column] for row in range(1, 6))
            )
    protected = {(formation, 5, column) for formation, column in (
        *generator._DEFENSE_INTERCEPTION_BASE_CELLS,
        *generator._DEFENSE_INTERCEPTION_ADD_CELLS,
        *generator._DEFENSE_INTERCEPTION_REMOVE_CELLS,
    )} | {("D", 3, 8), ("F", 2, 7)}
    for (formation, row), columns in before.items():
        for column, cell in columns.items():
            if column <= 4 or (formation, row, column) in protected or (
                cell not in {"QT", "BLACK"} and not cell.lstrip("+-").isdigit()
            ):
                assert model.defense[(formation, row)][column] == cell


def test_pressure_procedure_is_order_invariant_and_deterministic() -> None:
    low, samples = _source()
    high = replace(low, team_name="Synthetic High Pressure", offense=replace(
        low.offense, passing=replace(low.offense.passing, sacks=100),
    ))
    first = generator.resolve_cohort_pressure([(low, samples), (high, samples)], seed=8306)
    second = generator.resolve_cohort_pressure([(high, samples), (low, samples)], seed=8306)
    assert first == second
    renamed = replace(low, team_name="Another Synthetic Name", season=2027)
    assert generator.resolve_cohort_pressure([(renamed, samples)], seed=8306).defense == (
        generator.resolve_cohort_pressure([(low, samples)], seed=8306).defense
    )


def test_feasible_cohort_keeps_current_neutral_template() -> None:
    model = generator.resolve_cohort_pressure([_source(sacks=100)], seed=8306)
    assert model.evidence["moves"] == []
    assert model.defense == _neutral()


def test_extreme_target_cannot_erase_protected_qt_or_clamp_source() -> None:
    with pytest.raises(ValueError, match="pressure.*(infeasible|attainable|relocation)"):
        generator.resolve_cohort_pressure([_source(sacks=1, attempts=10000)], seed=8306)


def test_pressure_model_preserves_source_defense_strength() -> None:
    stats, samples = _source()
    model = generator.resolve_cohort_pressure([(stats, samples)], seed=8306)
    strong = replace(stats, defense=replace(stats.defense, passing=replace(
        stats.defense.passing, sacks=120,
    )))
    weak = replace(stats, defense=replace(stats.defense, passing=replace(
        stats.defense.passing, sacks=10,
    )))
    strong_cells = generator._generate_defense(strong, neutral_pressure=model)
    weak_cells = generator._generate_defense(weak, neutral_pressure=model)
    assert strong_cells[("D", 3)][8] == "QT"
    assert weak_cells[("D", 3)][8] != "QT"
    assert strong_cells[("F", 2)][7] == "QT"
    assert weak_cells[("F", 2)][7] != "QT"


def test_cohort_without_qt_observations_discloses_default_model() -> None:
    stats, _ = _source()
    model = generator.resolve_cohort_pressure([(stats, EmpiricalChartData())], seed=8306)
    assert model.defense == _neutral()
    assert model.evidence["constraints"] == []
    assert model.evidence["unconstrained_teams"] == [stats.team_name]


def test_source_sacks_without_conditional_support_still_fail() -> None:
    stats, samples = _source()
    samples = replace(samples, offense={**samples.offense, "qb_time": ("5",) * 100})
    with pytest.raises(ValueError, match="QT.*sack"):
        generator.resolve_cohort_pressure([(stats, samples)], seed=8306)


@pytest.mark.parametrize("fumble", ["F+2", "F + 2"])
def test_cohort_constraints_use_semantic_fumble_gain(fumble: str) -> None:
    stats, samples = _source()
    samples = replace(samples, offense={
        **samples.offense, "qb_time": ("-6",) * 50 + (fumble,) * 50,
    })
    model = generator.resolve_cohort_pressure([(stats, samples)], seed=8306)
    assert model.evidence["constraints"]
    assert all(item["conditional_sack_probability"] == pytest.approx(.5, abs=.02)
               for item in model.evidence["constraints"])


@pytest.mark.parametrize("source_sacks", [35, 40])
def test_low_source_pressure_reserves_interception_destinations_and_screen_costs(
    tmp_path, source_sacks: int,
) -> None:
    """Fresh pressure allocation must not put QT into future interception cells."""
    stats, samples = _source(sacks=source_sacks, attempts=1000 - source_sacks)
    high = replace(stats, defense=replace(stats.defense, passing=replace(
        stats.defense.passing, interceptions=60,
    )))
    model = generator.resolve_cohort_pressure([(high, samples)], seed=8306)
    assert model.evidence["moves"]
    assert model.evidence["attained_neutral_qt"] <= model.evidence["source_ceiling"]
    destinations = {("B", 5, 6), ("C", 5, 6), ("F", 5, 7)}
    for formation, row, column in destinations:
        assert model.defense[(formation, row)][column] == "BLACK"
    assert not any((move["formation"], move["to_subrow"], move["column"]) in destinations
                   for move in model.evidence["moves"])

    generator.generate_team_charts(
        high, tmp_path, empirical=samples, calibrate_empirical_pass_events=True,
        neutral_pressure=model,
    )
    defense = load_team_chart(tmp_path).defense.modifiers
    for formation in "BCF":
        for row in range(1, 6):
            assert defense[(formation, row)][5] == model.defense[(formation, row)][5]
    for key, columns in model.defense.items():
        for column, cell in columns.items():
            if cell == "QT":
                assert defense[key][column] == cell
    for formation, row, column in destinations:
        assert defense[(formation, row)][column].startswith("INT")
    assert generator._neutral_qt_probability(defense) == generator._neutral_qt_probability(
        model.defense,
    )
