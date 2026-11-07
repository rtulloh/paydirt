"""Independent audits retain F INC occurrence and its changed priority risk."""
from dataclasses import replace

import pytest

from paydirt.chart_audit import _decoder_cell_class, feature
from paydirt.chart_loader import DefenseChart
from paydirt.chart_tactics_audit import resolved_outcome_distribution
from paydirt.play_resolver import DefenseType, PlayType
from tests.test_chart_reference_contexts import trial
from tests.test_chart_reference_weighted import team


@pytest.mark.parametrize("context,calls", [("own1-first", 4), ("own40-first", 4),
                                         ("opp2-first", 4), ("own40-fourth", 1)])
def test_stateful_audit_counts_retained_joint_event_once(context: str, calls: int) -> None:
    result = trial(team("Offense", "F INC"), context)
    assert result["counts"]["retained_fumbles"] == calls
    assert result["official"]["pass_attempts"] == calls
    assert result["official"]["completions"] == 0
    assert result["home_stats"]["fumbles_lost"] == 0
    assert result["counts"]["turnover_on_downs"] == 1


@pytest.mark.parametrize("column", ["screen", "short_pass", "medium_pass", "long_pass", "te_short_long"])
def test_decoder_knows_primary_joint_token(column: str) -> None:
    assert _decoder_cell_class("offense", column, "F INC") == "supported"
    assert feature("F INC") == "retained_incompletion"


@pytest.mark.parametrize("unit,column", [("offense", "draw"), ("offense", "qb_time"),
                                         ("defense", "short_pass"),
                                         ("special_teams", "interception_return")])
def test_decoder_rejects_joint_token_in_other_consumers(unit: str, column: str) -> None:
    assert _decoder_cell_class(unit, column, "F INC") == "unsupported"


def test_exact_resolver_distribution_keeps_occurrence_separate_from_black() -> None:
    offense = team("Offense", "F INC")
    defense = DefenseChart({(formation, row): dict.fromkeys(range(1, 10), "0")
                            for formation in "ABCDEF" for row in range(1, 6)})
    joint = resolved_outcome_distribution(offense, defense, PlayType.SHORT_PASS, DefenseType.STANDARD)
    ordinary = resolved_outcome_distribution(
        replace(offense, offense=replace(offense.offense, short_pass=dict.fromkeys(range(10, 40), "BLACK"))),
        defense, PlayType.SHORT_PASS, DefenseType.STANDARD,
    )
    assert sum(joint.values()) == sum(ordinary.values()) == 1
    assert joint != ordinary
    assert all(outcome.detail == "retained_fumble_incompletion" for outcome in joint)
    assert all(outcome.kind == "incomplete" for outcome in joint)


@pytest.mark.parametrize("modifier,category", [("INT 12", "interception"), ("QT", "pressure"),
                                             ("(TD)", "touchdown"), ("0", "incomplete")])
def test_priority_delta_census_reports_every_formation_and_exact_signed_mass(
    modifier: str, category: str,
) -> None:
    from paydirt import chart_audit

    chart = team("Offense", "F INC")
    chart.defense = DefenseChart({(formation, row): dict.fromkeys(range(1, 10), modifier)
                                 for formation in "ABCDEF" for row in range(1, 6)})
    function = getattr(chart_audit, "retained_incompletion_priority_deltas", None)
    assert callable(function), "Every formation needs exact F INC versus BLACK priority deltas"
    report = function([chart])
    assert len(report["columns"]) == 30
    for row in report["columns"].values():
        denominator = row["physical_denominator"]
        assert row["joint_input_mass"] == denominator
        assert row["signed_event_mass"]["retained_incompletion"] == denominator
        assert row["signed_event_mass"][category] == -denominator
        assert sum(row["signed_event_mass"].values()) == 0


def test_season_audit_accepts_supported_joint_token_and_reports_delta(tmp_path) -> None:
    import shutil
    from pathlib import Path

    from paydirt.chart_audit import audit_season

    destination = tmp_path / "2026"
    shutil.copytree(Path("seasons/2026"), destination)
    path = destination / "Ironclads/offense.csv"
    rows = path.read_text().splitlines()
    cells = rows[1].split(",")
    cells[6] = "F INC"
    rows[1] = ",".join(cells)
    path.write_text("\n".join(rows) + "\n")
    report = audit_season(destination)
    assert report["passed"], report["errors"]
    assert report["retained_incompletion_priority_deltas"]["columns"]["short_pass/A"]["joint_input_mass"] > 0


def test_exact_chart_mechanics_keeps_joint_mass_separate_from_plain_incomplete() -> None:
    from paydirt.chart_audit import _exact_team_mechanics

    chart = team("Offense", "0")
    chart.offense.short_pass = dict.fromkeys(range(10, 40), "F INC")
    chart.defense = DefenseChart({(formation, row): dict.fromkeys(range(1, 10), "0")
                                 for formation in "ABCDEF" for row in range(1, 6)})
    report = _exact_team_mechanics(chart, [chart])
    assert report["plays"]["short_pass/A"]["probabilities"] == {"retained_fumble_incomplete:0": 1.0}


@pytest.mark.parametrize("settlement,expected", [("plain", 1), ("declined", 1),
                                                ("accepted", 0), ("offsetting", 0)])
def test_calibration_observer_counts_only_final_retained_occurrence(
    settlement: str, expected: int,
) -> None:
    from paydirt.chart_calibration import EngineCalibrationObserver
    from paydirt.game_engine import PaydirtGameEngine
    from tests.test_retained_fumble_incompletion import selected_cells

    game = PaydirtGameEngine(team("Offense"), team("Defense"))
    game.state.is_home_possession = True
    game.state.ball_position = 40
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
    cells = ("F INC",) if settlement == "plain" else ("OFF 5", "F INC")
    with selected_cells(cells, "DEF 5" if settlement == "offsetting" else "0"):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
        if outcome.pending_penalty_decision:
            outcome = game.apply_penalty_decision(outcome, accept_play=settlement == "declined")
    observer.on_result(game, outcome)
    totals = observer.team_totals(game.state.home_chart.peripheral.short_name).to_dict()
    assert totals["retained_fumble_incompletions"] == expected
    assert totals["pass_attempts"] == expected
    assert totals["completions"] == totals["rushing_attempts"] == 0
