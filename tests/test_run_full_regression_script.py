"""Regression coverage for scripts/run_full_regression.py.

These tests stay synthetic: they never execute the real suite, never read
private chart material and never touch the ignored local audit storage.
"""

from __future__ import annotations

import errno
import os
import socket
import subprocess
from pathlib import Path

import pytest

from paydirt.chart_release_gate import required_regression_commands
from scripts.run_full_regression import (
    StepResult,
    _port_free,
    browser_environment,
    choose_ports,
    clean_core_checkout,
    conditional_skip_reason,
    export_candidate_tree,
    main,
    regression_steps,
    summarize,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_port_environment(monkeypatch):
    monkeypatch.delenv("PAYDIRT_E2E_BACKEND_PORT", raising=False)
    monkeypatch.delenv("PAYDIRT_E2E_FRONTEND_PORT", raising=False)


def test_steps_cover_every_release_gate_command() -> None:
    steps = {step.name: step for step in regression_steps(ROOT)}
    expected = required_regression_commands(released_charts=True)
    assert set(expected) <= set(steps)
    for name, (cwd, argv) in expected.items():
        assert steps[name].cwd == cwd
        assert steps[name].argv == argv


def test_local_core_step_runs_the_whole_suite_without_coverage() -> None:
    """Dropping coverage must not quietly narrow the complete local run."""
    step = {entry.name: entry for entry in regression_steps(ROOT)}["core"]
    assert step.cwd == "."
    assert "tests/" in step.argv
    assert not any(part.startswith("--cov") for part in step.argv)


def test_released_chart_steps_use_released_audit() -> None:
    steps = {step.name: step for step in regression_steps(ROOT)}
    argv = steps["chart_1983"].argv
    assert "paydirt.released_chart_regression_audit" in argv
    assert "audit_generated_charts.py" not in " ".join(argv)


def test_routine_regression_uses_only_public_charts(tmp_path: Path) -> None:
    steps = {step.name: step for step in regression_steps(tmp_path)}
    assert "private_ai" not in steps
    assert all("1983-private-charts" not in " ".join(step.argv) for step in steps.values())
    assert conditional_skip_reason(steps["core"], tmp_path) is None


def test_default_ports_need_no_override_when_free() -> None:
    assert choose_ports(probe=lambda port: True) == {}


def test_occupied_default_ports_get_isolated_replacements() -> None:
    env = choose_ports(probe=lambda port: port not in (8000, 5173))
    assert env["PAYDIRT_E2E_BACKEND_PORT"] != "8000"
    assert env["PAYDIRT_E2E_FRONTEND_PORT"] != "5173"
    assert env["PAYDIRT_E2E_BACKEND_PORT"] != env["PAYDIRT_E2E_FRONTEND_PORT"]


@pytest.mark.parametrize("values", [
    {"PAYDIRT_E2E_BACKEND_PORT": "19000", "PAYDIRT_E2E_FRONTEND_PORT": "19001"},
])
def test_explicit_ports_are_preserved(monkeypatch, values) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    assert choose_ports(probe=lambda port: True) == values


@pytest.mark.parametrize("backend,frontend", [
    ("bad", "19001"), ("0", "19001"), ("65536", "19001"),
    ("19000", "19000"), ("19000", None),
])
def test_invalid_explicit_ports_fail_before_execution(monkeypatch, backend, frontend) -> None:
    monkeypatch.setenv("PAYDIRT_E2E_BACKEND_PORT", backend)
    if frontend is None:
        monkeypatch.delenv("PAYDIRT_E2E_FRONTEND_PORT", raising=False)
    else:
        monkeypatch.setenv("PAYDIRT_E2E_FRONTEND_PORT", frontend)
    with pytest.raises(ValueError, match="port|PORT"):
        choose_ports(probe=lambda port: True)


def test_occupied_explicit_ports_are_rejected(monkeypatch) -> None:
    monkeypatch.setenv("PAYDIRT_E2E_BACKEND_PORT", "19000")
    monkeypatch.setenv("PAYDIRT_E2E_FRONTEND_PORT", "19001")
    with pytest.raises(ValueError, match="occupied|available"):
        choose_ports(probe=lambda port: port != 19001)


def test_exhausted_isolation_range_never_returns_unprobed_port(monkeypatch) -> None:
    monkeypatch.delenv("PAYDIRT_E2E_BACKEND_PORT", raising=False)
    monkeypatch.delenv("PAYDIRT_E2E_FRONTEND_PORT", raising=False)
    with pytest.raises(ValueError, match="available|free"):
        choose_ports(probe=lambda port: False)


def test_port_probe_checks_both_localhost_families(monkeypatch) -> None:
    bound = []
    class FakeSocket:
        def __init__(self, family, kind):
            self.family = family
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def setsockopt(self, *args):
            pass
        def bind(self, address):
            bound.append(address)
            if self.family == socket.AF_INET6:
                raise OSError(48, "Address already in use")
    monkeypatch.setattr(socket, "socket", FakeSocket)
    assert _port_free(19000) is False
    assert ("127.0.0.1", 19000) in bound
    assert ("::1", 19000) in bound


@pytest.mark.parametrize("ipv6_error", [None, errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL])
def test_port_probe_allows_free_or_unavailable_ipv6(monkeypatch, ipv6_error) -> None:
    class FakeSocket:
        def __init__(self, family, kind):
            self.family = family
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def bind(self, address):
            if self.family == socket.AF_INET6 and ipv6_error:
                raise OSError(ipv6_error, "IPv6 unavailable")
    monkeypatch.setattr(socket, "socket", FakeSocket)
    assert _port_free(19000) is True


def test_isolated_pair_avoids_overlap_and_probes_next_candidate(monkeypatch) -> None:
    monkeypatch.setattr("scripts.run_full_regression.ISOLATED_FRONTEND_BASE", 18000)
    probed = []
    def probe(port):
        probed.append(port)
        return port not in (8000, 18001)
    assert choose_ports(probe) == {
        "PAYDIRT_E2E_BACKEND_PORT": "18000",
        "PAYDIRT_E2E_FRONTEND_PORT": "18002",
    }
    assert 18002 in probed


def test_invalid_ports_are_preflight_failure_not_traceback(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr("scripts.run_full_regression._preflight", lambda root: [])
    monkeypatch.setenv("PAYDIRT_E2E_BACKEND_PORT", "invalid")
    assert main(["--only", "browser"], root=tmp_path) == 2
    assert "PREFLIGHT:" in capsys.readouterr().err


def test_browser_step_pins_the_regression_interpreter_on_path() -> None:
    env = browser_environment(
        {"PATH": f"/usr/bin{os.pathsep}/bin"}, "/project/.venv/bin/python3"
    )
    entries = env["PATH"].split(os.pathsep)
    assert entries[0] == "/project/.venv/bin"
    assert entries[1:] == ["/usr/bin", "/bin"]


def test_browser_environment_does_not_mutate_its_input() -> None:
    base = {"PATH": "/usr/bin"}
    browser_environment(base, "/project/.venv/bin/python3")
    assert base == {"PATH": "/usr/bin"}


def test_browser_environment_tolerates_a_missing_path() -> None:
    env = browser_environment({}, "/project/.venv/bin/python3")
    assert env["PATH"] == "/project/.venv/bin"


def test_summarize_reports_failure_and_nonzero_exit() -> None:
    results = [
        StepResult(name="core", status="pass", seconds=1.25, returncode=0),
        StepResult(
            name="lint",
            status="fail",
            seconds=0.5,
            returncode=1,
            log_path=Path("lint.log"),
            tail=["E501 line too long"],
        ),
    ]
    text, code = summarize(results)
    assert code == 1
    assert "FAIL" in text
    assert "lint" in text
    assert "E501 line too long" in text


def test_summarize_all_skipped_is_success() -> None:
    results = [
        StepResult(name="core", status="pass", seconds=0.1, returncode=0),
        StepResult(name="browser", status="skip", seconds=0.0, reason="browser absent"),
    ]
    text, code = summarize(results)
    assert code == 0
    assert "SKIP" in text
    assert "browser absent" in text


def test_dry_run_plans_without_executing(tmp_path: Path, capsys) -> None:
    code = main(["--dry-run", "--only", "core"], root=tmp_path)
    assert code == 0
    output = capsys.readouterr().out
    assert "pytest" in output
    assert not (tmp_path / ".ai-audits").exists()


def test_list_mode_names_every_step(tmp_path: Path, capsys) -> None:
    code = main(["--list"], root=tmp_path)
    assert code == 0
    output = capsys.readouterr().out
    for name in required_regression_commands(released_charts=True):
        assert name in output
    assert "private_ai" not in output


def test_clean_checkout_step_is_opt_in() -> None:
    default_steps = {step.name for step in regression_steps(ROOT)}
    assert "clean_core" not in default_steps
    opted_in = {step.name for step in regression_steps(ROOT, include_clean_checkout=True)}
    assert "clean_core" in opted_in


def test_only_and_skip_filter_steps(tmp_path: Path, capsys) -> None:
    assert main(["--dry-run", "--only", "core,lint"], root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "core" in output
    assert "lint" in output
    assert "full_season" not in output

    assert main(["--dry-run", "--only", "core,lint", "--skip", "lint"], root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "core" in output
    assert "lint" not in output


def test_unknown_step_name_is_a_usage_error(tmp_path: Path, capsys) -> None:
    assert main(["--dry-run", "--only", "not_a_step"], root=tmp_path) == 2
    assert "not_a_step" in capsys.readouterr().err

def _make_candidate_repo(tmp_path: Path) -> Path:
    """Create a scratch repository with one committed tracked file."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("VALUE = 'head'\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_value.py").write_text(
        "from pkg import VALUE\n\n\ndef test_value() -> None:\n    assert VALUE == 'head'\n"
    )
    git = ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "initial"], cwd=repo, check=True)
    return repo


def test_candidate_export_includes_uncommitted_tracked_change(tmp_path: Path) -> None:
    """The clean checkout must validate the candidate, not the last commit."""
    repo = _make_candidate_repo(tmp_path)
    (repo / "pkg" / "__init__.py").write_text("VALUE = 'candidate'\n")
    target = tmp_path / "export"

    export_candidate_tree(repo, target)

    assert (target / "pkg" / "__init__.py").read_text() == "VALUE = 'candidate'\n"


def test_candidate_export_includes_staged_change(tmp_path: Path) -> None:
    repo = _make_candidate_repo(tmp_path)
    (repo / "pkg" / "__init__.py").write_text("VALUE = 'staged'\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    (repo / "pkg" / "__init__.py").write_text("VALUE = 'staged and edited'\n")
    target = tmp_path / "export"

    export_candidate_tree(repo, target)

    assert (target / "pkg" / "__init__.py").read_text() == "VALUE = 'staged and edited'\n"


def test_candidate_export_includes_new_untracked_file_but_excludes_ignored(tmp_path: Path) -> None:
    repo = _make_candidate_repo(tmp_path)
    (repo / ".gitignore").write_text("ignored.txt\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "ignore"],
        cwd=repo, check=True,
    )
    (repo / "new_test.py").write_text("VALUE = 'new work'\n")
    (repo / "ignored.txt").write_text("local only\n")
    target = tmp_path / "export"

    export_candidate_tree(repo, target)

    assert (target / "new_test.py").read_text() == "VALUE = 'new work'\n"
    assert not (target / "ignored.txt").exists()


def test_candidate_export_omits_a_tracked_file_deleted_in_the_worktree(tmp_path: Path) -> None:
    repo = _make_candidate_repo(tmp_path)
    (repo / "tests" / "test_value.py").unlink()
    target = tmp_path / "export"

    export_candidate_tree(repo, target)

    assert not (target / "tests" / "test_value.py").exists()


def test_candidate_export_refuses_a_directory_outside_git(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        export_candidate_tree(tmp_path, tmp_path / "export")


def test_clean_core_checkout_runs_the_candidate_test_suite(tmp_path: Path) -> None:
    """An uncommitted fix must flip the clean unit run from red to green."""
    repo = _make_candidate_repo(tmp_path)
    (repo / "tests" / "test_value.py").write_text(
        "from pkg import VALUE\n\n\ndef test_value() -> None:\n    assert VALUE == 'candidate'\n"
    )
    assert clean_core_checkout(repo) == 1

    (repo / "pkg" / "__init__.py").write_text("VALUE = 'candidate'\n")
    assert clean_core_checkout(repo) == 0
