"""Keep hosted test setup reproducible and dependency failures identifiable."""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def jobs() -> dict:
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
    return yaml.safe_load(workflow.read_text())["jobs"]


@pytest.mark.parametrize("job", ["test", "lint", "browser-games"])
def test_hosted_test_jobs_pin_supported_runner(jobs: dict, job: str) -> None:
    assert jobs[job]["runs-on"] == "ubuntu-24.04"


def test_python_matrix_keeps_all_versions_and_collects_independent_failures(jobs: dict) -> None:
    assert jobs["test"]["strategy"]["matrix"]["python-version"] == ["3.9", "3.10", "3.11", "3.12"]
    assert jobs["test"]["strategy"].get("fail-fast") is False


def test_browser_install_commands_are_separate_required_steps(jobs: dict) -> None:
    steps = jobs["browser-games"]["steps"]
    commands = [
        "python3 -m pip install -r ../backend/requirements.txt",
        "npm ci",
        "npx playwright install --with-deps chromium",
    ]
    indices = []
    for command in commands:
        matches = [(index, step) for index, step in enumerate(steps)
                   if step.get("run", "").strip() == command]
        assert len(matches) == 1, f"Dependency command needs its own step: {command}"
        index, step = matches[0]
        assert step.get("name")
        assert not step.get("continue-on-error", False)
        indices.append(index)
    assert indices == sorted(indices)
    assert steps[indices[-1] + 1]["run"] == "npm run test:coverage -- --run"
