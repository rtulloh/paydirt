"""Public-only coverage checks for the reusable chart release audit."""

import shutil
from pathlib import Path

import pytest

from paydirt.chart_audit import audit_season


def test_audit_reports_corrupt_cells_and_missing_rows(tmp_path):
    source = Path('seasons/2026')
    shutil.copytree(source, tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/offense.csv'
    rows = path.read_text().splitlines()
    cells = rows[1].split(',')
    cells[1] = '150'
    cells[2] = 'NOT_A_RESULT'
    rows[1] = ','.join(cells)
    path.write_text('\n'.join(rows[:-1]) + '\n')
    report = audit_season(tmp_path / '2026')
    assert not report['passed']
    errors = '\n'.join(report['errors'])
    assert 'Ironclads' in errors
    assert '150' in errors
    assert 'NOT_A_RESULT' in errors
    assert '39' in errors


def test_audit_measures_features_and_uses_no_private_fixtures():
    report = audit_season(Path('seasons/2026'))
    assert report['passed'], report['errors']
    assert report['team_count'] == 2
    assert report['features']['special_teams.punt']['penalty'] > 0
    assert report['features']['special_teams.punt']['marked'] > 0
    assert report['features']['offense.line_plunge']['numeric'] > 0
    assert 'defense.1' in report['features']


def test_audit_measures_offense_and_defense_through_priority_rules():
    report = audit_season(Path('seasons/2026'))
    matrix = report['combined_primary_rates']
    assert len(matrix) == 54
    assert set(matrix['short_pass/D']) >= {'incomplete', 'interception'}
    assert matrix['long_pass/F']['pressure'] > 0
    assert sum(matrix['short_pass/D'].values()) == pytest.approx(1.0)


def test_primary_rate_audit_cannot_reclassify_selected_fumble_as_interception():
    from paydirt.chart_audit import _combined_primary_rates
    from paydirt.chart_tactics_audit import controlled_offense

    team = controlled_offense("F + 2")
    team.defense.modifiers = {(formation, row): dict.fromkeys(range(1, 10), "INT 5")
                              for formation in "ABCDEF" for row in range(1, 6)}
    matrix = _combined_primary_rates([team])
    assert len(matrix) == 54
    assert all(rates == {"fumble": 1.0} for rates in matrix.values())


def test_audit_includes_exact_all_team_primary_secondary_and_special_mass():
    report = audit_season(Path('seasons/2026'))
    exact = report.get("exact_mechanics", {})
    assert set(exact) == {"Ironclads", "Thunderhawks"}
    for team in exact.values():
        assert len(team["plays"]) == 54
        assert team["physical_primary_combinations"] == 54 * 216 * 36 * 2
        assert team["special_teams"]["field_goal"]["by_distance"]
        assert team["recovery"]["retained"] + team["recovery"]["lost"] == pytest.approx(1)
        for play in team["plays"].values():
            assert sum(play["probabilities"].values()) == pytest.approx(1)
            assert play["exact_total_mass"] == [1, 1]


@pytest.mark.parametrize("token,expected", [("B", "breakaway:25"), ("QT", "sack:-6"),
                                           ("F + 2", "pending_fumble:2")])
def test_exact_report_conditions_secondary_and_recovery_branches(token, expected, monkeypatch):
    from dataclasses import replace

    import paydirt.chart_audit as audit
    from paydirt.chart_tactics_audit import controlled_offense

    team = controlled_offense(token)
    team.defense.modifiers = {(formation, row): dict.fromkeys(range(1, 10), "0")
                              for formation in "ABCDEF" for row in range(1, 6)}
    # Keep the test at the public loading boundary, supplying synthetic charts.
    monkeypatch.setattr(audit, "load_team_chart", lambda path: replace(team, team_dir=str(path)))
    report = audit.audit_season(Path('seasons/2026'), strict=False)
    exact = report.get("exact_mechanics", {})
    assert exact, "exact physical mechanics evidence is missing"
    assert exact["Ironclads"]["plays"]["short_pass/A"]["probabilities"] == {expected: 1.0}


def test_legacy_blank_rows_count_as_engine_zero_defaults(tmp_path):
    shutil.copytree(Path('seasons/2026'), tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/offense.csv'
    rows = path.read_text().splitlines()
    path.write_text('\n'.join(rows[:-1]) + '\n# Recovered,10-27\n# Lost,28-39\n')
    strict = audit_season(tmp_path / '2026')
    assert not strict['passed']
    legacy = audit_season(tmp_path / '2026', strict=False)
    assert legacy['passed']
    assert legacy['legacy_blank_cells'] > 0
    assert sum(legacy['combined_primary_rates']['line_plunge/A'].values()) == pytest.approx(1)


def test_audit_rejects_guaranteed_run_touchdowns(tmp_path):
    shutil.copytree(Path('seasons/2026'), tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/offense.csv'
    rows = path.read_text().splitlines()
    cells = rows[1].split(',')
    cells[1] = 'TD'
    rows[1] = ','.join(cells)
    path.write_text('\n'.join(rows) + '\n')
    report = audit_season(tmp_path / '2026')
    assert not report['passed']
    assert any('guaranteed run touchdown' in error for error in report['errors'])


def test_returns_can_include_yards_from_inside_the_end_zone(tmp_path):
    shutil.copytree(Path('seasons/2026'), tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/special.csv'
    rows = path.read_text().splitlines()
    cells = rows[1].split(',')
    cells[2] = '109'
    cells[5] = '100'
    rows[1] = ','.join(cells)
    path.write_text('\n'.join(rows) + '\n')
    report = audit_season(tmp_path / '2026')
    assert report['passed'], report['errors']


@pytest.mark.parametrize('recovered,lost', [
    ('10-28', '28-39'),  # A roll cannot both retain and lose possession.
    ('10-26', '28-39'),  # Every physical roll needs a recovery outcome.
    ('9-27', '28-39'),
    ('27-10', '28-39'),
])
def test_audit_rejects_ambiguous_or_invalid_fumble_ranges(tmp_path, recovered, lost):
    shutil.copytree(Path('seasons/2026'), tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/offense.csv'
    with path.open('a') as target:
        target.write(f'# Recovered,{recovered}\n# Lost,{lost}\n')
    report = audit_season(tmp_path / '2026')
    assert not report['passed']
    assert any('fumble recovery' in error for error in report['errors'])


@pytest.mark.parametrize('recovered,lost', [('0-0', '10-39'), ('10-39', '0-0')])
def test_audit_allows_zero_or_complete_fumble_loss_rate(tmp_path, recovered, lost):
    shutil.copytree(Path('seasons/2026'), tmp_path / '2026')
    path = tmp_path / '2026/Ironclads/offense.csv'
    rows = path.read_text().splitlines()
    for index in range(1, len(rows)):
        cells = rows[index].split(',')
        cells[12] = 'L' if recovered == '0-0' else 'R'
        rows[index] = ','.join(cells)
    path.write_text('\n'.join(rows) + '\n')
    with path.open('a') as target:
        target.write(f'# Recovered,{recovered}\n# Lost,{lost}\n')
    report = audit_season(tmp_path / '2026')
    assert report['passed'], report['errors']


@pytest.mark.parametrize("trigger,column,cell,low,high", [
    ("QT", "qb_time", "OFF 5", -5, 10),
    ("B", "breakaway", "DEF 5", 15, 40),
])
def test_exact_secondary_fallback_matches_real_resolver(trigger, column, cell, low, high):
    from unittest.mock import patch

    from paydirt.chart_audit import _exact_team_mechanics
    from paydirt.chart_tactics_audit import controlled_offense
    from paydirt.play_resolver import resolve_breakaway, resolve_qb_scramble

    team = controlled_offense(trigger)
    team.defense.modifiers = {(formation, row): dict.fromkeys(range(1, 10), "0")
                              for formation in "ABCDEF" for row in range(1, 6)}
    setattr(team.offense, column, dict.fromkeys(range(10, 40), cell))
    # These chart symbols invoke the core's documented random fallback. They
    # cannot be silently counted as a penalty, zero yards or missing mass.
    resolver = resolve_qb_scramble if trigger == "QT" else resolve_breakaway
    with patch("paydirt.play_resolver.random.randint", return_value=low) as rng:
        assert resolver(team.offense, 20).yards == low
        rng.assert_called_once_with(low, high)
    result = _exact_team_mechanics(team, [team])["plays"]["short_pass/A"]
    assert result["exact_total_mass"] == [1, 1]
    assert result["secondary_fallback_probability"] == 1
    assert len(result["probabilities"]) == high - low + 1
    assert set(result["probabilities"].values()) == {1 / (high - low + 1)}
    assert result["conditional_known_numeric_mean"] == (low + high) / 2


@pytest.mark.parametrize("filename,column,cell", [
    ("offense.csv", 11, "OFF 5"), ("offense.csv", 10, "BLACK"),
    ("offense.csv", 10, "F + 2"), ("special.csv", 2, "NG"),
    ("special.csv", 5, "BK -5"), ("special.csv", 6, "20*"),
])
def test_generated_gate_rejects_symbols_unsupported_in_that_column(tmp_path, filename, column, cell):
    shutil.copytree(Path("seasons/2026"), tmp_path / "2026")
    path = tmp_path / "2026/Ironclads" / filename
    rows = path.read_text().splitlines()
    values = rows[1].split(",")
    values[column] = cell
    rows[1] = ",".join(values)
    path.write_text("\n".join(rows) + "\n")
    report = audit_season(tmp_path / "2026")
    assert not report["passed"]
    assert any("unsupported" in error and "Ironclads" in error for error in report["errors"])


def test_exact_distance_curve_matches_weighted_real_field_goal_resolver():
    from unittest.mock import patch

    from paydirt.chart_audit import _exact_team_mechanics
    from paydirt.chart_tactics_audit import controlled_offense
    from paydirt.play_resolver import chart_roll_weights, resolve_field_goal_with_penalties

    team = controlled_offense("0")
    weights = chart_roll_weights()
    team.special_teams.field_goal = {roll: str(roll) for roll in weights}
    team.special_teams.field_goal[10] = "BK -7"
    team.special_teams.field_goal[11] = "F - 5"
    exact = _exact_team_mechanics(team, [team])["special_teams"]["field_goal"]
    for distance in (20, 40, 55, 65):
        mass = 0
        for roll, weight in weights.items():
            with patch("paydirt.play_resolver.roll_chart_dice", return_value=(roll, "synthetic")):
                result = resolve_field_goal_with_penalties(team.special_teams)
            if not result.is_blocked and not result.is_fumble and result.chart_yards >= distance - 17:
                mass += weight
        assert exact["by_distance"][str(distance)] == mass / 216
