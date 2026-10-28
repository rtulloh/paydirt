"""Private standings backups must not become accidental commit candidates."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / ".gitignore", tmp_path / ".gitignore")
    return tmp_path


@pytest.mark.parametrize("path,ignored", [
    ("standings_data/season_2026.json", True),
    ("standings_data.save/season_2026.json", True),
    ("standings_data.backup/season_2026.json", True),
    ("standings_data_2026/season_2026.json", True),
    ("standings_database.py", False),
    ("tests/test_standings.py", False),
    ("seasons/2026/2026.yaml", False),
])
def test_standings_directory_and_backup_privacy(
    repository: Path, path: str, ignored: bool,
) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", path],
        cwd=repository, capture_output=True, text=True, check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    assert (result.returncode == 0) is ignored
