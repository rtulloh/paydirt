"""Public-only, deterministic asset boundary for the FLOW-033 browser spike."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_browser_spike.py"


def builder() -> ModuleType:
    """Load the standalone builder through its normal namespace import."""
    return importlib.import_module("scripts.build_browser_spike")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    module = builder()
    root = tmp_path / "source"
    for relative in module.PUBLIC_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic public content: {relative}\n".encode())
    for relative in (
        "seasons/1983/Private/offense.csv", "seasons/2026/Private/offense.csv",
        "seasons/2026/Ironclads/private-notes.txt", ".ai-audits/private.json",
        "paydirt/private_export.py", "paydirt_save.json",
        "docs/images/private.png", "paydirt-web/backend/main.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SECRET MUST NEVER BE PUBLISHED")
    return root


def test_builder_cli_exposes_output_option() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output" in completed.stdout


def test_archive_is_exact_public_allowlist_with_verified_manifest(source: Path, tmp_path: Path) -> None:
    module = builder()
    output = tmp_path / "bundle"
    manifest = module.build_bundle(source, output)
    archive_bytes = (output / "python.zip").read_bytes()
    saved = json.loads((output / "manifest.json").read_text())
    assert manifest == saved
    assert saved["version"] == 1
    assert saved["scope"] == "public-released-seasons"
    assert saved["seasons"] == {year: list(teams) for year, teams in module.PUBLIC_SEASONS.items()}
    assert saved["files"] == [{
        "url": "python.zip", "mount": "/app", "bytes": len(archive_bytes),
        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
    }]
    with zipfile.ZipFile(output / "python.zip") as archive:
        assert archive.namelist() == sorted(module.PUBLIC_FILES)
        inventory = []
        for name in archive.namelist():
            data = archive.read(name)
            assert data == (source / name).read_bytes()
            assert b"SECRET" not in data
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            inventory.append({
                "path": name, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        assert saved["inventory"] == inventory
    assert sorted(path.name for path in output.iterdir()) == ["manifest.json", "python.zip"]


def test_archive_is_reproducible_even_when_source_mtime_changes(source: Path, tmp_path: Path) -> None:
    import os

    module = builder()
    first, second = tmp_path / "first", tmp_path / "second"
    module.build_bundle(source, first)
    for relative in module.PUBLIC_FILES:
        os.utime(source / relative, (1800000000, 1800000000))
    module.build_bundle(source, second)
    for name in ("manifest.json", "python.zip"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    module.build_bundle(source, second)
    assert (first / "python.zip").read_bytes() == (second / "python.zip").read_bytes()


def test_missing_allowlisted_file_fails_before_output_is_created(source: Path, tmp_path: Path) -> None:
    module = builder()
    (source / "paydirt/game_engine.py").unlink()
    output = tmp_path / "bundle"
    with pytest.raises(ValueError, match="Missing public asset"):
        module.build_bundle(source, output)
    assert not output.exists()


@pytest.mark.parametrize("directory", [False, True])
def test_source_symlinks_are_rejected(source: Path, tmp_path: Path, directory: bool) -> None:
    module = builder()
    asset = source / ("docs" if directory else "LICENSE")
    target = tmp_path / ("external-docs" if directory else "external-license")
    asset.rename(target)
    asset.symlink_to(target, target_is_directory=directory)
    output = tmp_path / "bundle"
    with pytest.raises(ValueError, match="Symlink"):
        module.build_bundle(source, output)
    assert not output.exists()


@pytest.mark.parametrize("relative", [".", "paydirt", "seasons/2026", "docs"])
def test_output_cannot_overwrite_source_tree(source: Path, relative: str) -> None:
    module = builder()
    with pytest.raises(ValueError, match="Unsafe output"):
        module.build_bundle(source, source / relative)
    assert not (source / "python.zip").exists()


def test_default_audit_output_is_allowed(source: Path) -> None:
    module = builder()
    output = source / ".ai-audits/browser-spike/staging"
    module.build_bundle(source, output)
    assert (output / "manifest.json").is_file()


def test_output_directory_with_unexpected_files_is_rejected(source: Path, tmp_path: Path) -> None:
    module = builder()
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "important.txt").write_text("retain me")
    with pytest.raises(ValueError, match="Unexpected output"):
        module.build_bundle(source, output)
    assert (output / "important.txt").read_text() == "retain me"


def test_output_symlink_is_rejected(source: Path, tmp_path: Path) -> None:
    module = builder()
    target = tmp_path / "external"
    target.mkdir()
    output = tmp_path / "bundle"
    output.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        module.build_bundle(source, output)
    assert list(target.iterdir()) == []


def test_output_asset_symlink_is_rejected(source: Path, tmp_path: Path) -> None:
    module = builder()
    output = tmp_path / "bundle"
    output.mkdir()
    target = tmp_path / "important"
    target.write_text("retain me")
    (output / "python.zip").symlink_to(target)
    with pytest.raises(ValueError, match="Symlink"):
        module.build_bundle(source, output)
    assert target.read_text() == "retain me"


def test_public_allowlist_contains_exact_released_seasons() -> None:
    module = builder()
    assert {year: len(teams) for year, teams in module.PUBLIC_SEASONS.items()} == {
        "1977": 28, "1983": 28, "2024": 32, "2026": 2,
    }
    expected = set()
    for year, teams in module.PUBLIC_SEASONS.items():
        assert len(teams) == len(set(teams))
        expected.add(f"seasons/{year}/{year}.yaml")
        for team in teams:
            expected.update(f"seasons/{year}/{team}/{name}" for name in (
                "team.yaml", "offense.csv", "defense.csv", "special.csv", "roster.json",
            ))
    expected.update({
        "seasons/1977/NOTES.md", "seasons/1977/generation-manifest.json",
        "seasons/1983/ATTRIBUTION.md", "seasons/1983/generation-manifest.json",
        "seasons/1983/chart-audit.json", "seasons/2024/ATTRIBUTION.md",
        "seasons/2024/generation-manifest.json", "seasons/2024/chart-audit.json",
        "seasons/2026/ai_behavior.yaml",
    })
    assert {name for name in module.PUBLIC_FILES if name.startswith("seasons/")} == expected
    assert len(module.PUBLIC_FILES) == len(set(module.PUBLIC_FILES))
    assert "paydirt-web/backend/http_adapter.py" not in module.PUBLIC_FILES
    assert all(not name.startswith((".ai-audits/", "private-data/")) for name in module.PUBLIC_FILES)


def test_cli_builds_default_output(source: Path, capsys: pytest.CaptureFixture) -> None:
    module = builder()
    assert module.main(["--source-root", str(source)]) == 0
    assert (source / ".ai-audits/browser-spike/staging/manifest.json").is_file()
    assert f"{len(module.PUBLIC_FILES)} public files" in capsys.readouterr().out


def test_cli_reports_invalid_output(source: Path, capsys: pytest.CaptureFixture) -> None:
    module = builder()
    with pytest.raises(SystemExit) as error:
        module.main(["--source-root", str(source), "--output", str(source)])
    assert error.value.code == 2
    assert "Unsafe output" in capsys.readouterr().err


def test_output_cannot_be_an_existing_file(source: Path, tmp_path: Path) -> None:
    module = builder()
    output = tmp_path / "important-file"
    output.write_text("retain me")
    with pytest.raises(ValueError, match="not a directory"):
        module.build_bundle(source, output)
    assert output.read_text() == "retain me"


def test_output_cannot_use_symlink_parent(source: Path, tmp_path: Path) -> None:
    module = builder()
    target = tmp_path / "external-parent"
    target.mkdir()
    parent = tmp_path / "linked-parent"
    parent.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        module.build_bundle(source, parent / "bundle")
    assert list(target.iterdir()) == []


def test_season_runtime_dependencies_are_explicitly_packaged() -> None:
    """A static browser must have the same save/campaign operations as native."""
    required = {
        "paydirt/campaigns.py", "paydirt/campaign_simulation.py", "paydirt/auto_game.py",
        "paydirt-web/backend/campaign_operations.py", "paydirt-web/backend/checkpoints.py",
        "config/season-schedules/1983.json", "config/season-schedules/2024.json",
    }
    assert required <= set(builder().PUBLIC_FILES)



def test_browser_bundle_includes_authoritative_kicking_statistics_module():
    assert 'paydirt/kicking_stats.py' in builder().PUBLIC_FILES



def test_browser_bundle_includes_offensive_efficiency_module():
    assert 'paydirt/offense_stats.py' in builder().PUBLIC_FILES


def test_extended_team_stats_module_is_in_public_worker_allowlist():
    assert "paydirt/team_stats.py" in builder().PUBLIC_FILES
