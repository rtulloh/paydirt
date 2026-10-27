"""Project permissions allow validation, not arbitrary Python or destructive Git."""

import json
from fnmatch import fnmatchcase
from pathlib import Path

import pytest


@pytest.mark.parametrize("command,expected", [
    ("python3 tests/run_ai_audit.py", "allow"),
    ("python3 tests/run_ai_audit.py --season 2026 --compare-balanced", "allow"),
    ("python3 tests/run_all_games.py", "allow"),
    ("python3 tests/run_full_season.py", "allow"),
    ("python3 -m pytest tests/ -q", "allow"),
    ("ruff check paydirt/ tests/ paydirt-web/backend/", "allow"),
    ("npm run test:coverage -- --run", "allow"),
    ("npm run test:e2e", "allow"),
    ("npm run build", "allow"),
    ("git status --short", "allow"),
    ("git push origin main", "ask"),
    ("python3 arbitrary_script.py", "ask"),
    ("git reset --hard", "deny"),
    ("git checkout -- paydirt/game_engine.py", "deny"),
    ("rm -rf seasons", "deny"),
])
def test_project_shell_permissions(command: str, expected: str) -> None:
    config_path = Path(__file__).resolve().parents[1] / "opencode.json"
    config = json.loads(config_path.read_text())
    assert "permission" not in config  # Use the documented V2 permissions array.
    effect = "ask"
    for rule in config["permissions"]:
        pattern = rule["resource"]
        if rule["action"] == "shell" and (
            fnmatchcase(command, pattern)
            or (pattern.endswith(" *") and command == pattern[:-2])
        ):
            effect = rule["effect"]
    assert effect == expected
