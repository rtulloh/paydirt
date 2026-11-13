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
    ("python3 -m pytest", "allow"),
    (".venv/bin/python3.12 -m pytest tests/ -q -o addopts= --tb=short", "allow"),
    (".venv/bin/python3.12 -m pytest", "allow"),
    (".venv/bin/python3 -m pytest tests/test_run_full_regression_script.py", "allow"),
    ("pytest tests/", "allow"),
    ("pytest", "allow"),
    (".venv/bin/pytest tests/ -q", "allow"),
    (".venv/bin/python3.12 scripts/run_full_regression.py --only browser", "allow"),
    (".venv/bin/python3.12 tests/run_ai_audit.py --season 2026", "allow"),
    ("python3 e2e/serve_backend.py --port 18000", "allow"),
    ("PAYDIRT_E2E_BACKEND_PORT=18000 PAYDIRT_E2E_FRONTEND_PORT=15173 npm run test:e2e", "allow"),
    ("npx playwright test e2e/charts.spec.js", "allow"),
    ("npx playwright install chromium", "allow"),
    ("ruff check paydirt/ tests/ paydirt-web/backend/", "allow"),
    ("python3 -m ruff check paydirt/ tests/", "allow"),
    ("python3 scripts/run_full_regression.py --list", "allow"),
    ("python3 scripts/run_full_regression.py", "allow"),
    ("npm run test:coverage -- --run", "allow"),
    ("npm run test:e2e", "allow"),
    ("npx test -- --run", "allow"),
    ("npx test", "allow"),
    ("npm run build", "allow"),
    ("git status --short", "allow"),
    ("git ls-remote", "allow"),
    ("git ls-remote --tags origin refs/tags/v1.9.5", "allow"),
    ("git ls-remote-other origin", "ask"),
    ("git ls-files", "allow"),
    ("git ls-files -v tests/run_all_games.py pyproject.toml", "allow"),
    ("git ls-files-other", "ask"),
    ("git checkout-index", "allow"),
    ("git checkout-index --all --prefix=/path/to/snapshot/", "allow"),
    ("git checkout-index --all --force --prefix=/path/to/snapshot/", "allow"),
    ("git checkout-index-other", "ask"),
    ("git remote", "ask"),
    ("git remote -v", "ask"),
    ("git remote-other", "ask"),
    ("gh", "deny"),
    ("gh --version", "deny"),
    ("gh run view 40724905123", "deny"),
    ("gh-other", "ask"),
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
