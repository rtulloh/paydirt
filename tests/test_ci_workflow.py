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
    assert jobs["test"]["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12"]
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


ACTION_REFS = {
    "actions/checkout": "v7.0.1",
    "actions/setup-python": "v7.1.0",
    "actions/setup-node": "v7.1.0",
    "actions/upload-artifact": "v7.0.2",
    "actions/download-artifact": "v8.0.2",
    "codecov/codecov-action": "v7.1.1",
    "softprops/action-gh-release": "v3.0.3",
}


@pytest.mark.parametrize("filename", ["test.yml", "release.yml"])
def test_workflows_use_reviewed_node24_actions(filename: str) -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows" / filename).read_text())
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step:
                action, ref = step["uses"].split("@")
                assert ref == ACTION_REFS[action]


def test_coverage_upload_keeps_optional_status_and_uses_supported_input(jobs: dict) -> None:
    step = next(step for step in jobs["test"]["steps"]
                if step.get("uses", "").startswith("codecov/"))
    assert step["with"] == {"files": "./coverage.xml", "fail_ci_if_error": False}
    assert step["continue-on-error"] is True
    assert step["if"] == "matrix.python-version == '3.10'"


def test_runtime_upgrade_preserves_release_safety_and_artifact_layout(jobs: dict) -> None:
    root = Path(__file__).resolve().parents[1]
    release = yaml.safe_load((root / ".github/workflows/release.yml").read_text())
    release_jobs = release["jobs"]
    assert release_jobs["release"]["if"] == (
        "github.event_name == 'workflow_dispatch' || "
        "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/'))"
    )
    assert len(release_jobs["build"]["strategy"]["matrix"]["include"]) == 4
    download = release_jobs["release"]["steps"][0]
    assert download["with"] == {"path": "artifacts"}
    for job in release_jobs.values():
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/upload-artifact@"):
                assert step.get("with", {}).get("archive", True) is True
    setup = next(step for step in release_jobs["build"]["steps"]
                 if step.get("uses", "").startswith("actions/setup-node@"))
    assert setup["with"] == {"node-version": "24.22.1", "package-manager-cache": False}
    browser_setup = next(step for step in jobs["browser-games"]["steps"]
                         if step.get("uses", "").startswith("actions/setup-node@"))
    assert browser_setup["with"] == {
        "node-version": "24.22.1", "cache": "npm",
        "cache-dependency-path": "paydirt-web/frontend/package-lock.json",
    }


def test_ci_lint_is_required_and_covers_backend(jobs: dict) -> None:
    lint = jobs["lint"]
    assert not lint.get("continue-on-error", False)
    step = next(step for step in lint["steps"] if "ruff check" in step.get("run", ""))
    assert step["run"] == "ruff check paydirt/ tests/ paydirt-web/backend/"
    assert not step.get("continue-on-error", False)


def test_ci_backend_suite_is_required_and_installs_test_dependencies(jobs: dict) -> None:
    backend = jobs["backend"]
    assert backend["runs-on"] == "ubuntu-24.04"
    assert not backend.get("continue-on-error", False)
    assert backend["defaults"]["run"]["working-directory"] == "paydirt-web/backend"
    install = next(step for step in backend["steps"]
                   if "pip install" in step.get("run", ""))
    assert "-r requirements.txt" in install["run"]
    assert "pytest" in install["run"]
    assert '"httpx<0.28"' in install["run"]
    run = next(step for step in backend["steps"]
               if "-m pytest" in step.get("run", ""))
    assert run["run"] == "python -m pytest tests/ -q -o addopts= --tb=short"
    assert not run.get("continue-on-error", False)


def test_ci_runs_complete_public_ai_audit_without_private_data(jobs: dict) -> None:
    audit = jobs["public-ai-audit"]
    assert audit["runs-on"] == "ubuntu-24.04"
    assert not audit.get("continue-on-error", False)
    run = next(step for step in audit["steps"]
               if "tests/run_ai_audit.py" in step.get("run", ""))
    assert run["run"] == (
        "python tests/run_ai_audit.py --season 2026 --weeks 16 --seed 8306 "
        "--compare-balanced --output .ai-audits/public-season.json"
    )
    assert not run.get("continue-on-error", False)
    assert "if" not in run


def test_python_matrix_matches_declared_supported_versions(jobs: dict) -> None:
    """CI should test the Python versions the package declares as supported."""
    import re

    metadata = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    declared = re.findall(r'"Programming Language :: Python :: (\d+\.\d+)"', metadata)
    assert declared, "Package metadata must declare supported Python minor versions"
    assert jobs["test"]["strategy"]["matrix"]["python-version"] == declared


def test_full_core_suite_runs_once_with_coverage_on_release_python(jobs: dict) -> None:
    steps = jobs["test"]["steps"]
    runs = [step for step in steps if "pytest" in step.get("run", "") and "pip install" not in step["run"]]
    full = [step for step in runs if "--cov=paydirt" in step["run"]]
    assert len(full) == 1
    assert full[0]["if"] == "matrix.python-version == '3.10'"
    assert "python -m pytest tests/" in full[0]["run"]
    compatibility = [step for step in runs if step is not full[0]]
    assert len(compatibility) == 1
    assert compatibility[0]["if"] == "matrix.python-version != '3.10'"
    for module in ("test_game.py", "test_save_game.py", "test_season_rules.py", "test_team_charts.py", "test_cli.py"):
        assert f"tests/{module}" in compatibility[0]["run"]


def test_superseded_branch_runs_are_cancelled() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
    concurrency = yaml.safe_load(workflow.read_text())["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "github.workflow" in concurrency["group"]
    assert "github.ref" in concurrency["group"]
