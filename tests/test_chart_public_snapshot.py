"""Clean unit evidence must bind exact public working-tree files and real logs."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

import paydirt.chart_release_gate as gate
from tests import test_chart_readiness_freeze as freeze_support
from tests.test_chart_regression_evidence import freeze_digest

freeze_files = freeze_support.freeze_files


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_inventory(root: Path) -> dict[str, str]:
    names = (
        subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
        )
        .decode()
        .split("\0")
    )
    return {name: digest(root / name) for name in names if name and (root / name).is_file()}


@pytest.fixture
def snapshot_files(freeze_files: tuple) -> tuple[Path, dict, dict]:
    root, freeze = freeze_files
    (root / ".gitignore").write_text(
        ".ai-audits/\ncandidates/\ninputs/\nseasons/1972/\nnode_modules/\n__pycache__/\n.pytest_cache/\n.coverage*\n"
    )
    (root / "README.md").write_text("Synthetic public documentation\n")
    for name, entry in freeze["cohorts"].items():
        shutil.copytree(
            root / entry["season_dir"],
            root / "seasons" / ("1983" if name == "1983-generated" else name),
        )
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "AGENTS.md"], check=True)
    (root / "AGENTS.md").write_text("Synthetic changed tracked public file\n")
    freeze["files"]["AGENTS.md"] = digest(root / "AGENTS.md")
    files = public_inventory(root)
    snapshot = root / ".ai-audits/public-snapshot/source"
    for name in files:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    commands = {}
    required = gate.required_regression_commands()
    for name in ("setup", "core", "backend", "frontend"):
        cwd, argv = ("paydirt-web/frontend", ["npm", "ci"]) if name == "setup" else required[name]
        log = root / ".ai-audits/public-snapshot" / (name + ".json")
        log.write_text(
            json.dumps(
                {
                    "argv": argv,
                    "cwd": str((snapshot / cwd).resolve()),
                    "returncode": 0,
                    "stdout": "Synthetic successful clean unit run\n",
                    "stderr": "",
                    "pythonpath": str(snapshot),
                }
            )
        )
        commands[name] = {"path": str(log.relative_to(root)), "sha256": digest(log)}
    return (
        root,
        freeze,
        {
            "schema_version": 1,
            "freeze_sha256": freeze_digest(freeze),
            "snapshot_dir": str(snapshot.relative_to(root)),
            "files": files,
            "commands": commands,
        },
    )


def audit(files: tuple) -> dict:
    function = getattr(gate, "audit_public_snapshot", None)
    assert callable(function), (
        "Readiness must independently validate clean public snapshot evidence"
    )
    return function(*files)


def test_clean_snapshot_includes_dirty_tracked_and_new_public_files(snapshot_files: tuple) -> None:
    root, _freeze, data = snapshot_files
    result = audit(snapshot_files)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert result["file_count"] == len(data["files"])
    assert data["files"]["AGENTS.md"] == digest(root / "AGENTS.md")
    assert "README.md" in data["files"]


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong-version",
        "wrong-freeze",
        "missing-file",
        "changed-file",
        "omitted-file",
        "extra-file",
        "source-change",
        "source-addition",
        "source-symlink",
        "snapshot-symlink",
        "private-season",
        "private-empty-directory",
        "substituted-candidate",
        "missing-command",
        "extra-command",
        "changed-log",
        "wrong-cwd",
        "wrong-command",
        "wrong-pythonpath",
        "failed-command",
        "bool-exit",
        "bare-log",
        "duplicate-json",
        "missing-output",
        "extra-field",
    ],
)
def test_stale_incomplete_or_contaminated_snapshot_cannot_validate(
    snapshot_files: tuple,
    mutation: str,
) -> None:
    root, freeze, original = snapshot_files
    data = deepcopy(original)
    snapshot = root / data["snapshot_dir"]
    reference = data["commands"]["core"]
    log = root / reference["path"]
    execution = json.loads(log.read_text())
    rewrite = False
    if mutation == "wrong-version":
        data["schema_version"] = True
    elif mutation == "wrong-freeze":
        data["freeze_sha256"] = "0" * 64
    elif mutation == "missing-file":
        (snapshot / "README.md").unlink()
    elif mutation == "changed-file":
        (snapshot / "README.md").write_text("Changed\n")
    elif mutation == "omitted-file":
        (snapshot / "README.md").unlink()
        data["files"].pop("README.md")
    elif mutation == "extra-file":
        (snapshot / "extra.txt").write_text("Unbound\n")
    elif mutation == "source-change":
        (root / "README.md").write_text("Changed source\n")
    elif mutation == "source-addition":
        (root / "new-public.txt").write_text("New source\n")
    elif mutation in {"source-symlink", "snapshot-symlink"}:
        path = (root if mutation == "source-symlink" else snapshot) / "README.md"
        path.unlink()
        path.symlink_to(root / "AGENTS.md")
    elif mutation in {"private-season", "private-empty-directory"}:
        directory = snapshot / "seasons/1972/Synthetic"
        directory.mkdir(parents=True)
        if mutation == "private-season":
            (directory / "offense.csv").write_text("Synthetic forbidden stand-in\n")
    elif mutation == "substituted-candidate":
        for directory in (root, snapshot):
            (directory / "seasons/2024/offense.csv").write_text("Different synthetic candidate\n")
        data["files"] = public_inventory(root)
    elif mutation == "missing-command":
        data["commands"].pop("backend")
    elif mutation == "extra-command":
        data["commands"]["smoke"] = deepcopy(reference)
    elif mutation == "changed-log":
        log.write_text("Changed\n")
    elif mutation == "wrong-cwd":
        execution["cwd"] = str(root)
        rewrite = True
    elif mutation == "wrong-command":
        execution["argv"] = ["python3", "-m", "pytest", "-k", "one_test"]
        rewrite = True
    elif mutation == "wrong-pythonpath":
        execution["pythonpath"] = str(root)
        rewrite = True
    elif mutation == "failed-command":
        execution["returncode"] = 1
        rewrite = True
    elif mutation == "bool-exit":
        execution["returncode"] = False
        rewrite = True
    elif mutation == "bare-log":
        data["commands"]["core"] = reference["path"]
    elif mutation == "duplicate-json":
        log.write_text('{"returncode":0,"returncode":1}')
        reference["sha256"] = digest(log)
    elif mutation == "missing-output":
        execution["stdout"] = ""
        rewrite = True
    elif mutation == "extra-field":
        data["passed"] = True
    if rewrite:
        log.write_text(json.dumps(execution))
        reference["sha256"] = digest(log)
    result = audit((root, freeze, data))
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False


def test_snapshot_allows_generated_caches_and_dependencies_but_preserves_skip_diagnostics(
    snapshot_files: tuple,
) -> None:
    root, _freeze, data = snapshot_files
    snapshot = root / data["snapshot_dir"]
    for name in (
        "paydirt/__pycache__/cached.pyc",
        ".pytest_cache/cache",
        ".coverage",
        "paydirt-web/frontend/node_modules/public-library/index.js",
    ):
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Generated cache\n")
    reference = data["commands"]["core"]
    path = root / reference["path"]
    execution = json.loads(path.read_text())
    execution["stdout"] = "100 passed, 2 skipped\nSKIPPED [2] synthetic existing capability\n"
    execution["stderr"] = "WARNING: synthetic existing deprecation\n"
    path.write_text(json.dumps(execution))
    reference["sha256"] = digest(path)
    result = audit(snapshot_files)
    assert result["passed"], result["errors"]
    assert len(result["commands"]["core"]["diagnostics"]) == 3


def test_snapshot_preserves_npm_warn_and_dependency_audit_summary(snapshot_files: tuple) -> None:
    root, _freeze, data = snapshot_files
    reference = data["commands"]["setup"]
    path = root / reference["path"]
    execution = json.loads(path.read_text())
    execution.update(
        {
            "stdout": "17 vulnerabilities (synthetic public fixture)\n",
            "stderr": "npm warn deprecated synthetic package\n",
        }
    )
    path.write_text(json.dumps(execution))
    reference["sha256"] = digest(path)
    result = audit(snapshot_files)
    assert result["passed"], result["errors"]
    assert result["commands"]["setup"]["diagnostics"] == [
        "17 vulnerabilities (synthetic public fixture)",
        "npm warn deprecated synthetic package",
    ]
