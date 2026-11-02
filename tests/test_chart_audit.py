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
