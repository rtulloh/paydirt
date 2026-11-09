"""Trusted released-data regression uses synthetic repositories only."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from paydirt import released_chart_regression as gate


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(Path(__file__).resolve().parents[1] / "seasons/2026", root / "seasons/2026")
    for name, content in {"paydirt/game_engine.py": "RULE = True\n", "paydirt/__init__.py": "__version__ = '1.10.3'\n", "config/chart-validation/2026.json": json.dumps({"known_accuracy_exceptions": [{"strict_passed": False}]}), "seasons/2026/generation-manifest.json": json.dumps({"source": "synthetic", "original_generation_manifest_sha256": "a" * 64})}.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    commit = git("rev-parse", "HEAD")
    git("tag", "v1.10.3")
    monkeypatch.setattr(gate, "TRUSTED_RELEASES", {"v1.10.3": {"commit": commit, "seasons": {2026: ("seasons/2026", 2)}}})
    return root, git


def test_unchanged_sanitized_public_release_keeps_exceptions(baseline):
    report = gate.audit_released_season(baseline[0], season=2026)
    assert report["passed"]
    assert report["known_accuracy_exceptions"] == [{"strict_passed": False}]
    assert report["strict_fit_passed"] is False
    assert report["source_reproduction_checked"] is False
    assert report["gameplay_implementation_unchanged"] is True


@pytest.mark.parametrize("kind", ["chart", "manifest", "contract", "runtime"])
def test_changed_release_identity_rejected(baseline, kind):
    root, _ = baseline
    paths = {"chart": next((root / "seasons/2026").glob("*/offense.csv")), "manifest": root / "seasons/2026/generation-manifest.json", "contract": root / "config/chart-validation/2026.json", "runtime": root / "paydirt/game_engine.py"}
    path = paths[kind]
    path.write_bytes(path.read_bytes() + b"\n")
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_new_season_cannot_claim_released_status(baseline):
    root, _ = baseline
    shutil.copytree(root / "seasons/2026", root / "seasons/1977")
    assert not gate.audit_released_season(root, season=1977)["passed"]


def test_self_attested_manifest_cannot_rebind_changed_chart(baseline):
    root, _ = baseline
    path = next((root / "seasons/2026").glob("*/offense.csv"))
    path.write_bytes(path.read_bytes() + b"\n")
    (root / "seasons/2026/generation-manifest.json").write_text(json.dumps({"released": True, "source": "replacement"}))
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_moved_release_tag_rejected(baseline):
    root, git = baseline
    (root / "paydirt/game_engine.py").write_text("RULE = False\n")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "replacement")
    git("tag", "-f", "v1.10.3")
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_new_runtime_module_rejected(baseline):
    root, _ = baseline
    (root / "paydirt/unknown_rule.py").write_text("RULE = False\n")
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_generation_only_and_version_changes_allowed(baseline):
    root, _ = baseline
    (root / "paydirt/chart_generator.py").write_text("GENERATOR = True\n")
    (root / "paydirt/__init__.py").write_text("__version__ = '1.10.4'\n")
    assert gate.audit_released_season(root, season=2026)["passed"]


def test_symlink_to_identical_bytes_is_rejected(baseline, tmp_path):
    root, _ = baseline
    chart = next((root / "seasons/2026").glob("*/offense.csv"))
    external = tmp_path / "chart.csv"
    external.write_bytes(chart.read_bytes())
    chart.unlink()
    chart.symlink_to(external)
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_version_allowance_does_not_allow_other_init_changes(baseline):
    root, _ = baseline
    (root / "paydirt/__init__.py").write_text("__version__ = '1.10.4'\nHIDDEN_RULE = True\n")
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_required_release_checklist_uses_explicit_released_gate():
    from paydirt.chart_release_gate import required_regression_commands
    for season in ("1983", "2024"):
        _, command = required_regression_commands(released_charts=True)[f"chart_{season}"]
        assert command[1:3] == ["-m", "paydirt.released_chart_regression"]
        assert command[command.index("--season") + 1] == season


def test_git_replacement_cannot_rebind_trusted_tree(baseline):
    root, git = baseline
    old = git("rev-parse", "HEAD")
    chart = next((root / "seasons/2026").glob("*/offense.csv"))
    chart.write_bytes(chart.read_bytes() + b"\n")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "replacement")
    git("replace", old, git("rev-parse", "HEAD"))
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_cli_cannot_overwrite_protected_launcher(baseline, monkeypatch):
    root, _ = baseline
    launcher = root / "paydirt_runner.py"
    launcher.write_text("original launcher\n")
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression.py"))
    monkeypatch.setattr(gate, "audit_released_season", lambda *args, **kwargs: {"passed": True})
    with pytest.raises(SystemExit) as error:
        gate.main(["--season", "2026", "--output", str(launcher)])
    assert error.value.code == 2
    assert launcher.read_text() == "original launcher\n"


def test_symlinked_season_directory_rejected(baseline, tmp_path):
    root, _ = baseline
    original = root / "seasons/2026"
    external = tmp_path / "external-season"
    original.rename(external)
    original.symlink_to(external, target_is_directory=True)
    assert not gate.audit_released_season(root, season=2026)["passed"]


def test_cli_ignored_directory_cannot_redirect_into_inputs(baseline, monkeypatch):
    root, _ = baseline
    (root / ".ai-audits").symlink_to(root / "paydirt", target_is_directory=True)
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression.py"))
    monkeypatch.setattr(gate, "audit_released_season", lambda *args, **kwargs: {"passed": True})
    original = (root / "paydirt/game_engine.py").read_bytes()
    with pytest.raises(SystemExit):
        gate.main(["--season", "2026", "--output", str(root / ".ai-audits/game_engine.py")])
    assert (root / "paydirt/game_engine.py").read_bytes() == original


def test_hardlinked_receipt_cannot_overwrite_launcher(baseline, monkeypatch):
    import os
    root, _ = baseline
    launcher = root / "paydirt_runner.py"
    launcher.write_text("original launcher\n")
    destination = root / ".ai-audits/report.json"
    destination.parent.mkdir()
    os.link(launcher, destination)
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression.py"))
    monkeypatch.setattr(gate, "audit_released_season", lambda *args, **kwargs: {"passed": True})
    with pytest.raises(SystemExit):
        gate.main(["--season", "2026", "--output", str(destination)])
    assert launcher.read_text() == "original launcher\n"
