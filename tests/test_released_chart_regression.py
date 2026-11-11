"""Trusted released-data regression uses synthetic repositories only."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from paydirt import released_chart_regression_audit as gate


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(Path(__file__).resolve().parents[1] / "seasons/2026", root / "seasons/2026")
    for name, content in {"paydirt/game_engine.py": "RULE = True\n", "paydirt/__init__.py": "__version__ = '1.10.3'\n", "config/chart-validation/2026.json": json.dumps({"known_accuracy_exceptions": [{"strict_passed": False}]}), "seasons/2026/generation-manifest.json": json.dumps({"source": "synthetic", "original_generation_manifest_sha256": "a" * 64})}.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    for name in ("paydirt/__main__.py", "paydirt-web/backend/main.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("app = FastAPI(title='Synthetic', version='1.10.3')\n")
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
        assert command[1:3] == ["-m", "paydirt.released_chart_regression_audit"]
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
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression_audit.py"))
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
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression_audit.py"))
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
    monkeypatch.setattr(gate, "__file__", str(root / "paydirt/released_chart_regression_audit.py"))
    monkeypatch.setattr(gate, "audit_released_season", lambda *args, **kwargs: {"passed": True})
    with pytest.raises(SystemExit):
        gate.main(["--season", "2026", "--output", str(destination)])
    assert launcher.read_text() == "original launcher\n"


def test_release_auditor_does_not_change_gameplay_source_identity(tmp_path, monkeypatch):
    from paydirt import chart_engine_audit as engine
    measurement = tmp_path / "chart_engine_audit.py"
    measurement.write_text("MEASUREMENT = 1\n")
    core = tmp_path / "game_engine.py"
    core.write_text("CORE = 1\n")
    monkeypatch.setattr(engine, "__file__", str(measurement))
    before = engine.engine_fingerprint()
    helper = tmp_path / Path(gate.__file__).name
    helper.write_text("VALIDATOR = 1\n")
    assert engine.engine_fingerprint() == before
    helper.write_text("VALIDATOR = 2\n")
    assert engine.engine_fingerprint() == before
    core.write_text("CORE = 2\n")
    assert engine.engine_fingerprint() != before
    core.write_text("CORE = 1\n")
    measurement.write_text("MEASUREMENT = 2\n")
    assert engine.engine_fingerprint() != before


@pytest.mark.parametrize("name", ["paydirt/__main__.py", "paydirt-web/backend/main.py"])
def test_api_release_version_metadata_may_change_without_gameplay_change(baseline, name):
    root, _ = baseline
    (root / name).write_text("app = FastAPI(title='Synthetic', version='1.10.4')\n")
    assert gate.audit_released_season(root, season=2026)["passed"]


@pytest.mark.parametrize("name", ["paydirt/__main__.py", "paydirt-web/backend/main.py"])
def test_api_metadata_allowance_does_not_hide_other_behavior(baseline, name):
    root, _ = baseline
    (root / name).write_text("app = FastAPI(title='Changed', version='1.10.4')\n")
    assert not gate.audit_released_season(root, season=2026)["passed"]


@pytest.mark.parametrize("change", [None, "chart", "extra", "symlink"])
def test_relocated_release_requires_exact_baseline_bytes(baseline, monkeypatch, change):
    root, _ = baseline
    original = root / "seasons/2026"
    relocated = root / "seasons/2026-public"
    original.rename(relocated)
    monkeypatch.setattr(gate, "CURRENT_SEASON_PATHS", {2026: "seasons/2026-public"}, raising=False)
    chart = next(relocated.glob("*/offense.csv"))
    if change == "chart":
        chart.write_bytes(chart.read_bytes() + b"\n")
    elif change == "extra":
        (relocated / "extra.txt").write_text("unexpected")
    elif change == "symlink":
        external = root / "external.csv"
        chart.rename(external)
        chart.symlink_to(external)
    report = gate.audit_released_season(root, season=2026)
    assert report["passed"] is (change is None), report["errors"]
    if change is None:
        assert report["gameplay_implementation_unchanged"] is True
        assert report["baseline_season_path"] == "seasons/2026"
        assert report["current_season_path"] == "seasons/2026-public"


@pytest.fixture
def metadata_baseline(baseline, monkeypatch):
    """Build synthetic historical labels around public sample chart bytes only."""
    root, git = baseline
    season = root / "seasons/1983"
    originals = {"Chargers": "LAC", "Cardinals": "ARI", "Raiders": "OAK"}
    for team, abbreviation in originals.items():
        target = season / team
        shutil.copytree(root / "seasons/2026/Ironclads", target)
        (target / "team.yaml").write_text(
            f'team_name: "{team}"\nshort_name: "{abbreviation} \'83"\nnickname: "{team}"\n'
        )
    (root / "config/chart-validation/1983.json").write_text("{}")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "synthetic metadata baseline")
    commit = git("rev-parse", "HEAD")
    git("tag", "-f", "v1.10.3")
    monkeypatch.setattr(gate, "TRUSTED_RELEASES", {
        "v1.10.3": {"commit": commit, "seasons": {1983: ("seasons/1983", 3)}},
    })
    monkeypatch.setattr(gate, "REVIEWED_METADATA_BASELINE_COMMIT", commit, raising=False)
    monkeypatch.setattr(gate, "audit_public_season", lambda *args, **kwargs: {"errors": []})
    return root


def apply_reviewed_labels(root: Path) -> None:
    for team, before, after in (
        ("Chargers", "LAC", "SD"), ("Cardinals", "ARI", "STL"), ("Raiders", "OAK", "LA"),
    ):
        path = root / "seasons/1983" / team / "team.yaml"
        path.write_bytes(path.read_bytes().replace(
            f'short_name: "{before} \'83"'.encode(),
            f'short_name: "{after} \'83"'.encode(),
        ))


def test_exact_reviewed_metadata_corrections_pass_and_are_receipted(metadata_baseline):
    root = metadata_baseline
    apply_reviewed_labels(root)
    report = gate.audit_released_season(root, season=1983)
    assert report["passed"], report["errors"]
    assert report["gameplay_implementation_unchanged"]
    corrections = report["accepted_metadata_corrections"]
    assert len(corrections) == 3
    assert {item["path"] for item in corrections} == {
        f"seasons/1983/{team}/team.yaml" for team in ("Chargers", "Cardinals", "Raiders")
    }
    assert all(item["issue"] == "DATA-047" for item in corrections)
    for item in corrections:
        current = root / item["path"]
        original = subprocess.check_output([
            "git", "-C", str(root), "show", f"v1.10.3:{item['path']}",
        ])
        assert item["baseline_sha256"] == hashlib.sha256(original).hexdigest()
        assert item["accepted_sha256"] == hashlib.sha256(current.read_bytes()).hexdigest()


@pytest.mark.parametrize("mutation", [
    "extra-field", "wrong-label", "whitespace", "chart", "contract", "runtime", "symlink",
])
def test_metadata_allowance_rejects_every_other_change(metadata_baseline, mutation):
    root = metadata_baseline
    apply_reviewed_labels(root)
    path = root / "seasons/1983/Chargers/team.yaml"
    if mutation == "extra-field":
        path.write_bytes(path.read_bytes() + b"city: Wrong City\n")
    elif mutation == "wrong-label":
        path.write_bytes(path.read_bytes().replace(b"SD '83", b"LV '83"))
    elif mutation == "whitespace":
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "symlink":
        external = root / "external.yaml"
        path.rename(external)
        path.symlink_to(external)
    else:
        path = {
            "chart": root / "seasons/1983/Chargers/offense.csv",
            "contract": root / "config/chart-validation/1983.json",
            "runtime": root / "paydirt/game_engine.py",
        }[mutation]
        path.write_bytes(path.read_bytes() + b"\n")
    assert not gate.audit_released_season(root, season=1983)["passed"]


def test_metadata_allowance_requires_reviewed_baseline_identity(metadata_baseline, monkeypatch):
    apply_reviewed_labels(metadata_baseline)
    monkeypatch.setattr(gate, "REVIEWED_METADATA_BASELINE_COMMIT", "0" * 40, raising=False)
    assert not gate.audit_released_season(metadata_baseline, season=1983)["passed"]


@pytest.mark.parametrize("path", [
    "paydirt-web/backend/routes.py", "paydirt-web/backend/test_rule.py",
    "paydirt/game_engine.py", "paydirt_runner.py",
    "paydirt-web/backend/tests_helpers.py", "paydirt-web/backend/tests_runtime/rules.py",
])
def test_gameplay_identity_still_covers_runtime_paths(path):
    assert gate._runtime_path(path)


def test_backend_tests_are_validated_as_tests_not_gameplay_identity(baseline):
    root, _ = baseline
    test = root / "paydirt-web/backend/tests/test_synthetic.py"
    test.parent.mkdir(parents=True)
    test.write_text("def test_control():\n    assert True\n")
    assert not gate._runtime_path(str(test.relative_to(root)))
    assert gate.audit_released_season(root, season=2026)["passed"]
