"""Synthetic controls for defensive interception allocation and tactical costs."""

from collections import Counter
from dataclasses import replace

import pytest

from paydirt import chart_generator as generator
from paydirt.chart_generator import TeamSeasonStats
from paydirt.play_resolver import defense_subrow_weights


def _source(interceptions: int) -> TeamSeasonStats:
    """Use neutral efficiency and pressure to isolate interception strength."""
    return TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Synthetic Coverage",
        "defense": {
            "passing": {"attempts": 1000, "yards": 7200, "sacks": 65,
                        "interceptions": interceptions},
            "rushing": {"attempts": 1000, "yards": 4100},
        },
    })


def _weighted_tokens(defense: dict[tuple[str, int], dict[int, str]],
                     formation: str, column: int) -> Counter[str]:
    return Counter({cell: sum(weight for row, weight in defense_subrow_weights().items()
                              if defense[(formation, row)][column] == cell)
                    for cell in {defense[(formation, row)][column] for row in range(1, 6)}})


def test_high_interception_strength_retains_screen_counterplay() -> None:
    """Turnover strength must retain the template's parenthesized Screen costs."""
    neutral = generator._generate_defense(_source(25))
    strong = generator._generate_defense(_source(60))
    for formation in "BCF":
        assert _weighted_tokens(strong, formation, 5) == _weighted_tokens(neutral, formation, 5)


def test_interception_saturation_does_not_intercept_one_call_in_every_formation() -> None:
    """The bounded strength budget must not consume all six Screen counters."""
    defense = generator._generate_defense(_source(60))
    for column in range(5, 10):
        assert not all(defense[(formation, 5)][column].startswith("INT")
                       for formation in "ABCDEF"), column


@pytest.mark.parametrize("interceptions,expected_units", [(0, 0), (23, 1), (25, 2),
                                                         (27, 3), (43, 11), (60, 17),
                                                         (100, 17)])
def test_interception_strength_retains_rare_monotone_budget(
    interceptions: int, expected_units: int,
) -> None:
    """Count physical defensive mass without treating calls as a usage model."""
    defense = generator._generate_defense(_source(interceptions))
    hits = [(formation, row, column) for (formation, row), cells in defense.items()
            for column, cell in cells.items() if cell.startswith("INT")]
    assert len(hits) == expected_units
    assert all(row == 5 and 5 <= column <= 9 for _, row, column in hits)
    assert sum(defense_subrow_weights()[row] for _, row, _ in hits) == expected_units


@pytest.mark.parametrize("interceptions", [0, 25, 43, 60, 100])
def test_interception_strength_preserves_other_tactical_result_families(interceptions: int) -> None:
    """Run, pressure, replacement and touchdown structures have separate purposes."""
    neutral = generator._generate_defense(_source(25))
    candidate = generator._generate_defense(_source(interceptions))
    for (formation, row), cells in neutral.items():
        for column, cell in cells.items():
            if column <= 4 or row != 5 or cell == "QT" or cell.startswith("("):
                assert candidate[(formation, row)][column] == cell, (formation, row, column)


def test_interception_allocation_retains_name_independence_and_nested_strength() -> None:
    """No name-seeded decoration may stand in for source defense strength."""
    previous: set[tuple[str, int]] = set()
    for interceptions in range(101):
        source = _source(interceptions)
        defense = generator._generate_defense(source)
        assert generator._generate_defense(replace(source, team_name="Another Synthetic Team")) == defense
        current = {(formation, column) for (formation, row), cells in defense.items()
                   for column, cell in cells.items() if cell.startswith("INT")}
        assert previous <= current
        previous = current


@pytest.mark.parametrize("interceptions,expected_by_formation", [
    (25, [0, 0, 0, 1, 1, 0]),
    (43, [1, 1, 1, 4, 3, 1]),
    (60, [2, 2, 2, 5, 4, 2]),
])
def test_interception_allocation_preserves_each_formation_strength_budget(
    interceptions: int, expected_by_formation: list[int],
) -> None:
    defense = generator._generate_defense(_source(interceptions))
    for formation, expected in zip("ABCDEF", expected_by_formation):
        assert sum(defense[(formation, row)][column].startswith("INT")
                   * defense_subrow_weights()[row]
                   for row in range(1, 6) for column in range(5, 10)) == expected


def test_screen_counterplay_survives_real_priority_and_secondary_resolution() -> None:
    from paydirt.chart_loader import DefenseChart
    from paydirt.chart_tactics_audit import controlled_offense, resolved_outcome_distribution
    from paydirt.play_resolver import DefenseType, PlayType

    neutral = DefenseChart(generator._generate_defense(_source(25)))
    strong = DefenseChart(generator._generate_defense(_source(60)))
    for formation in DefenseType:
        if formation.value not in "BCF":
            continue
        for token in ("10", "(7)", "B", "QT", "INT 8", "F + 2", "OFF 5"):
            offense = controlled_offense(token)
            assert resolved_outcome_distribution(offense, strong, PlayType.SCREEN, formation) == (
                resolved_outcome_distribution(offense, neutral, PlayType.SCREEN, formation)
            )
