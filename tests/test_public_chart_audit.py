"""Public chart CI checks need committed charts only and retain honest scope."""
import shutil
from pathlib import Path

import pytest

from paydirt import chart_audit


def run(path: Path, teams: int = 2) -> dict:
    function = getattr(chart_audit, "audit_public_season", None)
    assert callable(function), "Public structural and decoder audit must be separate from private source proof"
    return function(path, expected_teams=teams)


@pytest.fixture
def public_season(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "seasons/2026", tmp_path / "2026")
    return tmp_path / "2026"


def test_public_charts_validate_without_source_or_manifest(public_season: Path) -> None:
    result = run(public_season)
    assert result["passed"], result["errors"]
    assert result["team_count"] == 2 and len(result["decoder"]) == 2
    assert result["source_reproduction_checked"] is False
    assert result["historical_accuracy_checked"] is False
    assert result["release_certified"] is False


def test_public_audit_rejects_missing_cohort_member(public_season: Path) -> None:
    shutil.rmtree(public_season / "Ironclads")
    result = run(public_season)
    assert not result["passed"] and result["errors"]


def test_public_audit_rejects_decoder_duplicate_rows(public_season: Path) -> None:
    path = public_season / "Ironclads/offense.csv"
    rows = path.read_text().splitlines()
    path.write_text("\n".join([*rows, rows[1]]) + "\n")
    result = run(public_season)
    assert not result["passed"]
    assert any("duplicate physical row" in error for error in result["errors"])


def test_public_audit_rejects_invalid_engine_symbol(public_season: Path) -> None:
    path = public_season / "Ironclads/special.csv"
    rows = path.read_text().splitlines()
    row = rows[1].split(",")
    row[6] = "INVALID"
    rows[1] = ",".join(row)
    path.write_text("\n".join(rows) + "\n")
    with pytest.warns(UserWarning, match="unreadable cell"):
        result = run(public_season)
    assert not result["passed"] and result["errors"]


def test_public_audit_requires_fully_supported_decoder(public_season: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = chart_audit.audit_chart_decoder

    def with_fallback(path: Path) -> dict:
        result = original(path)
        result.update(fully_supported=False, limitations=["Known engine default requires explicit authored gain"])
        return result

    monkeypatch.setattr(chart_audit, "audit_chart_decoder", with_fallback)
    result = run(public_season)
    assert not result["passed"]
    assert any("decoder" in error for error in result["errors"])
